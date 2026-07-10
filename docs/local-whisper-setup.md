# Local Whisper Setup on Ubuntu 24.04

This guide enables private, CPU-only transcription for WAV, G.711 mu-law WAV,
MP3, M4A, and MP4 uploads. Audio is normalized by FFmpeg and transcribed by a
local faster-whisper model. Uploaded media is never sent to Google, OpenAI, or
any other transcription service.

The recommended configuration for a 4-vCPU, 4 GB RAM virtual machine is:

- Model: multilingual `base` (`Systran/faster-whisper-base`), not `base.en`
- Device: CPU
- Compute type: INT8
- OpenMP threads: 4
- Concurrent audio jobs: 1 (enforced by the application)

## 1. Install System Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg libgomp1
```

FFmpeg provides consistent decoding for telephony WAV codecs such as G.711
mu-law. `libgomp1` provides the GNU OpenMP runtime used for CPU inference.

## 2. Install the Application Dependencies

These examples assume the application is installed at
`/opt/markdown-converter` and runs as the `markdown-converter` user.

```bash
sudo -u markdown-converter python3 -m venv /opt/markdown-converter/.venv
sudo -u markdown-converter /opt/markdown-converter/.venv/bin/pip install --upgrade pip
sudo -u markdown-converter /opt/markdown-converter/.venv/bin/pip install -r /opt/markdown-converter/requirements.txt
```

## 3. Download the Model Once

This is the only step that requires an outbound Internet connection. It
downloads model files only; it does not upload any audio or application data.

Create a model directory owned by the service account:

```bash
sudo install -d -o markdown-converter -g markdown-converter /opt/models/faster-whisper-base
```

Install the Hugging Face CLI in the application virtual environment:

```bash
sudo -u markdown-converter /opt/markdown-converter/.venv/bin/pip install --upgrade huggingface_hub
```

Download the multilingual CTranslate2 `base` model into the fixed local
directory:

```bash
sudo -u markdown-converter /opt/markdown-converter/.venv/bin/hf download Systran/faster-whisper-base --local-dir /opt/models/faster-whisper-base
```

Confirm that the model directory contains files such as `config.json`,
`model.bin`, `tokenizer.json`, and `vocabulary.txt`:

```bash
sudo -u markdown-converter find /opt/models/faster-whisper-base -maxdepth 1 -type f -printf '%f\n' | sort
```

The application passes an absolute directory path to faster-whisper and sets
offline environment flags at startup. It never uses a model name that could
trigger an automatic runtime download.

## 4. Optional: Add Swap

Four GB of swap is recommended for a VM with only 4 GB of RAM. It provides a
safety margin during model loading and large document conversions.

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Verify it:

```bash
swapon --show
free -h
```

Skip the creation commands if the server already has sufficient swap.

## 5. Configure systemd

Edit the existing unit:

```bash
sudo nano /etc/systemd/system/markdown-converter.service
```

The service section should include these settings:

```ini
[Service]
Type=simple
User=markdown-converter
Group=markdown-converter
WorkingDirectory=/opt/markdown-converter
Environment=PYTHONUNBUFFERED=1
Environment=MAX_UPLOAD_SIZE_MB=500
Environment=WHISPER_MODEL_PATH=/opt/models/faster-whisper-base
Environment=WHISPER_BEAM_SIZE=5
Environment=FFMPEG_TIMEOUT_SECONDS=600
Environment=OMP_NUM_THREADS=4
ExecStart=/opt/markdown-converter/.venv/bin/python /opt/markdown-converter/app.py
Restart=always
RestartSec=5
```

Do not configure multiple application workers on this VM. The application
serializes audio normalization and transcription with an in-process lock, so
only one audio job uses CPU and memory at a time.

Reload and restart systemd after editing the unit:

```bash
sudo systemctl daemon-reload
sudo systemctl restart markdown-converter
sudo systemctl status markdown-converter --no-pager
```

## 6. Test Local Transcription

Upload a short WAV or MP3 from the web interface, or test the endpoint directly:

```bash
curl -sS -F 'files=@/path/to/test.wav' http://127.0.0.1:8082/convert
```

View logs while testing:

```bash
sudo journalctl -u markdown-converter -f
```

The first audio request loads the model and therefore takes longer. Later
requests reuse the same in-memory model.

## 7. Optional Language Setting

Language detection is automatic by default. To force Spanish, add this to the
systemd service:

```ini
Environment=WHISPER_LANGUAGE=es
```

Run `systemctl daemon-reload` and restart the service after changing it.

## Troubleshooting

### Local model directory not found

Confirm the path and service-user permissions:

```bash
sudo -u markdown-converter test -r /opt/models/faster-whisper-base/model.bin
```

### FFmpeg is missing

```bash
sudo apt install -y ffmpeg
```

### The service is killed while loading the model

Check memory and swap with `free -h`, then inspect the kernel log:

```bash
sudo journalctl -k -g 'Out of memory\|Killed process'
```

Use the multilingual `base` model, keep `OMP_NUM_THREADS=4`, and ensure only one
service process is running.

### Runtime privacy

The browser is restricted to same-origin connections by Content Security
Policy. MarkItDown outbound requests are blocked, its remote audio converter is
unregistered, and faster-whisper is loaded with `local_files_only=True` plus
offline environment flags.
