# Audio Transcription Setup on Pop!_OS 22.04

The converter offers two independent transcription paths:

- OpenAI: `gpt-4o-transcribe` and `gpt-4o-transcribe-diarize`
- Private/local: faster-whisper `large-v3-turbo` on NVIDIA CUDA

Missing cloud configuration does not affect local or document conversion.
Missing local dependencies only disables the Local Whisper choice.

## System and NVIDIA prerequisites

These instructions target Pop!_OS 22.04 and an RTX 3070. Install the current
System76 NVIDIA driver and verify that the GPU is visible:

```bash
sudo apt update
sudo apt install -y system76-driver-nvidia ffmpeg libgomp1 python3-venv
nvidia-smi
ffmpeg -version
```

Install the application dependencies in a virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

The faster-whisper/CTranslate2 build must support the CUDA and cuDNN versions
installed on the host. Confirm detection before starting the service:

```bash
python -c 'import ctranslate2; print(ctranslate2.get_cuda_device_count())'
```

The result must be at least `1`.

## Download large-v3-turbo once

Model download is an explicit administration step. The application never
downloads a model during startup or a request.

```bash
python -m pip install huggingface_hub
huggingface-cli download Systran/faster-whisper-large-v3-turbo \
  --local-dir /srv/models/faster-whisper-large-v3-turbo
```

You may use another compatible CTranslate2 `large-v3-turbo` repository. Set
`WHISPER_MODEL_PATH` to its local directory; do not commit a machine-specific
path or secret to the repository.

```bash
export WHISPER_MODEL_PATH=/srv/models/faster-whisper-large-v3-turbo
```

At first use, the app loads that directory with `device="cuda"`,
`compute_type="float16"`, and `local_files_only=True`. The successful model is
cached in memory. Transcription uses VAD and local jobs are serialized.

## Configure OpenAI (optional)

Set the API key only in the server environment or secret manager:

```bash
export OPENAI_API_KEY='your-key-here'
```

Never put the value in source control or frontend configuration. The browser
does not receive the key. When the key is absent, document conversion and Local
Whisper continue to work; choosing a GPT-4o engine returns a configuration
error for the affected audio file.

For systemd, add environment references using your deployment's secret-loading
method, then restart the service. A minimal non-secret configuration is:

```ini
[Service]
Environment=WHISPER_MODEL_PATH=/srv/models/faster-whisper-large-v3-turbo
Environment=WHISPER_BEAM_SIZE=5
Environment=FFMPEG_TIMEOUT_SECONDS=600
```

## Verify capabilities

Start the application and inspect the lightweight status endpoint:

```bash
curl -s http://127.0.0.1:8082/api/transcription/status
```

This performs dependency, path, FFmpeg, and CUDA checks without loading the
complete model. Upload a short audio file and select Local Whisper to verify the
first model load. If loading fails, the response contains a per-file error and
Local Whisper remains unavailable until the process is restarted.

Cloud audio is normalized to compressed MP3. Files still above the OpenAI
25 MB input limit are split into ordered chunks and reassembled. Temporary
normalized audio and chunks are removed after processing.

## Privacy notes

- Document conversion remains local.
- Local Whisper audio is never submitted to a transcription service.
- GPT-4o audio is sent to OpenAI only after the user explicitly selects that engine.
- Offline flags prevent Hugging Face model downloads at runtime.
