"""DigiTech Markdown Converter — Flask server.

Converts uploaded files to Markdown using the markitdown library.
Converted files live in temp directories and are cleaned up after
download or after 30 minutes of inactivity.
"""

import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path

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

MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB per file
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif"}
TEMP_DIR_PREFIX = "mc-"
TEMP_DIR_MAX_AGE_SECONDS = 30 * 60  # 30 minutes
TEMP_ROOT = Path(tempfile.gettempdir())

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE_BYTES

converter = MarkItDown()


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
        result = converter.convert(str(input_path))
        markdown_text = result.text_content
        if input_path.suffix.lower() in IMAGE_EXTENSIONS:
            ocr_text = extract_image_text(input_path)
            if ocr_text:
                markdown_text = (
                    f"{markdown_text}\n\n## Extracted Text (OCR)\n\n{ocr_text}\n"
                )
        output_path.write_text(markdown_text, encoding="utf-8")
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
    directory = md_file.parent
    response = send_file(
        md_file,
        as_attachment=True,
        download_name=md_file.name,
        mimetype="text/markdown",
    )
    response.call_on_close(lambda: shutil.rmtree(directory, ignore_errors=True))
    return response


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({"files": [], "error": "File exceeds the 50 MB limit"}), 413


# Listen on all IPv4 interfaces so the app can be reached from other machines.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=False)
