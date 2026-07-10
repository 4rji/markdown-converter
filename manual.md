# DigiTech Markdown Converter User Manual

## 1. Overview

DigiTech Markdown Converter turns supported files into clean Markdown files.
You can upload one file or several files at once, inspect the converted content,
copy it, or download it as a `.md` file.

The original files are not changed. Each successful conversion creates a
separate Markdown result.

## 2. Supported Formats

| Category | Supported formats | Result |
| --- | --- | --- |
| Documents | `.pdf` | Text and supported document structure in Markdown |
| Word documents | `.docx` | Text and supported document structure in Markdown |
| Presentations | `.pptx` | Slide content in Markdown |
| Spreadsheets | `.xlsx` | Spreadsheet content in Markdown tables or structured text |
| Web and text files | `.html`, `.txt` | Readable text and supported structure in Markdown |
| Delimited and structured data | `.csv`, `.json`, `.xml` | Data represented as readable Markdown |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.tif` | Image information and, when readable, extracted text |
| Archives and ebooks | `.zip`, `.epub` | Supported contents represented in Markdown |
| Audio and video | `.mp3`, `.wav`, `.m4a`, `.mp4` | A Markdown transcript of detected speech |

Audio and video files must contain an audio track. Image text extraction depends
on the clarity and legibility of the image. Complex layouts may not preserve
every visual detail.

## 3. Converting Files

### 3.1 Upload by Dragging

1. Open the converter page.
2. Drag one or more files onto the **Drag & drop your files** area.
3. Release the files inside the upload area.
4. Wait for the upload and conversion to finish.

### 3.2 Upload by Browsing

1. Click **Browse Files**, or click anywhere inside the upload area.
2. Select one or more files from the file picker.
3. Confirm the selection.
4. Wait for the upload and conversion to finish.

Multiple files can be selected in one operation. Each file receives its own
result, and an error in one file does not remove successful results from the
same batch.

### 3.3 Progress Status

The progress area shows the current stage:

- **Uploading** shows the upload percentage when progress is available.
- **Converting** indicates that the file is being processed.
- The progress area disappears when the request finishes.

## 4. Converted Files

Successful files appear in the **Converted Files** list. The output name uses
the original file name with its extension replaced by `.md`. For example,
`report.pdf` becomes `report.md`.

Every successful result provides these actions:

- **View** opens the converted Markdown in the visualizer.
- **Copy** copies the complete Markdown source to the clipboard without
  downloading a file.
- **Download** downloads the Markdown result as a `.md` file.

The result list remains available while the corresponding temporary result is
available. Downloading a file does not remove it from the list.

Failed conversions appear with an error indicator and a message. They do not
provide View, Copy, or Download actions.

## 5. Markdown Visualizer

Click **View** on a successful result to open the **Markdown Visualizer**.
The visualizer presents the converted content as a readable document and can
display common Markdown elements such as:

- Headings
- Paragraphs and line breaks
- Bulleted and numbered lists
- Tables
- Links and images
- Block quotes
- Inline code and code blocks
- Horizontal rules

The visualizer has its own scroll area for long documents. Its footer provides:

- **Copy** to copy the Markdown source.
- **Download** to download the current result as a `.md` file.

To close the visualizer, click the close button, click outside the panel, or
press `Escape`.

## 6. Copying Markdown

You can copy a result in either of two ways:

1. Click **Copy** beside a file in the results list.
2. Open **View**, then click **Copy** in the visualizer footer.

While the copy operation is running, the button shows **Copying**. A
successful operation shows **Copied**, and a failed operation shows **Failed**
before the button returns to its normal state.

The copied content is the original Markdown source, not the visual styling
shown in the visualizer.

## 7. Session History

Successful results are kept in the current browser tab's session history so
they can be restored after reloading the page while the temporary files are
still available.

- Up to 50 successful results are retained in the session history.
- Only result information such as the name and identifier is remembered; the
  Markdown content is not stored in the history.
- Expired results may remain visible until an action is attempted, but their
  preview or download will no longer be available.
- Click **Clear history** to remove all entries from the visible list and close
  any open preview.

Clearing the history does not change or delete the original files. Converted
files are temporary and are removed automatically after 30 minutes of
inactivity.

## 8. Theme

Click the theme button in the upper-right corner to switch between:

- **Dark theme**, the default appearance.
- **Light theme**.

The selected theme is remembered for future visits in the same browser.

## 9. Keyboard Use

The upload area can be operated without a mouse:

- Focus the upload area and press `Enter` or `Space` to choose files.
- Use the standard keyboard controls to activate buttons.
- Press `Escape` to close an open visualizer.

The layout also adapts to smaller screens, so uploading and managing results
remains available on mobile-sized displays.

## 10. Limits and Common Errors

- The default maximum size is **500 MB per file**.
- A file with an empty or unusable name cannot be converted.
- Unsupported or damaged files return an error instead of a Markdown result.
- Audio or video without a usable audio track cannot produce a transcript.
- If an operation fails, read the message shown beside the affected file and
  upload a supported, readable file again if necessary.

## 11. File Availability and Privacy

Converted results are temporary. They are automatically cleared after 30
minutes without activity, so download or copy important content before it
expires. Viewing, copying, or downloading a result counts as activity while
the result is still available.

File processing stays within the server that provides the converter. Files are
not kept as permanent application records or shared with external services.
