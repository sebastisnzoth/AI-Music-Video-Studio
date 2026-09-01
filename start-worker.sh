#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PORT="${PORT:-8080}"
COMFYUI_URL="${COMFYUI_URL:-http://127.0.0.1:8188}"
VERCEL_ORIGIN="${VERCEL_ORIGIN:-https://ai-music-video-studio-three.vercel.app}"
LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 no está instalado."
  exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ERROR: FFmpeg no está instalado. En macOS: brew install ffmpeg"
  exit 1
fi
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "ERROR: cloudflared no está instalado."
  echo "Instalalo con: brew install cloudflared"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creando entorno Python..."
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null

export COMFYUI_URL
export WEB_ORIGINS="${WEB_ORIGINS:-$VERCEL_ORIGIN,http://127.0.0.1:$PORT,http://localhost:$PORT}"

if curl -fsS "$COMFYUI_URL/system_stats" >/dev/null 2>&1; then
  echo "✓ ComfyUI online: $COMFYUI_URL"
else
  echo "⚠ ComfyUI no responde en $COMFYUI_URL"
  echo "  El worker arrancará igual, pero no mostrará modelos ni generará IA hasta iniciar ComfyUI."
fi

cleanup() {
  if [ -n "${WORKER_PID:-}" ] && kill -0 "$WORKER_PID" >/dev/null 2>&1; then
    kill "$WORKER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
  echo "✓ Worker ya estaba activo en http://127.0.0.1:$PORT"
else
  echo "Iniciando AI Music Video Studio worker..."
  PORT="$PORT" python -m app.main_v2 >"$LOG_DIR/worker.log" 2>&1 &
  WORKER_PID=$!
  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    echo "ERROR: el worker no arrancó. Log: $LOG_DIR/worker.log"
    tail -n 40 "$LOG_DIR/worker.log" || true
    exit 1
  fi
  echo "✓ Worker online: http://127.0.0.1:$PORT"
fi

echo
echo "Abriendo túnel HTTPS público..."
echo "Cuando aparezca una URL https://xxxxx.trycloudflare.com, copiala y pegala en 'Conectar render worker' en Vercel."
echo "Vercel: https://ai-music-video-studio-three.vercel.app"
echo

cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$PORT" 2>&1 | tee "$LOG_DIR/cloudflared.log"
