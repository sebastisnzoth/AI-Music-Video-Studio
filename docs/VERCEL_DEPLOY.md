# Vercel deployment

## Production control plane

- URL: https://ai-music-video-studio-three.vercel.app
- Vercel project: `ai-music-video-studio`
- Project ID: `prj_7IYSARPDm3ntnkCy1DanIv8tRg07`

The Vercel deployment is intentionally a lightweight control plane. Heavy generation stays on the render worker.

## Architecture

```text
Vercel UI / FastAPI control
        |
        | direct browser upload + API calls
        v
Render worker (FastAPI)
        |
        +-- Librosa / Whisper
        +-- ComfyUI
        +-- Deep-Live-Cam
        +-- Wav2Lip
        +-- Real-ESRGAN
        +-- FFmpeg
```

## Start the worker

```bash
cd AI-Music-Video-Studio
git pull
export WEB_ORIGINS="https://ai-music-video-studio-three.vercel.app"
bash run.sh
```

The worker listens on `http://127.0.0.1:8080` by default.

## Expose the worker over HTTPS

A simple development option is Cloudflare Tunnel:

```bash
brew install cloudflared
cloudflared tunnel --url http://127.0.0.1:8080
```

Cloudflare prints a temporary public HTTPS URL such as:

```text
https://example.trycloudflare.com
```

Use that URL as `RENDER_WORKER_URL` in the Vercel project environment variables.

For a permanent installation, use a named Cloudflare Tunnel, a VPS, or another persistent HTTPS reverse proxy.

## Vercel environment variable

Configure:

```text
RENDER_WORKER_URL=https://your-worker.example.com
```

Then redeploy the Vercel project. The production page will change from `Worker: offline` to `Worker: online` when `/api/health` is reachable.

## Important

Do not run ComfyUI, model inference, long FFmpeg renders, Wav2Lip, Deep-Live-Cam, or Real-ESRGAN inside the Vercel function. Vercel only hosts the interface and control API.

Song/video uploads are sent directly from the browser to the render worker, so large media files do not pass through the Vercel function request body.
