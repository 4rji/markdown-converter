#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODEL_NAME="${MODEL_NAME:-large-v3-turbo}"
VENV_DIR="${VENV_DIR:-$SCRIPT_DIR/.venv}"
MODEL_DIR="${MODEL_DIR:-/opt/whisper-models/$MODEL_NAME}"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
SKIP_APT="${SKIP_APT:-0}"

log() {
    printf '\n\033[1;34m==>\033[0m %s\n' "$*"
}

fail() {
    printf '\n\033[1;31mERROR:\033[0m %s\n' "$*" >&2
    exit 1
}

command -v sudo >/dev/null 2>&1 || fail "sudo is required."
command -v nvidia-smi >/dev/null 2>&1 || fail "nvidia-smi was not found. Install the NVIDIA driver first."

log "Checking NVIDIA GPU"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader \
    || fail "The NVIDIA GPU is not available."

if [[ "$SKIP_APT" != "1" ]]; then
    PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || printf '3.10')"
    VENV_PACKAGE="python${PYTHON_VERSION}-venv"
    log "Installing system dependencies"
    sudo apt-get update
    sudo apt-get install -y \
        python3 \
        python3-venv \
        "$VENV_PACKAGE" \
        python3-pip \
        ffmpeg \
        ca-certificates \
        libgomp1
fi

log "Preparing directories"
mkdir -p "$(dirname "$VENV_DIR")"
sudo install -d -m 0755 -o "$USER" -g "$(id -gn)" "$MODEL_DIR"

log "Creating or reusing Python environment: $VENV_DIR"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel

log "Installing application dependencies in the shared environment"
"$VENV_DIR/bin/python" -m pip install --no-cache-dir -r "$REQUIREMENTS_FILE"

log "Installing Faster-Whisper and CUDA runtime libraries"
"$VENV_DIR/bin/python" -m pip install --upgrade \
    faster-whisper \
    nvidia-cublas-cu12 \
    "nvidia-cudnn-cu12==9.*"

log "Locating CUDA libraries"
CUDA_LIB_PATH="$("$VENV_DIR/bin/python" - <<'PY'
import importlib
import os


def package_directory(module_name):
    module = importlib.import_module(module_name)
    package_paths = list(getattr(module, "__path__", []))
    if package_paths:
        return os.fspath(package_paths[0])

    module_file = getattr(module, "__file__", None)
    if module_file:
        return os.path.dirname(os.fspath(module_file))

    raise RuntimeError(f"Could not locate CUDA package directory: {module_name}")


print(
    package_directory("nvidia.cublas.lib")
    + ":"
    + package_directory("nvidia.cudnn.lib")
)
PY
)"

[[ -n "$CUDA_LIB_PATH" ]] || fail "Could not locate the installed CUDA libraries."

log "Downloading $MODEL_NAME to $MODEL_DIR"
MODEL_NAME="$MODEL_NAME" MODEL_DIR="$MODEL_DIR" \
"$VENV_DIR/bin/python" - <<'PY'
import os
from faster_whisper.utils import download_model

model_name = os.environ["MODEL_NAME"]
model_dir = os.environ["MODEL_DIR"]

path = download_model(model_name, output_dir=model_dir)
print(f"Model downloaded to: {path}")
PY

for required_file in config.json model.bin tokenizer.json; do
    [[ -f "$MODEL_DIR/$required_file" ]] \
        || fail "Model download is incomplete: missing $required_file"
done

log "Validating CUDA and loading the model"
LD_LIBRARY_PATH="$CUDA_LIB_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
MODEL_DIR="$MODEL_DIR" \
"$VENV_DIR/bin/python" - <<'PY'
import os
import ctranslate2
from faster_whisper import WhisperModel

model_dir = os.environ["MODEL_DIR"]
compute_types = ctranslate2.get_supported_compute_types("cuda")

if "float16" not in compute_types:
    raise RuntimeError(
        f"CUDA is available, but float16 is not supported. Supported types: {sorted(compute_types)}"
    )

WhisperModel(
    model_dir,
    device="cuda",
    compute_type="float16",
)

print("Whisper large-v3-turbo loaded successfully on CUDA.")
PY

log "Updating environment file: $ENV_FILE"
ENV_FILE="$ENV_FILE" \
MODEL_DIR="$MODEL_DIR" \
VENV_DIR="$VENV_DIR" \
CUDA_LIB_PATH="$CUDA_LIB_PATH" \
"$VENV_DIR/bin/python" - <<'PY'
import os
from pathlib import Path

env_file = Path(os.environ["ENV_FILE"])
env_file.parent.mkdir(parents=True, exist_ok=True)

updates = {
    "WHISPER_MODEL_PATH": os.environ["MODEL_DIR"],
    "WHISPER_MODEL_NAME": "large-v3-turbo",
    "WHISPER_DEVICE": "cuda",
    "WHISPER_COMPUTE_TYPE": "float16",
    "WHISPER_VENV_PATH": os.environ["VENV_DIR"],
    "CUDA_VISIBLE_DEVICES": "0",
    "LD_LIBRARY_PATH": os.environ["CUDA_LIB_PATH"],
}

existing_lines = (
    env_file.read_text(encoding="utf-8").splitlines()
    if env_file.exists()
    else []
)

written = set()
result = []

for line in existing_lines:
    stripped = line.strip()

    if not stripped or stripped.startswith("#") or "=" not in line:
        result.append(line)
        continue

    key = line.split("=", 1)[0].strip()

    if key in updates:
        result.append(f"{key}={updates[key]}")
        written.add(key)
    else:
        result.append(line)

if result and result[-1] != "":
    result.append("")

for key, value in updates.items():
    if key not in written:
        result.append(f"{key}={value}")

env_file.write_text("\n".join(result).rstrip() + "\n", encoding="utf-8")
PY

cat <<EOF

Installation completed.

Model:
  $MODEL_DIR

Python environment:
  $VENV_DIR

Environment file:
  $ENV_FILE

The application loads $ENV_FILE automatically at startup.
Start it with:
  "$VENV_DIR/bin/python" "$SCRIPT_DIR/app.py"

To load the variables in the current shell (only needed for manual
faster-whisper commands outside the app):
  set -a
  source "$ENV_FILE"
  set +a

EOF
