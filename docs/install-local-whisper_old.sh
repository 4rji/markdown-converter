#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/markdown-converter}"
APP_USER="${APP_USER:-markdown-converter}"
APP_GROUP="${APP_GROUP:-markdown-converter}"
VENV_PATH="${VENV_PATH:-$APP_DIR/.venv}"
MODEL_DIR="${WHISPER_MODEL_PATH:-/opt/models/faster-whisper-base}"
DOWNLOAD_MODEL="${DOWNLOAD_MODEL:-0}"

if [[ "${1:-}" == "--download-model" ]]; then
  DOWNLOAD_MODEL=1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this script as root or with sudo."
  exit 1
fi

if [[ ! -d "$APP_DIR" ]]; then
  echo "Application directory not found: $APP_DIR"
  exit 1
fi

if ! id "$APP_USER" >/dev/null 2>&1; then
  echo "Application user not found: $APP_USER"
  exit 1
fi

echo "Installing system packages..."
apt update
apt install -y python3 python3-venv python3-pip ffmpeg libgomp1

echo "Creating virtual environment at $VENV_PATH..."
install -d -o "$APP_USER" -g "$APP_GROUP" "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv "$VENV_PATH"

echo "Installing Python requirements..."
sudo -u "$APP_USER" "$VENV_PATH/bin/python" -m pip install --upgrade pip
sudo -u "$APP_USER" "$VENV_PATH/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "Verifying faster-whisper..."
sudo -u "$APP_USER" "$VENV_PATH/bin/python" -c "import faster_whisper; print(faster_whisper.__file__)"

echo "Preparing model directory at $MODEL_DIR..."
install -d -o "$APP_USER" -g "$APP_GROUP" "$MODEL_DIR"

if [[ "$DOWNLOAD_MODEL" == "1" ]]; then
  echo "Installing Hugging Face CLI and downloading the model..."
  sudo -u "$APP_USER" "$VENV_PATH/bin/pip" install --upgrade huggingface_hub
  sudo -u "$APP_USER" "$VENV_PATH/bin/hf" download Systran/faster-whisper-base --local-dir "$MODEL_DIR"
fi

if [[ -r "$MODEL_DIR/model.bin" ]]; then
  echo "Model present: $MODEL_DIR/model.bin"
else
  echo "Model not found at $MODEL_DIR/model.bin"
  echo "Run again with --download-model if this server should download it now."
fi

echo
echo "Done."
echo "Check the package with:"
echo "  sudo -u $APP_USER $VENV_PATH/bin/pip show faster-whisper"
