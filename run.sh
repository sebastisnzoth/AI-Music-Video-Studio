#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

export PATH="$ROOT/.tools/bin:$PATH"
export COMFYUI_URL="${COMFYUI_URL:-http://127.0.0.1:8188}"

SIBLING_COMFYUI="$(cd "$ROOT/.." && pwd)/ComfyUI"
if [ -z "${COMFYUI_DIR:-}" ] && [ -d "$SIBLING_COMFYUI" ]; then
  export COMFYUI_DIR="$SIBLING_COMFYUI"
fi
if [ -z "${COMFYUI_OUTPUT_DIR:-}" ] && [ -n "${COMFYUI_DIR:-}" ]; then
  export COMFYUI_OUTPUT_DIR="$COMFYUI_DIR/output"
fi

export VIDEO_ENGINE="${VIDEO_ENGINE:-wan22-hf}"
export HF_VIDEO_ENABLED="${HF_VIDEO_ENABLED:-1}"
export WEB_ORIGINS="${WEB_ORIGINS:-https://ai-music-video-studio-three.vercel.app,https://ai-music-video-studio-sebastisnzoths-projects.vercel.app,http://127.0.0.1:8080,http://localhost:8080}"

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "ERROR: faltan FFmpeg/FFprobe en $ROOT/.tools/bin"
  exit 1
fi

echo "AI Music Video Studio worker"
echo "COMFYUI_URL=$COMFYUI_URL"
echo "COMFYUI_DIR=${COMFYUI_DIR:-auto/API}"
echo "COMFYUI_OUTPUT_DIR=${COMFYUI_OUTPUT_DIR:-auto/API}"
echo "VIDEO_ENGINE=$VIDEO_ENGINE"

exec python -m uvicorn app.main_v2:app --host 0.0.0.0 --port 8080
