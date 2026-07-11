# Markdown Converter

**Anything in. Markdown out.**

Transform any document into clean, LLM-friendly Markdown. Convert PDFs, Office documents, images, and more with a single click.

![Markdown Converter App](./app.webp)

## Why Markdown?

Markdown is the language LLMs understand best. Converting your files to Markdown:

- **Strips away layout noise** — Removes formatting clutter and preserves clean structure
- **Improves accuracy** — Models like ChatGPT and Claude read your content more accurately
- **Saves tokens** — Use fewer tokens in API calls, reducing costs
- **Gets better answers** — Cleaner input leads to higher-quality responses from AI models

## Supported File Formats

- **Documents:** `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.html`, `.txt`, `.csv`, `.json`, `.xml`
- **Office formats:** Microsoft Word, Excel, PowerPoint
- **Web content:** HTML files
- **Images:** `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`
- **Archives:** `.zip`, `.epub`
- **Audio/video transcription:** `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`, `.webm`, `.mp4`

## Features

✨ **Drag & Drop Interface** — Drop files directly or browse your computer  
🔄 **Batch Processing** — Convert multiple files at once  
👁️ **Live Preview** — See Markdown before downloading  
📋 **Copy Markdown** — Copy converted text without downloading  
💾 **Instant Download** — Get your converted files immediately  
🕘 **Session History** — Keep converted files in the browser tab while they are available  
🔒 **Privacy First** — Temporary files are auto-deleted (30 min timeout)  
🤖 **OCR Support** — Extracts text from images using Tesseract  
🎙️ **Selectable Transcription** — GPT-4o, speaker diarization, or private Local Whisper

## Installation

### Prerequisites

- Python 3.9+
- `pip` or your preferred Python package manager
- FFmpeg for audio normalization, including G.711 telephony WAV files
- An `OPENAI_API_KEY` for cloud audio transcription and/or a local faster-whisper model
- (Optional) Tesseract for OCR support: `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Linux)

For Pop!_OS, NVIDIA CUDA, and local model setup instructions, see
[Local Whisper Setup](docs/local-whisper-setup.md).

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd markdown-converter
   ```

2. **Install the application dependencies:**

   ```bash
   ./script -i
   ```

   This creates or reuses the repository's `.venv` environment and installs
   `requirements.txt` into it. Run this command as your normal user—do not use
   `sudo`. The Local Whisper installer invokes `sudo` itself only for the
   system packages and model directory that require it. On Ubuntu/Pop!_OS, the
   script detects the active Python version and installs both `python3-venv` and
   its version-specific package, such as `python3.10-venv`, when needed.

3. **Install Local Whisper with NVIDIA CUDA (recommended for private audio):**

   ```bash
   ./install_whisper_local.sh
   ```

   Run this after `./script -i`. Both scripts use the same `.venv`. The Local
   Whisper installer checks the NVIDIA GPU, installs the CUDA runtime packages,
   downloads `large-v3-turbo`, validates a CUDA/float16 model load, and writes
   the required paths to `.env`.

   This step requires Pop!_OS/Ubuntu, `sudo`, and a working NVIDIA driver. It is
   optional if you only intend to use document conversion or OpenAI audio
   transcription.

4. **Load the Local Whisper configuration:**

   ```bash
   set -a
   source .env
   set +a
   ```

   Repeat this in each new shell before starting the application. For a systemd
   deployment, configure the service to read this file with `EnvironmentFile=`.

5. **Configure OpenAI transcription (optional):**

   ```bash
   export OPENAI_API_KEY="your-key-here"
   ```

   Keep the real key in the server environment or a secret manager. Do not add
   it to the repository.

6. **Run the application using the shared environment:**

   ```bash
   .venv/bin/python app.py
   ```

7. **Open your browser:**

   ```
   http://SERVER_IP:8082
   ```

The complete Local Whisper installation sequence is therefore:

```bash
./script -i
./install_whisper_local.sh
set -a
source .env
set +a
.venv/bin/python app.py
```

To install the Python dependencies without the helper script, use:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The upload limit defaults to 500 MB per file. Override it when starting the
server if needed:

```bash
MAX_UPLOAD_SIZE_MB=1000 .venv/bin/python app.py
```

## Usage

1. **Upload files** by dragging & dropping or clicking "Browse Files"
2. **For audio/video, choose an engine and options**, then click "Convert Files"
3. **Preview or copy** the Markdown content in the built-in viewer
4. **Download** your converted files as `.md` files when needed

Files are stored temporarily and automatically deleted after 30 minutes of inactivity.
The browser stores only session metadata for the result list, not file content.

## Architecture

Built with:

- **Flask** — Lightweight Python web framework
- **MarkItDown** — Powerful document-to-Markdown converter
- **OpenAI Python SDK** — GPT-4o transcription and speaker diarization
- **faster-whisper** — Private CUDA speech-to-text transcription
- **FFmpeg** — Audio extraction and codec normalization
- **Tesseract OCR** — Optional image text extraction
- **Vanilla JavaScript** — No build step required
- **Responsive CSS** — Mobile-friendly design

## How It Works

1. **Upload** — Files are securely uploaded and stored in temporary directories
2. **Convert** — MarkItDown handles documents; FFmpeg prepares audio for the selected OpenAI or Local Whisper engine
3. **Enhance** — For images, optional OCR extracts visible text
4. **Use** — Converted Markdown can be previewed, copied, or downloaded
5. **Cleanup** — Temporary files remain available during the session and are automatically deleted after timeout

## Security & Privacy

- Files are stored in temporary directories only
- Automatic cleanup after 30 minutes
- No file contents are persisted permanently
- Documents stay local; audio is sent to OpenAI only when a GPT-4o engine is selected
- Local Whisper loads only the model directory configured on the server
- Local GPU transcription jobs are limited to one at a time
- Maximum file size: 500 MB per file by default (configurable with `MAX_UPLOAD_SIZE_MB`)
- Browser-friendly download headers

Direct audio and video uploads bypass MarkItDown's audio converter and use only
the explicitly selected engine. Local Whisper never makes a transcription API
request. The MarkItDown remote audio converter remains unregistered.

## Limitations

- File size limited to 500 MB by default
- Some complex layouts may lose formatting details
- OCR quality depends on image clarity
- Audio transcription requires FFmpeg plus either `OPENAI_API_KEY` or a configured CUDA local model
- Unsupported file types will return an error

## Development

### Project Structure

```
markdown-converter/
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html     # Web interface
└── static/
    ├── style.css      # Styling
    └── app.js         # Client-side logic
```

### Running Tests

```bash
pytest tests/
```

## License

MIT License — See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Made with ❤️ by the Markdown Converter team**
