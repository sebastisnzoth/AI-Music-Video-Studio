#!/usr/bin/env bash
set -e

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ERROR: FFmpeg no está instalado. En macOS: brew install ffmpeg"
  exit 1
fi

python -m app.main_v2
