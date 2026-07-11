"""Markdown Converter Flask server.

Converts uploaded files to Markdown using the markitdown library.
Converted files live in temp directories and are cleaned up after
30 minutes of inactivity.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

from env_loader import load_dotenv_and_reexec

# Load .env (WHISPER_MODEL_PATH, LD_LIBRARY_PATH, ...) before anything that
# can touch CUDA. May re-exec the process once so the dynamic linker sees
# LD_LIBRARY_PATH; must therefore run before other application imports.
load_dotenv_and_reexec()

from flask import Flask, abort, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from transcription import (
    Options,
    render_markdown,
    transcribe,
    transcription_status,
    validate_options,
)

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
FFMPEG_TIMEOUT_SECONDS = int(os.environ.get("FFMPEG_TIMEOUT_SECONDS", "600"))
WHISPER_BEAM_SIZE = int(os.environ.get("WHISPER_BEAM_SIZE", "5"))
if FFMPEG_TIMEOUT_SECONDS <= 0:
    raise ValueError("FFMPEG_TIMEOUT_SECONDS must be greater than zero")
if WHISPER_BEAM_SIZE <= 0:
    raise ValueError("WHISPER_BEAM_SIZE must be greater than zero")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".webm", ".mp4"}
TEMP_DIR_PREFIX = "mc-"
TEMP_DIR_MAX_AGE_SECONDS = 30 * 60  # 30 minutes
TEMP_ROOT = Path(tempfile.gettempdir())

# The model must already exist on disk. These flags prevent runtime downloads,
# update checks, and telemetry from the model-loading stack.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_UPDATE_CHECK"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["DO_NOT_TRACK"] = "1"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE_BYTES


audio_processing_lock = threading.Lock()


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


def find_markitdown_cli() -> str:
    """Return the MarkItDown executable installed beside this Python."""
    venv_executable = Path(sys.executable).with_name("markitdown")
    if venv_executable.is_file() and os.access(venv_executable, os.X_OK):
        return str(venv_executable)

    executable = shutil.which("markitdown")
    if executable is None:
        raise RuntimeError("markitdown not found. Run ./script -i to install dependencies.")
    return executable


def convert_with_markitdown_cli(input_path: Path) -> str:
    """Convert a document through the same CLI used by ./script."""
    try:
        process = subprocess.run(
            [find_markitdown_cli(), str(input_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"Could not run MarkItDown: {exc}") from exc

    if process.returncode != 0:
        detail = process.stderr.strip().splitlines()
        message = detail[-1] if detail else "unknown conversion error"
        raise RuntimeError(f"MarkItDown conversion failed: {message}")
    return process.stdout


def convert_single_file(upload, transcription_options: Options) -> dict:
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
            if transcription_options.engine == "local_whisper":
                # Serialize local GPU jobs while allowing cloud jobs to proceed.
                with audio_processing_lock:
                    transcript = transcribe(
                        input_path, directory, transcription_options,
                        FFMPEG_TIMEOUT_SECONDS, WHISPER_BEAM_SIZE,
                    )
            else:
                transcript = transcribe(
                    input_path, directory, transcription_options,
                    FFMPEG_TIMEOUT_SECONDS, WHISPER_BEAM_SIZE,
                )
            markdown_text = render_markdown(transcript, transcription_options.include_timestamps)
        else:
            markdown_text = convert_with_markitdown_cli(conversion_path)

        if suffix in IMAGE_EXTENSIONS:
            ocr_text = extract_image_text(input_path)
            if ocr_text:
                markdown_text = (
                    f"{markdown_text}\n\n## Extracted Text (OCR)\n\n{ocr_text}\n"
                )
        output_path.write_text(markdown_text, encoding="utf-8")
        for temporary_file in directory.iterdir():
            if temporary_file != output_path and temporary_file.is_file():
                temporary_file.unlink(missing_ok=True)
        return {
            "id": file_id,
            "original_name": original_name,
            "md_name": md_name,
            "status": "ok",
            "transcription_engine": (
                transcription_options.engine if suffix in AUDIO_EXTENSIONS else None
            ),
        }
    except Exception as exc:  # markitdown raises many exception types
        shutil.rmtree(directory, ignore_errors=True)
        return {
            "id": None,
            "original_name": original_name,
            "md_name": None,
            "status": "error",
            "error": str(exc) or "Unsupported file type",
            "transcription_engine": transcription_options.engine,
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
    try:
        options = validate_options(request.form)
    except ValueError as exc:
        return jsonify({"files": [], "error": str(exc)}), 400
    results = [convert_single_file(upload, options) for upload in uploads]
    return jsonify({"files": results})


@app.route("/api/transcription/status")
def transcription_capabilities():
    return jsonify(transcription_status())


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
