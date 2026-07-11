#!/usr/bin/env bash

set -Eeuo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-/opt/markdown-converter}"
APP_USER="${APP_USER:-markdown-converter}"
APP_GROUP="${APP_GROUP:-markdown-converter}"
VENV_PATH="${VENV_PATH:-$APP_DIR/.venv}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"
MODEL_NAME="${MODEL_NAME:-large-v3-turbo}"
MODEL_DIR="${MODEL_DIR:-/opt/whisper-models/$MODEL_NAME}"
SERVICE_NAME="${SERVICE_NAME:-markdown-converter}"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"
INSTALL_LOCAL_WHISPER="${INSTALL_LOCAL_WHISPER:-1}"
INSTALL_TESSERACT="${INSTALL_TESSERACT:-1}"

log() {
  printf '\n\033[1;34m==>\033[0m %s\n' "$*"
}

fail() {
  printf '\n\033[1;31mERROR:\033[0m %s\n' "$*" >&2
  exit 1
}

[[ "$(id -u)" -eq 0 ]] || fail "Run this installer with sudo."
command -v systemctl >/dev/null 2>&1 \
  || fail "systemctl was not found; this installer requires systemd."
[[ -f "$SOURCE_DIR/app.py" && -f "$SOURCE_DIR/requirements.txt" ]] \
  || fail "Run the installer from inside the markdown-converter repository."

log "Installing operating-system dependencies"
apt-get update
apt_packages=(
  python3 python3-venv python3-pip ffmpeg libgomp1 ca-certificates rsync
)
if [[ "$INSTALL_TESSERACT" == "1" ]]; then
  apt_packages+=(tesseract-ocr)
fi
apt-get install -y "${apt_packages[@]}"

python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || fail "Python 3.10 or newer is required."
PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
apt-get install -y "python${PYTHON_VERSION}-venv"

log "Creating the dedicated service account"
if ! getent group "$APP_GROUP" >/dev/null; then
  groupadd --system "$APP_GROUP"
fi
if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --gid "$APP_GROUP" --home-dir "$APP_DIR" \
    --no-create-home --shell /usr/sbin/nologin "$APP_USER"
fi

if systemctl is-active --quiet "$SERVICE_NAME"; then
  log "Stopping the existing service during deployment"
  systemctl stop "$SERVICE_NAME"
fi

log "Deploying application files to $APP_DIR"
install -d -m 0755 -o "$APP_USER" -g "$APP_GROUP" "$APP_DIR"
if [[ "$SOURCE_DIR" != "$APP_DIR" ]]; then
  rsync -a \
    --exclude='.git/' \
    --exclude='.venv/' \
    --exclude='.env' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    "$SOURCE_DIR/" "$APP_DIR/"
fi
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

log "Installing Python dependencies into $VENV_PATH"
if [[ ! -x "$VENV_PATH/bin/python" || ! -f "$VENV_PATH/bin/activate" ]]; then
  rm -rf "$VENV_PATH"
  sudo -u "$APP_USER" python3 -m venv "$VENV_PATH"
fi
sudo -u "$APP_USER" -H "$VENV_PATH/bin/python" -m pip install --upgrade pip setuptools wheel
sudo -u "$APP_USER" -H "$VENV_PATH/bin/python" -m pip install --upgrade --no-cache-dir \
  -r "$APP_DIR/requirements.txt"

log "Validating document conversion dependencies"
MARKITDOWN_CLI="$VENV_PATH/bin/markitdown"
[[ -x "$MARKITDOWN_CLI" ]] \
  || fail "MarkItDown CLI was not installed at $MARKITDOWN_CLI"

sudo -u "$APP_USER" -H "$VENV_PATH/bin/python" -m pip check
sudo -u "$APP_USER" -H "$VENV_PATH/bin/python" - <<'PY'
from importlib import import_module
from importlib.metadata import version

converters = {
    "PDF": "pdfminer",
    "Word": "mammoth",
    "PowerPoint": "pptx",
    "Excel XLSX": "openpyxl",
    "Excel XLS": "xlrd",
    "Outlook": "olefile",
}
for label, module_name in converters.items():
    import_module(module_name)
    print(f"{label} dependency: OK ({module_name})")
