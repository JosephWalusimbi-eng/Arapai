#!/usr/bin/env bash
# ADTC 2026 — download model weights (required by submission template).
#
# Rules:
# - Idempotent (safe to run multiple times).
# - Public URL only (no credentials).
# - Output path must match `_runtime.model_path` in metadata.json.
#
# Also copies the file to models/lite/model.gguf for the Arapai Streamlit app.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$HERE/model"
MODEL_FILE="$MODEL_DIR/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
APP_FILE="$HERE/models/lite/model.gguf"

MODEL_URL="https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

mkdir -p "$MODEL_DIR"
mkdir -p "$(dirname "$APP_FILE")"

if [[ -f "$MODEL_FILE" ]]; then
  echo "ADTC model already present at $MODEL_FILE"
else
  echo "Downloading $MODEL_URL"
  echo "  -> $MODEL_FILE (~637 MB)"

  if command -v curl > /dev/null 2>&1; then
    curl -L --fail --progress-bar -o "$MODEL_FILE.partial" "$MODEL_URL"
  elif command -v wget > /dev/null 2>&1; then
    wget --show-progress -O "$MODEL_FILE.partial" "$MODEL_URL"
  else
    echo "error: neither curl nor wget found" >&2
    exit 1
  fi

  mv "$MODEL_FILE.partial" "$MODEL_FILE"
  echo "done: $MODEL_FILE"
fi

if [[ ! -f "$APP_FILE" ]] || ! cmp -s "$MODEL_FILE" "$APP_FILE"; then
  cp "$MODEL_FILE" "$APP_FILE"
  echo "copied to app path: $APP_FILE"
fi

echo "Ready for ADTC profiler and: streamlit run app.py"
