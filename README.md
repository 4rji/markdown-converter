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
- **Audio:** `.mp3`, `.wav`

## Features

✨ **Drag & Drop Interface** — Drop files directly or browse your computer  
🔄 **Batch Processing** — Convert multiple files at once  
👁️ **Live Preview** — See Markdown before downloading  
💾 **Instant Download** — Get your converted files immediately  
🔒 **Privacy First** — Temporary files are auto-deleted (30 min timeout)  
🤖 **OCR Support** — Extracts text from images using Tesseract  

## Installation

### Prerequisites

- Python 3.9+
- `pip` or your preferred Python package manager
- (Optional) Tesseract for OCR support: `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Linux)

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

## Usage

1. **Upload files** by dragging & dropping or clicking "Browse Files"
2. **Wait for conversion** — Processing happens instantly
3. **Preview** the Markdown content in the built-in viewer
4. **Download** your converted files as `.md` files

Files are stored temporarily and automatically deleted after 30 minutes of inactivity.

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
4. **Download** — Converted Markdown file is served with a single click
5. **Cleanup** — Temporary files are automatically deleted after download or timeout

## Security & Privacy

- Files are stored in temporary directories only
- Automatic cleanup after 30 minutes
- No files are persisted or shared
- Maximum file size: 50 MB per file
- Browser-friendly download headers

## Limitations

- File size limited to 50 MB
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