print(f"MarkItDown version: {version('markitdown')}")
PY

smoke_dir="$(mktemp -d)"
smoke_input="$smoke_dir/markitdown-smoke.txt"
printf 'MarkItDown installation check\n' > "$smoke_input"
chown "$APP_USER:$APP_GROUP" "$smoke_dir" "$smoke_input"
smoke_output="$(sudo -u "$APP_USER" -H "$MARKITDOWN_CLI" "$smoke_input")"
rm -f "$smoke_input"
rmdir "$smoke_dir"
[[ "$smoke_output" == *"MarkItDown installation check"* ]] \
  || fail "MarkItDown CLI smoke conversion failed"
log "MarkItDown CLI validated at $MARKITDOWN_CLI"

CUDA_LIB_PATH=""
if [[ "$INSTALL_LOCAL_WHISPER" == "1" ]]; then
  command -v nvidia-smi >/dev/null 2>&1 \
    || fail "nvidia-smi was not found. Install the NVIDIA driver or use INSTALL_LOCAL_WHISPER=0."

  log "Installing and validating Local Whisper CUDA support"
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
  sudo -u "$APP_USER" -H "$VENV_PATH/bin/python" -m pip install --upgrade \
    faster-whisper nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"

  CUDA_LIB_PATH="$("$VENV_PATH/bin/python" - <<'PY'
import importlib
import os

def package_directory(module_name):
    module = importlib.import_module(module_name)
    paths = list(getattr(module, "__path__", []))
    if paths:
        return os.fspath(paths[0])
    module_file = getattr(module, "__file__", None)
    if module_file:
        return os.path.dirname(os.fspath(module_file))
    raise RuntimeError(f"Could not locate {module_name}")

print(":".join([
    package_directory("nvidia.cublas.lib"),
    package_directory("nvidia.cudnn.lib"),
]))
PY
)"
  [[ -n "$CUDA_LIB_PATH" ]] || fail "Could not locate the pip-installed CUDA libraries."

  install -d -m 0755 -o "$APP_USER" -g "$APP_GROUP" "$MODEL_DIR"
  if [[ ! -f "$MODEL_DIR/model.bin" ]]; then
    log "Downloading $MODEL_NAME to $MODEL_DIR"
    sudo -u "$APP_USER" -H env \
      MODEL_NAME="$MODEL_NAME" MODEL_DIR="$MODEL_DIR" HF_TOKEN="${HF_TOKEN:-}" \
      "$VENV_PATH/bin/python" - <<'PY'
import os
from faster_whisper.utils import download_model

download_model(os.environ["MODEL_NAME"], output_dir=os.environ["MODEL_DIR"])
PY
  else
    log "Reusing the existing Local Whisper model at $MODEL_DIR"
  fi

  for required_file in config.json model.bin tokenizer.json; do
    [[ -f "$MODEL_DIR/$required_file" ]] \
      || fail "Local Whisper model is incomplete: missing $MODEL_DIR/$required_file"
  done

  sudo -u "$APP_USER" -H env \
    LD_LIBRARY_PATH="$CUDA_LIB_PATH" MODEL_DIR="$MODEL_DIR" \
    "$VENV_PATH/bin/python" - <<'PY'
import os
import ctranslate2
from faster_whisper import WhisperModel

if ctranslate2.get_cuda_device_count() < 1:
    raise RuntimeError("No CUDA device was detected")
if "float16" not in ctranslate2.get_supported_compute_types("cuda"):
    raise RuntimeError("The CUDA device does not support float16")

WhisperModel(
    os.environ["MODEL_DIR"],
    device="cuda",
    compute_type="float16",
    local_files_only=True,
)
print("Local Whisper loaded successfully on CUDA.")
PY
fi

log "Installing and updating $ENV_FILE"
source_env="$SOURCE_DIR/.env"
if [[ "$source_env" != "$ENV_FILE" && -f "$source_env" ]]; then
  install -m 0600 -o "$APP_USER" -g "$APP_GROUP" "$source_env" "$ENV_FILE"
elif [[ ! -f "$ENV_FILE" ]]; then
  install -m 0600 -o "$APP_USER" -g "$APP_GROUP" /dev/null "$ENV_FILE"
fi

