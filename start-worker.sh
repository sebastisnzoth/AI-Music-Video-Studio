#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PORT="${PORT:-8080}"
COMFYUI_URL="${COMFYUI_URL:-http://127.0.0.1:8188}"
VERCEL_ORIGIN="${VERCEL_ORIGIN:-https://ai-music-video-studio-three.vercel.app}"
LOG_DIR="$ROOT/.logs"
TOOLS_BIN="$ROOT/.tools/bin"
TOOLS_TMP="$ROOT/.tools/tmp"
mkdir -p "$LOG_DIR" "$TOOLS_BIN" "$TOOLS_TMP"
export PATH="$TOOLS_BIN:$PATH"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 no está instalado."
  exit 1
fi

install_ffmpeg_macos_intel() {
  echo "FFmpeg/ffprobe no encontrados. Instalando binarios locales para macOS Intel..."
  rm -f "$TOOLS_TMP"/ffmpeg*.zip "$TOOLS_TMP"/ffprobe*.zip
  curl -fLJ "https://evermeet.cx/ffmpeg/getrelease/zip" -o "$TOOLS_TMP/ffmpeg.zip"
  curl -fLJ "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip" -o "$TOOLS_TMP/ffprobe.zip"
  unzip -qo "$TOOLS_TMP/ffmpeg.zip" -d "$TOOLS_TMP/ffmpeg-unpack"
  unzip -qo "$TOOLS_TMP/ffprobe.zip" -d "$TOOLS_TMP/ffprobe-unpack"
  FFMPEG_SRC="$(find "$TOOLS_TMP/ffmpeg-unpack" -type f -name ffmpeg -perm -111 | head -n 1 || true)"
  FFPROBE_SRC="$(find "$TOOLS_TMP/ffprobe-unpack" -type f -name ffprobe -perm -111 | head -n 1 || true)"
  if [ -z "$FFMPEG_SRC" ] || [ -z "$FFPROBE_SRC" ]; then
    echo "ERROR: no pude extraer ffmpeg/ffprobe."
    exit 1
  fi
  cp "$FFMPEG_SRC" "$TOOLS_BIN/ffmpeg"
  cp "$FFPROBE_SRC" "$TOOLS_BIN/ffprobe"
  chmod +x "$TOOLS_BIN/ffmpeg" "$TOOLS_BIN/ffprobe"
  xattr -dr com.apple.quarantine "$TOOLS_BIN/ffmpeg" "$TOOLS_BIN/ffprobe" 2>/dev/null || true
}

install_cloudflared_macos_intel() {
  echo "cloudflared no encontrado. Instalando binario local para macOS Intel..."
  rm -rf "$TOOLS_TMP/cloudflared-unpack" "$TOOLS_TMP/cloudflared.tgz"
  mkdir -p "$TOOLS_TMP/cloudflared-unpack"
  curl -fL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz" -o "$TOOLS_TMP/cloudflared.tgz"
  tar -xzf "$TOOLS_TMP/cloudflared.tgz" -C "$TOOLS_TMP/cloudflared-unpack"
  CLOUDFLARED_SRC="$(find "$TOOLS_TMP/cloudflared-unpack" -type f -name cloudflared | head -n 1 || true)"
  if [ -z "$CLOUDFLARED_SRC" ]; then
    echo "ERROR: no pude extraer cloudflared."
    exit 1
  fi
  cp "$CLOUDFLARED_SRC" "$TOOLS_BIN/cloudflared"
  chmod +x "$TOOLS_BIN/cloudflared"
  xattr -dr com.apple.quarantine "$TOOLS_BIN/cloudflared" 2>/dev/null || true
}

OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  if [ "$OS_NAME" = "Darwin" ] && [ "$ARCH_NAME" = "x86_64" ]; then
    install_ffmpeg_macos_intel
  else
    echo "ERROR: FFmpeg no está instalado. Instalalo y volvé a ejecutar este script."
    exit 1
  fi
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  if [ "$OS_NAME" = "Darwin" ] && [ "$ARCH_NAME" = "x86_64" ]; then
    install_cloudflared_macos_intel
  else
    echo "ERROR: cloudflared no está instalado. Instalalo y volvé a ejecutar este script."
    exit 1
  fi
fi

echo "✓ FFmpeg: $(ffmpeg -version 2>/dev/null | head -n 1)"
echo "✓ FFprobe: $(ffprobe -version 2>/dev/null | head -n 1)"
echo "✓ Cloudflared: $(cloudflared --version 2>/dev/null | head -n 1)"
echo "✓ Python: $(python3 --version 2>&1)"

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
