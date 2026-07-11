# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Markdown Converter is a Flask web application that converts any document into clean, LLM-friendly Markdown. It supports PDFs, Office documents, images, archives, and audio/video files. The core conversion uses the MarkItDown library; audio/video transcription routes through either OpenAI's GPT-4o model or a private local Whisper instance for privacy-sensitive deployments.

## Setup & Common Commands

**Install dependencies:**
```bash
./script -i
```
This creates `.venv/`, installs `requirements.txt`, and prints next steps.

**Run the application:**
```bash
source .venv/bin/activate
python app.py
```
Server listens on `0.0.0.0:8082` by default. Open `http://localhost:8082` in a browser.

**Run tests:**
```bash
python -m pytest tests/
```

**Reinstall MarkItDown (after version updates):**
```bash
./script -r
```

**Set environment variables (optional):**
- `MAX_UPLOAD_SIZE_MB` (default: 500) — upload size limit
- `FFMPEG_TIMEOUT_SECONDS` (default: 600) — audio processing timeout
- `WHISPER_BEAM_SIZE` (default: 5) — Whisper decoding beam width
- `OPENAI_API_KEY` — for cloud transcription (optional; required only for OpenAI transcription)

For local Whisper setup on systems with NVIDIA CUDA:
```bash
./install_whisper_local.sh
```
`app.py` auto-loads `.env` at startup via `env_loader.py` (re-execs once when `.env` adds `LD_LIBRARY_PATH`, since the dynamic linker only reads it at process start). No manual `source .env` needed.

## Architecture

### Request Flow
1. **Upload** (`POST /convert`) — client sends files via multipart; `convert_single_file()` processes each one
2. **Convert** — route by file type:
   - **Audio/video** (`suffix in AUDIO_EXTENSIONS`) → calls `transcribe()` (from `transcription.py`); result becomes Markdown via `render_markdown()`
   - **Documents/archives** → `markitdown` CLI from the application's virtualenv
   - **Images** → `markitdown` CLI + optional OCR extraction via Tesseract
3. **Store** — converted Markdown saved to a temp directory named `mc-<uuid>`; returned as JSON with file ID
4. **Retrieve** — client calls `GET /preview/<id>` or `GET /download/<id>` to read/download the `.md` file
5. **Cleanup** — temp directories auto-delete after 30 minutes (`TEMP_DIR_MAX_AGE_SECONDS`); cleanup check runs before each request

### Core Modules

- **app.py** — Flask server; file upload, routing, temp management, OCR integration
- **transcription.py** — pluggable transcription backends (OpenAI cloud vs. local Whisper); validates user options; renders segment data into Markdown

### Key Design Patterns

**Security & Privacy:**
- Audio/video extensions are routed to the selected transcription engine before the MarkItDown CLI can be invoked
- Temp directories isolated to `tempfile.gettempdir()` for automatic OS cleanup
- CSP headers prevent external script/style injection
- File uploads validated via `secure_filename()`

**Transcription Options:**
- Defined in `Options` dataclass (engine, language, context, include_timestamps)
- Three engines: `openai` (cloud), `openai_diarize` (cloud with speaker IDs), `local_whisper` (GPU)
- Local Whisper jobs serialized via `audio_processing_lock` to avoid GPU contention; cloud jobs run in parallel
- Input validation in `validate_options()` — e.g., timestamps not supported for plain OpenAI

**Optional Features:**
- OCR (Tesseract) gracefully degrades: if `pytesseract` or binary not found, images convert without text extraction
- Environment offline mode prevents model downloads (`HF_HUB_OFFLINE=1`, etc.)

## Testing & Verification

**Unit tests** in `tests/test_transcription.py` cover:
- Default option validation
- Engine-specific constraints (e.g., timestamps)
- Markdown rendering for diarized vs. local transcripts
- Transcription status endpoint

**Manual testing workflow:**
1. Start the app locally
2. Upload test files (PDF, image, audio file)
3. Verify conversion in the browser preview
4. Check temp directory cleanup after 30 minutes

**Common test file types:**
- PDFs, DOCX, PPTX, XLSX, CSV, JSON, XML — covered by MarkItDown
- PNG, JPG with text — test OCR extraction
- MP3, WAV, M4A — test transcription engines

## Common Issues & Patterns

**No Markdown file found (404 on preview/download):**
- Conversion failed (check error in response); file ID doesn't correspond to a valid temp directory

**OCR text not in output:**
- Tesseract not installed (`brew install tesseract` on macOS, `apt-get install tesseract-ocr` on Linux)
- Image is not in `IMAGE_EXTENSIONS` set

**Transcription fails or times out:**
- FFMPEG_TIMEOUT_SECONDS too short for long audio; increase it or check FFmpeg installation
- OpenAI: missing or invalid `OPENAI_API_KEY`
- Local Whisper: model not in expected path or CUDA misconfigured

**Upload limit exceeded:**
- Raise `MAX_UPLOAD_SIZE_MB` environment variable before starting the app

## Browser UI

The frontend (`static/app.js`, `templates/index.html`) is vanilla JavaScript with no build step. It:
- Manages drag-drop file upload
- Collects transcription options (engine, language, timestamps)
- Polls `/api/transcription/status` to show available engines
- Displays preview and download links for each converted file
- Persists session history in browser memory (clears on tab close)

## Deployment

**Local development:**
```bash
python app.py
```

**Production with systemd (Pop!_OS/Ubuntu):**
```bash
sudo ./install-systemd-service_new.sh
```
Installs to `/opt/markdown-converter`, sets up service, reuses `.env` with corrected CUDA paths.

Useful systemd commands:
```bash
sudo systemctl status markdown-converter
sudo journalctl -u markdown-converter -f
curl -s http://127.0.0.1:8082/api/transcription/status
```

To skip Local Whisper on serverless/non-GPU deployments:
```bash
sudo INSTALL_LOCAL_WHISPER=0 ./install-systemd-service_new.sh
```
