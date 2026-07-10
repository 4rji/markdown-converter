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
- **Audio:** `.mp3`, `.wav`, `.m4a`, `.mp4` (requires a local Whisper model)

## Features

✨ **Drag & Drop Interface** — Drop files directly or browse your computer  
🔄 **Batch Processing** — Convert multiple files at once  
👁️ **Live Preview** — See Markdown before downloading  
📋 **Copy Markdown** — Copy converted text without downloading  
💾 **Instant Download** — Get your converted files immediately  
🕘 **Session History** — Keep converted files in the browser tab while they are available  
🔒 **Privacy First** — Temporary files are auto-deleted (30 min timeout)  
🤖 **OCR Support** — Extracts text from images using Tesseract  

## Installation

### Prerequisites

- Python 3.9+
- `pip` or your preferred Python package manager
- FFmpeg for automatic conversion of telephony WAV codecs such as G.711 μ-law
- A faster-whisper model directory stored locally for audio transcription
- (Optional) Tesseract for OCR support: `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Linux)

Install FFmpeg with `brew install ffmpeg` on macOS or `apt-get install ffmpeg`
on Debian/Ubuntu.

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

Audio transcription is disabled until a local faster-whisper model is supplied.
The application never downloads a model or sends audio to a transcription API:

```bash
WHISPER_MODEL_PATH=/absolute/path/to/local-whisper-model python app.py
```

Optional settings are `WHISPER_LANGUAGE` (blank means automatic detection),
`WHISPER_DEVICE` (defaults to `cpu`), and `WHISPER_COMPUTE_TYPE` (defaults to
`int8`). The model directory must already exist on the server.

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
- **Tesseract OCR** — Optional image text extraction
- **Vanilla JavaScript** — No build step required
- **Responsive CSS** — Mobile-friendly design

## How It Works

1. **Upload** — Files are securely uploaded and stored in temporary directories
2. **Convert** — The MarkItDown library processes the file and extracts text
3. **Enhance** — For images, optional OCR extracts visible text
4. **Use** — Converted Markdown can be previewed, copied, or downloaded
5. **Cleanup** — Temporary files remain available during the session and are automatically deleted after timeout

## Security & Privacy

- Files are stored in temporary directories only
- Automatic cleanup after 30 minutes
- No file contents are persisted permanently or shared
- No external browser assets or remote transcription services are used
- Local Whisper model downloads are disabled at runtime
- Maximum file size: 500 MB per file by default (configurable with `MAX_UPLOAD_SIZE_MB`)
- Browser-friendly download headers

## Limitations

- File size limited to 500 MB by default
- Some complex layouts may lose formatting details
- OCR quality depends on image clarity
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