sudo -u "$APP_USER" -H env \
ENV_FILE="$ENV_FILE" MODEL_DIR="$MODEL_DIR" VENV_PATH="$VENV_PATH" \
CUDA_LIB_PATH="$CUDA_LIB_PATH" INSTALL_LOCAL_WHISPER="$INSTALL_LOCAL_WHISPER" \
"$VENV_PATH/bin/python" - <<'PY'
import os
from pathlib import Path

env_file = Path(os.environ["ENV_FILE"])
updates = {
    "OPENAI_API_KEY": "",
    "WHISPER_BEAM_SIZE": "5",
    "FFMPEG_TIMEOUT_SECONDS": "600",
    "MAX_UPLOAD_SIZE_MB": "500",
}
if os.environ["INSTALL_LOCAL_WHISPER"] == "1":
    updates.update({
        "WHISPER_MODEL_PATH": os.environ["MODEL_DIR"],
        "WHISPER_MODEL_NAME": "large-v3-turbo",
        "WHISPER_DEVICE": "cuda",
        "WHISPER_COMPUTE_TYPE": "float16",
        "WHISPER_VENV_PATH": os.environ["VENV_PATH"],
        "CUDA_VISIBLE_DEVICES": "0",
        "LD_LIBRARY_PATH": os.environ["CUDA_LIB_PATH"],
    })

lines = env_file.read_text(encoding="utf-8").splitlines()
existing = {}
for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        existing[key.strip()] = value

# Preserve every existing value, especially OPENAI_API_KEY, while correcting
# deployment-specific Local Whisper and CUDA paths.
for key, default in updates.items():
    if key not in existing or key != "OPENAI_API_KEY":
        existing[key] = default

ordered_keys = [
    "OPENAI_API_KEY", "WHISPER_MODEL_PATH", "WHISPER_MODEL_NAME",
    "WHISPER_DEVICE", "WHISPER_COMPUTE_TYPE", "WHISPER_VENV_PATH",
    "CUDA_VISIBLE_DEVICES", "LD_LIBRARY_PATH", "WHISPER_BEAM_SIZE", "FFMPEG_TIMEOUT_SECONDS",
    "MAX_UPLOAD_SIZE_MB",
]
output = [
    "# Managed by install-systemd-service_new.sh.",
    "# Add the real OpenAI key below; never commit this file.",
]
written = set()
for key in ordered_keys:
    if key in existing:
        output.append(f"{key}={existing[key]}")
        written.add(key)
for key, value in existing.items():
    if key not in written:
        output.append(f"{key}={value}")

env_file.write_text("\n".join(output) + "\n", encoding="utf-8")
PY
chown "$APP_USER:$APP_GROUP" "$ENV_FILE"
chmod 0600 "$ENV_FILE"

if [[ -f "$SERVICE_PATH" ]]; then
  backup_path="${SERVICE_PATH}.bak.$(date +%Y%m%d%H%M%S)"
  log "Backing up the existing unit to $backup_path"
  cp -a "$SERVICE_PATH" "$backup_path"
fi

log "Writing the systemd unit"
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Markdown Converter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV_PATH/bin/python $APP_DIR/app.py
Restart=on-failure
RestartSec=5
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF
chmod 0644 "$SERVICE_PATH"

log "Enabling and starting $SERVICE_NAME"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

sleep 2
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  systemctl status "$SERVICE_NAME" --no-pager || true
  journalctl -u "$SERVICE_NAME" -n 100 --no-pager || true
  fail "The service did not start successfully."
fi

log "Installation complete"
systemctl status "$SERVICE_NAME" --no-pager
cat <<EOF

Application:      $APP_DIR
Environment:      $ENV_FILE
Python:           $VENV_PATH/bin/python
MarkItDown:       $MARKITDOWN_CLI
Local model:      $MODEL_DIR
Service:          $SERVICE_NAME

OpenAI key:
  sudo nano $ENV_FILE
  # Set OPENAI_API_KEY=your_real_key, then run:
  sudo systemctl restart $SERVICE_NAME

Live logs:
  sudo journalctl -u $SERVICE_NAME -f

Status endpoint:
  curl -s http://127.0.0.1:8082/api/transcription/status
EOF
