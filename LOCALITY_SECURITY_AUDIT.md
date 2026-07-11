# Local-Only Processing Security Audit

> **Historical result:** This report covers the former in-process MarkItDown
> integration using `LocalOnlyRequestsSession`. Document conversion now invokes
> the virtual environment's `markitdown` CLI to match the standalone `script`,
> so the subprocess-based implementation requires a new network-locality audit.

**Audit date:** July 10, 2026  
**Project:** Markdown Converter
**Result:** Passed, with the qualifications documented below

## Objective

Verify that files submitted to the application are processed on the Flask
server without uploading file contents to third-party APIs, downloading remote
resources referenced by a file, or loading remote browser assets.

In this report, **local** means local to the server running the application.
When a user opens the application from another computer, the browser still
uploads the selected file to that server over the application's same-origin
`/convert` endpoint. The application is not a client-only converter.

## Scope

The audit covered:

- Flask upload, conversion, preview, and download routes
- MarkItDown converter configuration and registered converters
- Local OCR through Tesseract
- Local audio normalization through FFmpeg
- Local audio transcription configuration through faster-whisper
- Browser JavaScript, HTML, CSS, images, and Content Security Policy
- Runtime behavior when documents contain remote URLs or external relations

Dependency installation, repository cloning, and the one-time download of a
local Whisper model were considered setup activities, not runtime file
processing. Those setup operations require network access when performed.

## Static Code Review

### Backend controls

The following controls were confirmed in [`app.py`](app.py):

- `LocalOnlyRequestsSession` rejects every request made through MarkItDown's
  HTTP session.
- MarkItDown's `AudioConverter` is explicitly unregistered. This also prevents
  audio nested inside ZIP archives from invoking its remote transcription
  path.
- No LLM client or remote API client is supplied to the image or PowerPoint
  converters.
- Direct audio and video uploads use FFmpeg followed by faster-whisper.
- Whisper receives a filesystem model path and `local_files_only=True`.
- `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, telemetry, and update-check
  environment controls are enabled before the model is loaded.
- Tesseract receives a local filesystem image and runs as a local process.
- Uploaded files and generated Markdown are stored under temporary server
  directories and are removed after the configured inactivity period.

### Browser controls

The following controls were confirmed in [`static/app.js`](static/app.js),
[`templates/index.html`](templates/index.html), and
[`static/style.css`](static/style.css):

- Uploads use the relative same-origin route `/convert`.
- Preview, copy, and download operations use relative `/preview/...` and
  `/download/...` routes.
- JavaScript, CSS, icons, and logos are served by the application. No CDN,
  remote font, analytics, tracking, or telemetry asset is loaded.
- Markdown previews are inserted with `textContent`. Remote image or link URLs
  contained in converted Markdown are therefore displayed as text and are not
  fetched by the preview.
- The response Content Security Policy restricts scripts, styles, images,
  fonts, forms, and connections to the application's own origin, except for
  inline styles and `data:` images explicitly allowed by the policy.

## Runtime Network Test

The Flask test client was used to perform actual conversions while Python's
DNS and socket connection entry points were instrumented to record and reject
network access. The instrumentation covered `socket.connect`, `connect_ex`,
`create_connection`, and `getaddrinfo`.

The following samples were submitted:

| Sample | Adversarial or relevant content | Result |
| --- | --- | --- |
| TXT | Plain local text | Converted |
| CSV | Local tabular data | Converted |
| JSON | Local structured data | Converted |
| XML | External HTTP entity declaration | Converted without a network attempt |
| HTML | Remote stylesheet, image, and hyperlink URLs | Converted without fetching them |
| PNG | Local raster image and OCR path | Converted |
| PDF | Local image PDF | Converted |
| XLSX | Local workbook | Converted |
| PPTX | Local presentation | Converted |
| DOCX | External hyperlink relationship | Converted without following it |
| ZIP | HTML with a remote image plus a fake nested MP3 | Converted without a network attempt |

**Observed Python DNS or socket attempts: 0.**

The active MarkItDown instance was also inspected at runtime:

- HTTP session class: `LocalOnlyRequestsSession`
- Registered `AudioConverter` instances: 0
- MarkItDown version tested: 0.1.6
- Requests version tested: 2.32.3

## FFmpeg Subprocess Test

FFmpeg runs outside the Python process, so the Python socket instrumentation
does not cover it. It was tested separately with a local HTTP listener that
recorded requests.

Two crafted inputs, named with an application-accepted multimedia extension,
contained references to the listener:

1. An HLS-style playlist containing an HTTP media segment
2. An FFconcat-style input containing an HTTP file reference

FFmpeg rejected both crafted inputs. The local listener recorded **0 HTTP
requests**. A normal media upload is still passed to FFmpeg by local filesystem
path.

## External URL Inventory

The runtime interface contains one external URL:

- `https://4rji.com` in the footer credit

This is a user-initiated hyperlink, not an automatically loaded resource. It
uses `noopener noreferrer`, is not involved in conversion, and does not send
file contents. If the policy requires the application to contain no external
destinations at all, this link should be removed or changed to plain text.

Converted files may themselves contain hyperlinks or image URLs copied from
their source documents. The application does not fetch those URLs during
conversion or preview. Another Markdown viewer could fetch them later if a
user opens the downloaded output and follows a link or renders remote images;
that behavior is outside this application's runtime.

## Audio Environment Observation

The environment used for this audit did not have `faster-whisper` installed
and did not have `WHISPER_MODEL_PATH` configured. A direct MP3 upload therefore
returned a local configuration error before transcription. It did **not** fall
back to a remote API.

`faster-whisper` is declared in [`requirements.txt`](requirements.txt). A
production deployment must install it and provide an already downloaded local
model directory for audio transcription to work.

## Qualifications and Residual Risk

- The audit establishes the behavior of the reviewed code and installed
  dependency versions; it is not a mathematical guarantee for every future
  file parser or dependency release.
- Dependency versions are not pinned exactly. A future installation can
  receive different converter behavior and should be retested.
- The application provides code-level controls, but it does not create an
  operating-system-level egress firewall. A host firewall or container network
  policy is the strongest independent guarantee that no process can reach the
  public network.
- Any future converter, plugin, analytics package, remote asset, or LLM client
  must be reviewed before deployment.

## Recommended Regression Controls

1. Pin or lock production dependency versions.
2. Add the instrumented conversion checks to the automated test suite.
3. Run the production service with outbound network access denied when a
   strict no-egress guarantee is required.
4. Retest after upgrades to MarkItDown, faster-whisper, FFmpeg, Tesseract, or
   document parser dependencies.
5. Optionally remove the footer hyperlink if the requirement is literally zero
   external URLs, including user-initiated navigation.

## Conclusion

No automatic external request or third-party file upload was observed during
the reviewed conversion paths. Documents containing remote references were
processed without resolving or fetching those references. Browser assets and
application requests are same-origin, and remote audio and LLM conversion
paths are not enabled.

Subject to the qualifications above, the application satisfies the stated
requirement that file conversion occur locally on the application server.
