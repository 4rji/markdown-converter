# Run Markdown Converter as a systemd Service

The production installer deploys the current repository to
`/opt/markdown-converter` and configures it to start automatically at boot.
These instructions target Pop!_OS/Ubuntu with systemd.

## Complete installation

From the source repository, run:

```bash
sudo ./install-systemd-service_new.sh
```

The installer:

- installs Python, the version-specific `pythonX.Y-venv` package, FFmpeg,
  Tesseract, and required system libraries;
- creates the `markdown-converter` service account;
- synchronizes the repository to `/opt/markdown-converter` without deleting the
  source checkout;
- creates `/opt/markdown-converter/.venv` and installs `requirements.txt`;
- installs the pip CUDA runtime packages;
- reuses or downloads `large-v3-turbo` under `/opt/whisper-models`;
- validates CUDA and float16 model loading;
- copies `.env`, preserves `OPENAI_API_KEY`, and recalculates
  `LD_LIBRARY_PATH` for the `/opt` virtual environment;
- writes, enables, and starts `markdown-converter.service`.

The command is safe to run again when deploying application or dependency
updates. Existing systemd units are backed up before replacement.

## Environment variables and secrets

The deployed environment file is:

```text
/opt/markdown-converter/.env
```

It is owned by the service account with mode `0600`. Add the OpenAI key there:

```bash
sudo nano /opt/markdown-converter/.env
```

```dotenv
OPENAI_API_KEY=replace_with_your_real_key
```

Then restart the service:

```bash
sudo systemctl restart markdown-converter
```

The systemd unit loads all variables through:

```ini
EnvironmentFile=/opt/markdown-converter/.env
```

Do not put the real key in `.env.example`, source control, or the unit file.

## Optional installer settings

Skip Local Whisper on a server without NVIDIA CUDA:

```bash
sudo INSTALL_LOCAL_WHISPER=0 ./install-systemd-service_new.sh
```

Skip Tesseract OCR:

```bash
sudo INSTALL_TESSERACT=0 ./install-systemd-service_new.sh
```

Use a Hugging Face token for the initial model download:

```bash
sudo HF_TOKEN=your_read_token ./install-systemd-service_new.sh
```

Alternative locations and names can be supplied through `APP_DIR`, `MODEL_DIR`,
`SERVICE_NAME`, `APP_USER`, and `APP_GROUP`.

## Operations

Check the service:

```bash
sudo systemctl status markdown-converter
```

Follow logs, including Local Whisper runtime states:

```bash
sudo journalctl -u markdown-converter -f
```

Restart or stop it:

```bash
sudo systemctl restart markdown-converter
sudo systemctl stop markdown-converter
```

Confirm transcription capabilities:

```bash
curl -s http://127.0.0.1:8082/api/transcription/status
```

The application listens on `0.0.0.0:8082`. Configure the host firewall and a
reverse proxy as appropriate for the deployment.
