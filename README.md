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
- **Audio/video transcription:** `.mp3`, `.wav`, `.m4a`, `.mp4`

## Features

✨ **Drag & Drop Interface** — Drop files directly or browse your computer  
🔄 **Batch Processing** — Convert multiple files at once  
👁️ **Live Preview** — See Markdown before downloading  
📋 **Copy Markdown** — Copy converted text without downloading  
💾 **Instant Download** — Get your converted files immediately  
🕘 **Session History** — Keep converted files in the browser tab while they are available  
🔒 **Privacy First** — Temporary files are auto-deleted (30 min timeout)  
🤖 **OCR Support** — Extracts text from images using Tesseract  
🎙️ **Private Transcription** — Runs faster-whisper locally with no remote API  

## Installation

### Prerequisites

- Python 3.9+
- `pip` or your preferred Python package manager
- FFmpeg for audio normalization, including G.711 telephony WAV files
- A local faster-whisper model for audio and video transcription
- (Optional) Tesseract for OCR support: `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Linux)

For Ubuntu CPU-only installation and model download instructions, see
[Local Whisper Setup](docs/local-whisper-setup.md).

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd markdown-converter
   ```

2. **Install dependencies:**
   ```bash
   ./script -i
   ```
   Or manually:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser:**
   ```
   http://SERVER_IP:8082
   ```

The upload limit defaults to 500 MB per file. Override it when starting the
server if needed:

```bash
MAX_UPLOAD_SIZE_MB=1000 python app.py
```

## Usage

1. **Upload files** by dragging & dropping or clicking "Browse Files"
2. **Wait for conversion** — Processing happens instantly
3. **Preview or copy** the Markdown content in the built-in viewer
4. **Download** your converted files as `.md` files when needed

Files are stored temporarily and automatically deleted after 30 minutes of inactivity.
The browser stores only session metadata for the result list, not file content.

## Architecture

Built with:

- **Flask** — Lightweight Python web framework
- **MarkItDown** — Powerful document-to-Markdown converter
- **faster-whisper** — Local CPU speech-to-text transcription
- **FFmpeg** — Audio extraction and codec normalization
- **Tesseract OCR** — Optional image text extraction
- **Vanilla JavaScript** — No build step required
- **Responsive CSS** — Mobile-friendly design

## How It Works

1. **Upload** — Files are securely uploaded and stored in temporary directories
2. **Convert** — MarkItDown handles documents; FFmpeg and local Whisper handle audio
3. **Enhance** — For images, optional OCR extracts visible text
4. **Use** — Converted Markdown can be previewed, copied, or downloaded
5. **Cleanup** — Temporary files remain available during the session and are automatically deleted after timeout

## Security & Privacy

- Files are stored in temporary directories only
- Automatic cleanup after 30 minutes
- No file contents are persisted permanently or shared
- No external browser assets or remote transcription services are used
- Local Whisper loads only the model directory configured on the server
- Audio normalization and transcription are limited to one job at a time
- Maximum file size: 500 MB per file by default (configurable with `MAX_UPLOAD_SIZE_MB`)
- Browser-friendly download headers

Direct audio and video uploads bypass MarkItDown's remote audio converter and
use only the locally configured faster-whisper model. The remote converter is
also unregistered, so audio inside ZIP archives cannot invoke it.

## Limitations

- File size limited to 500 MB by default
- Some complex layouts may lose formatting details
- OCR quality depends on image clarity
- Audio transcription requires FFmpeg and a configured local model directory
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
