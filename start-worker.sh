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
mkdir -p "$LOG_DIR" "$TOOLS_BIN"
rm -rf "$TOOLS_TMP"
mkdir -p "$TOOLS_TMP"
export PATH="$TOOLS_BIN:$PATH"

free_mb() {
  df -Pk "$ROOT" | awk 'NR==2 {print int($4/1024)}'
}

require_free_mb() {
  local needed="$1"
  local available
  available="$(free_mb)"
  if [ "$available" -lt "$needed" ]; then
    echo "ERROR: espacio insuficiente en disco."
    echo "  Libre: ${available} MB"
    echo "  Recomendado para continuar: al menos ${needed} MB"
    echo
    echo "Podés liberar cachés seguras con:"
    echo "  rm -rf ~/Library/Caches/Homebrew/*"
    echo "  rm -rf ~/Library/Caches/pip/* 2>/dev/null || true"
    echo "Luego comprobá con: df -h /"
    exit 1
  fi
}

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 no está instalado."
  exit 1
fi

install_one_evermeet_binary() {
  local name="$1"
  local url="$2"
  local archive="$TOOLS_TMP/${name}.zip"
  local unpack="$TOOLS_TMP/${name}-unpack"

  rm -rf "$archive" "$unpack"
  mkdir -p "$unpack"
  curl -fLJ "$url" -o "$archive"
  unzip -qo "$archive" -d "$unpack"
  local src
  src="$(find "$unpack" -type f -name "$name" -perm -111 | head -n 1 || true)"
  if [ -z "$src" ]; then
    echo "ERROR: no pude extraer $name."
    exit 1
  fi
  rm -f "$TOOLS_BIN/$name"
  cp "$src" "$TOOLS_BIN/$name"
  chmod +x "$TOOLS_BIN/$name"
  xattr -dr com.apple.quarantine "$TOOLS_BIN/$name" 2>/dev/null || true
  rm -rf "$archive" "$unpack"
}

install_ffmpeg_macos_intel() {
  echo "FFmpeg/ffprobe no encontrados. Instalando binarios locales para macOS Intel..."
  require_free_mb 350
  if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "→ Descargando FFmpeg..."
    install_one_evermeet_binary "ffmpeg" "https://evermeet.cx/ffmpeg/getrelease/zip"
  fi
  if ! command -v ffprobe >/dev/null 2>&1; then
    echo "→ Descargando FFprobe..."
    install_one_evermeet_binary "ffprobe" "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"
  fi
}

install_cloudflared_from_url() {
  local url="$1"
  rm -rf "$TOOLS_TMP/cloudflared-unpack" "$TOOLS_TMP/cloudflared.tgz"
  mkdir -p "$TOOLS_TMP/cloudflared-unpack"
  curl -fL "$url" -o "$TOOLS_TMP/cloudflared.tgz"
  tar -xzf "$TOOLS_TMP/cloudflared.tgz" -C "$TOOLS_TMP/cloudflared-unpack"
  local src
  src="$(find "$TOOLS_TMP/cloudflared-unpack" -type f -name cloudflared | head -n 1 || true)"
  if [ -z "$src" ]; then
    echo "ERROR: no pude extraer cloudflared."
    exit 1
  fi
  rm -f "$TOOLS_BIN/cloudflared"
  cp "$src" "$TOOLS_BIN/cloudflared"
  chmod +x "$TOOLS_BIN/cloudflared"
  xattr -dr com.apple.quarantine "$TOOLS_BIN/cloudflared" 2>/dev/null || true
  rm -rf "$TOOLS_TMP/cloudflared-unpack" "$TOOLS_TMP/cloudflared.tgz"
}

install_cloudflared_macos_intel() {
  echo "cloudflared no encontrado o incompatible. Instalando binario local para macOS Intel..."
  require_free_mb 250
  local os_version
  os_version="$(sw_vers -productVersion 2>/dev/null || true)"
  if [[ "$os_version" == 10.15* ]]; then
    echo "→ Catalina detectado: usando cloudflared 2024.12.2 compatible con Intel antiguo."
    install_cloudflared_from_url "https://github.com/cloudflare/cloudflared/releases/download/2024.12.2/cloudflared-darwin-amd64.tgz"
  else
    install_cloudflared_from_url "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz"
  fi
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

if ! command -v cloudflared >/dev/null 2>&1 || ! cloudflared --version >/dev/null 2>&1; then
  if [ "$OS_NAME" = "Darwin" ] && [ "$ARCH_NAME" = "x86_64" ]; then
    install_cloudflared_macos_intel
  else
    echo "ERROR: cloudflared no está instalado o no puede ejecutarse."
    exit 1
  fi
fi

if ! cloudflared --version >/dev/null 2>&1; then
  echo "ERROR: cloudflared se descargó pero macOS no puede ejecutarlo."
  exit 1
fi

echo "✓ FFmpeg: $(ffmpeg -version 2>/dev/null | head -n 1)"
echo "✓ FFprobe: $(ffprobe -version 2>/dev/null | head -n 1)"
echo "✓ Cloudflared: $(cloudflared --version 2>/dev/null | head -n 1)"
echo "✓ Python: $(python3 --version 2>&1)"
echo "✓ Espacio libre: $(free_mb) MB"

require_free_mb 1200

if [ ! -d ".venv" ]; then
  echo "Creando entorno Python..."
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade --no-cache-dir pip >/dev/null
pip install --no-cache-dir -r requirements.txt >/dev/null

export COMFYUI_URL
export WEB_ORIGINS="${WEB_ORIGINS:-$VERCEL_ORIGIN,http://127.0.0.1:$PORT,http://localhost:$PORT}"

if curl -fsS "$COMFYUI_URL/system_stats" >/dev/null 2>&1; then
  echo "✓ ComfyUI online: $COMFYUI_URL"
else
  echo "⚠ ComfyUI no responde en $COMFYUI_URL"
  echo "  El worker arrancará igual, pero no mostrará modelos ni generará IA hasta iniciar ComfyUI."
fi

cleanup() {
  rm -rf "$TOOLS_TMP" >/dev/null 2>&1 || true
  if [ -n "${WORKER_PID:-}" ] && kill -0 "$WORKER_PID" >/dev/null 2>&1; then
    kill "$WORKER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
  echo "✓ Worker ya estaba activo en http://127.0.0.1:$PORT"
else
  echo "Iniciando AI Music Video Studio worker..."
  python -m uvicorn app.main_v2:app --host 0.0.0.0 --port "$PORT" >"$LOG_DIR/worker.log" 2>&1 &
  WORKER_PID=$!
  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    echo "ERROR: el worker no arrancó. Log: $LOG_DIR/worker.log"
    tail -n 60 "$LOG_DIR/worker.log" || true
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
