#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8080}"
TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "ERROR: cloudflared no está instalado o no está en PATH."
  exit 1
fi

if [ -z "$TOKEN" ]; then
  echo "ERROR: falta CLOUDFLARE_TUNNEL_TOKEN."
  echo "Usá start-worker.sh para desarrollo con Quick Tunnel o configurá un Named Tunnel para producción."
  exit 1
fi

if ! curl -fsS "http://127.0.0.1:${PORT}/api/v1/health" >/dev/null 2>&1; then
  echo "ERROR: el worker no responde en http://127.0.0.1:${PORT}/api/v1/health"
  echo "Iniciá primero el worker local."
  exit 1
fi

echo "✓ Worker local online en puerto ${PORT}"
echo "✓ Iniciando Cloudflare Named Tunnel estable"

exec cloudflared tunnel --no-autoupdate run --token "$TOKEN"
