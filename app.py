"""DigiTech Markdown Converter — Flask server.

Converts uploaded files to Markdown using the markitdown library.
Converted files live in temp directories and are cleaned up after
30 minutes of inactivity.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import wave
from pathlib import Path

import requests
from flask import Flask, abort, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

try:
    from markitdown import MarkItDown
except ImportError:
    print("ERROR: markitdown not found. Run ./script -i to install dependencies.")
    sys.exit(1)

# OCR is optional: without pytesseract/tesseract, images fall back to
# metadata-only conversion (markitdown's default behavior).
try:
    import pytesseract
    from PIL import Image

    HAS_OCR = True
except ImportError:
    HAS_OCR = False

MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "500"))
if MAX_UPLOAD_SIZE_MB <= 0:
    raise ValueError("MAX_UPLOAD_SIZE_MB must be greater than zero")
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4"}
TEMP_DIR_PREFIX = "mc-"
TEMP_DIR_MAX_AGE_SECONDS = 30 * 60  # 30 minutes
TEMP_ROOT = Path(tempfile.gettempdir())
FFMPEG_TIMEOUT_SECONDS = 120

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE_BYTES


class LocalOnlyRequestsSession(requests.Session):
    """Reject every outbound request attempted by a document converter."""

    def request(self, method, url, *args, **kwargs):
        raise RuntimeError(f"External network access is disabled: {url}")


def create_local_only_converter() -> MarkItDown:
    """Build MarkItDown without its Google-backed audio converter."""
    local_converter = MarkItDown(requests_session=LocalOnlyRequestsSession())
    registrations = local_converter._converters
    local_converter._converters = [
        registration
        for registration in registrations
        if registration.converter.__class__.__name__ != "AudioConverter"
    ]
    if len(local_converter._converters) == len(registrations):
        raise RuntimeError("Could not disable MarkItDown's remote audio converter")
    return local_converter


converter = create_local_only_converter()
local_whisper_model = None


def temp_dir_for(file_id: str) -> Path:
    return TEMP_ROOT / f"{TEMP_DIR_PREFIX}{file_id}"


def is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def sweep_stale_temp_dirs() -> None:
    """Delete mc-* temp directories older than 30 minutes."""
    cutoff = time.time() - TEMP_DIR_MAX_AGE_SECONDS
    for entry in TEMP_ROOT.glob(f"{TEMP_DIR_PREFIX}*"):
        try:
            if entry.is_dir() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
        except OSError:
            continue


def find_markdown_file(file_id: str) -> Path:
    """Return the .md file for a file_id or abort with 404."""
    if not is_valid_uuid(file_id):
        abort(404)
    directory = temp_dir_for(file_id)
    if not directory.is_dir():
        abort(404)
    md_files = list(directory.glob("*.md"))
    if not md_files:
        abort(404)
    directory.touch(exist_ok=True)
    return md_files[0]


def extract_image_text(input_path: Path) -> str:
    """Run local Tesseract OCR on an image; returns extracted text or ''."""
    if not HAS_OCR:
        return ""
    try:
        with Image.open(input_path) as image:
            return pytesseract.image_to_string(image).strip()
    except Exception:
        return ""


def transcode_audio_to_pcm(input_path: Path) -> Path:
    """Extract the first audio stream as mono 16 kHz PCM WAV."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise RuntimeError(
            "FFmpeg is required to extract or normalize this audio file."
        )

    normalized_path = input_path.with_name(f"{input_path.stem}.normalized.wav")
    try:
        process = subprocess.run(
            [
                ffmpeg_path,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_path),
                "-map",
                "0:a:0",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-y",
                str(normalized_path),
            ],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Audio extraction timed out") from exc

    if process.returncode != 0 or not normalized_path.is_file():
        stderr = process.stderr.strip()
        if "matches no streams" in stderr or "does not contain any stream" in stderr:
            raise ValueError(
                f"{input_path.suffix.upper().lstrip('.')} file does not contain "
                "an audio track to transcribe"
            )
        detail = stderr.splitlines()
        message = detail[-1] if detail else "FFmpeg could not decode the audio"
        raise ValueError(f"Unsupported or invalid audio: {message}")

    return normalized_path


def normalize_wav_for_transcription(input_path: Path) -> Path:
    """Return a PCM WAV path, transcoding unsupported WAV codecs when needed."""
    try:
        with wave.open(str(input_path), "rb") as audio:
            if (
                audio.getcomptype() == "NONE"
                and 1 <= audio.getnchannels() <= 2
                and 1 <= audio.getsampwidth() <= 4
            ):
                return input_path
    except (EOFError, wave.Error):
        # Codecs such as G.711 mu-law have a valid WAV container but are not
        # readable by Python's PCM-only wave decoder.
        pass

    return transcode_audio_to_pcm(input_path)


