#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/markdown-converter}"
APP_USER="${APP_USER:-markdown-converter}"
APP_GROUP="${APP_GROUP:-markdown-converter}"
VENV_PATH="${VENV_PATH:-$APP_DIR/.venv}"
SERVICE_NAME="${SERVICE_NAME:-markdown-converter}"
SERVICE_PATH="${SERVICE_PATH:-/etc/systemd/system/$SERVICE_NAME.service}"
REPO_URL="${REPO_URL:-}"
MAX_UPLOAD_SIZE_MB="${MAX_UPLOAD_SIZE_MB:-500}"
WHISPER_MODEL_PATH="${WHISPER_MODEL_PATH:-/opt/models/faster-whisper-base}"
WHISPER_BEAM_SIZE="${WHISPER_BEAM_SIZE:-5}"
FFMPEG_TIMEOUT_SECONDS="${FFMPEG_TIMEOUT_SECONDS:-600}"
OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"
INSTALL_TESSERACT="${INSTALL_TESSERACT:-1}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this script as root or with sudo."
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found. This script is for systemd-based Linux servers."
  exit 1
fi

echo "Installing system packages..."
apt update
apt install -y python3 python3-venv python3-pip ffmpeg libgomp1 git

if [[ "$INSTALL_TESSERACT" == "1" ]]; then
  apt install -y tesseract-ocr
fi

if ! id "$APP_USER" >/dev/null 2>&1; then
  echo "Creating service user: $APP_USER"
  useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
fi

if [[ ! -d "$APP_DIR" ]]; then
  if [[ -z "$REPO_URL" ]]; then
    echo "Application directory not found: $APP_DIR"
    echo "Set REPO_URL to clone the repository automatically."
    exit 1
  fi

  echo "Cloning repository into $APP_DIR..."
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "Setting ownership on $APP_DIR..."
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

echo "Creating virtual environment..."
sudo -u "$APP_USER" python3 -m venv "$VENV_PATH"
sudo -u "$APP_USER" "$VENV_PATH/bin/python" -m pip install --upgrade pip
sudo -u "$APP_USER" "$VENV_PATH/bin/pip" install -r "$APP_DIR/requirements.txt"

if [[ -f "$SERVICE_PATH" ]]; then
  backup_path="${SERVICE_PATH}.bak.$(date +%Y%m%d%H%M%S)"
  echo "Backing up existing service file to $backup_path..."
  cp "$SERVICE_PATH" "$backup_path"
fi

echo "Writing $SERVICE_PATH..."
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Markdown Converter Flask App
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
Environment=MAX_UPLOAD_SIZE_MB=$MAX_UPLOAD_SIZE_MB
Environment=WHISPER_MODEL_PATH=$WHISPER_MODEL_PATH
Environment=WHISPER_BEAM_SIZE=$WHISPER_BEAM_SIZE
Environment=FFMPEG_TIMEOUT_SECONDS=$FFMPEG_TIMEOUT_SECONDS
Environment=OMP_NUM_THREADS=$OMP_NUM_THREADS
ExecStart=$VENV_PATH/bin/python $APP_DIR/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd and enabling service..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo
echo "Service status:"
systemctl status "$SERVICE_NAME" --no-pager || true

echo
echo "Recent logs:"
journalctl -u "$SERVICE_NAME" -n 50 --no-pager || true

echo
echo "Done."
echo "If audio transcription is required, ensure the model exists at:"
echo "  $WHISPER_MODEL_PATH"
echo "You can install it with:"
echo "  sudo bash docs/install-local-whisper.sh --download-model"