def get_local_whisper_model():
    """Load a Whisper model from disk without allowing network downloads."""
    global local_whisper_model
    if local_whisper_model is not None:
        return local_whisper_model

    model_path_value = os.environ.get("WHISPER_MODEL_PATH", "").strip()
    if not model_path_value:
        raise RuntimeError(
            "Local audio transcription is not configured. Set WHISPER_MODEL_PATH "
            "to a faster-whisper model directory stored on this server."
        )

    model_path = Path(model_path_value).expanduser().resolve()
    if not model_path.is_dir():
        raise RuntimeError(f"Local Whisper model directory not found: {model_path}")

    # These flags provide an additional guard against accidental model downloads.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Local audio transcription requires the faster-whisper package."
        ) from exc

    local_whisper_model = WhisperModel(
        str(model_path),
        device=os.environ.get("WHISPER_DEVICE", "cpu"),
        compute_type=os.environ.get("WHISPER_COMPUTE_TYPE", "int8"),
        local_files_only=True,
    )
    return local_whisper_model


def transcribe_audio_locally(input_path: Path) -> str:
    """Transcribe audio with a local-only faster-whisper model."""
    model = get_local_whisper_model()
    language = os.environ.get("WHISPER_LANGUAGE", "").strip() or None
    segments, _info = model.transcribe(
        str(input_path),
        language=language,
        vad_filter=True,
    )
    transcript = " ".join(
        segment.text.strip() for segment in segments if segment.text.strip()
    )
    if not transcript:
        transcript = "[No speech detected]"
    return f"### Audio Transcript\n\n{transcript}\n"


def convert_single_file(upload) -> dict:
    """Convert one uploaded file; always returns a per-file result dict."""
    original_name = upload.filename or "unnamed"
    safe_name = secure_filename(original_name)
    if not safe_name:
        return {
            "id": None,
            "original_name": original_name,
            "md_name": None,
            "status": "error",
            "error": "Invalid filename",
        }

    file_id = str(uuid.uuid4())
    directory = temp_dir_for(file_id)
    directory.mkdir(parents=True, exist_ok=True)
    input_path = directory / safe_name
    md_name = f"{Path(safe_name).stem}.md"
    output_path = directory / md_name

    try:
        upload.save(input_path)
        conversion_path = input_path
        suffix = input_path.suffix.lower()
        if suffix in AUDIO_EXTENSIONS:
            # Never pass audio to MarkItDown: its audio converter uses Google's
            # remote speech-recognition service.
            if suffix == ".wav":
                conversion_path = normalize_wav_for_transcription(input_path)
            else:
                conversion_path = transcode_audio_to_pcm(input_path)
            markdown_text = transcribe_audio_locally(conversion_path)
        else:
            result = converter.convert(str(conversion_path))
            markdown_text = result.text_content

        if suffix in IMAGE_EXTENSIONS:
            ocr_text = extract_image_text(input_path)
            if ocr_text:
                markdown_text = (
                    f"{markdown_text}\n\n## Extracted Text (OCR)\n\n{ocr_text}\n"
                )
        output_path.write_text(markdown_text, encoding="utf-8")
        if conversion_path != input_path:
            conversion_path.unlink(missing_ok=True)
        input_path.unlink(missing_ok=True)
        return {
            "id": file_id,
            "original_name": original_name,
            "md_name": md_name,
            "status": "ok",
        }
    except Exception as exc:  # markitdown raises many exception types
        shutil.rmtree(directory, ignore_errors=True)
        return {
            "id": None,
            "original_name": original_name,
            "md_name": None,
            "status": "error",
            "error": str(exc) or "Unsupported file type",
        }


@app.before_request
def cleanup_before_request():
    sweep_stale_temp_dirs()


@app.after_request
def add_local_only_content_security_policy(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "img-src 'self' data:; "
        "object-src 'none'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "frame-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    uploads = request.files.getlist("files")
    if not uploads:
        return jsonify({"files": [], "error": "No files provided"}), 400
    results = [convert_single_file(upload) for upload in uploads]
    return jsonify({"files": results})


@app.route("/preview/<file_id>")
def preview(file_id: str):
    md_file = find_markdown_file(file_id)
    return md_file.read_text(encoding="utf-8"), 200, {
        "Content-Type": "text/plain; charset=utf-8"
    }


@app.route("/download/<file_id>")
def download(file_id: str):
    md_file = find_markdown_file(file_id)
    return send_file(
        md_file,
        as_attachment=True,
        download_name=md_file.name,
        mimetype="text/markdown",
    )


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify(
        {"files": [], "error": f"File exceeds the {MAX_UPLOAD_SIZE_MB} MB limit"}
    ), 413


# Listen on all IPv4 interfaces so the app can be reached from other machines.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=False)
