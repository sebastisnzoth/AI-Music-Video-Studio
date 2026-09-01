# Evaluated repositories and roles

This file records how external/open-source projects fit into AI Music Video Studio.

## Core / high priority

### VocaVid
Primary architectural reference for storyboard-first, per-scene ComfyUI generation, resumable projects and music-video assembly.

### Maestro
Reference for music analysis, energy, beat-aware direction and shot planning.

### LocalAI
**High value.** Unified local AI engine for LLM, vision, voice, image and video. Supports multiple hardware classes and exposes API-compatible backends. LocalAI has supported LTX-family video generation, making it a strong optional image-to-video backend.

Integration:
- `/api/integrations` detects LocalAI.
- `/api/projects/{project}/scenes/{scene}/generate-video-localai` submits a scene to a configurable LocalAI video endpoint.
- `LOCALAI_BASE_URL` defaults to `http://127.0.0.1:8080`.
- `LOCALAI_VIDEO_ENDPOINT` is intentionally configurable because video routes/backends evolve.

### Pixelle-Video
**High architectural value.** Modular pipeline with ComfyUI workflows, image-to-video, digital-human generation, motion transfer, batch jobs, history and replaceable providers. We reuse the modular design, not paid API dependencies.

## Quality / identity

### Deep-Live-Cam
Optional local face-refinement backend after scene video generation and before lip-sync. Useful for single-image identity transfer, mouth mask and face enhancement.

### Duix Avatar
Powerful offline digital-human/lip-sync system with local synthesis APIs. Useful as an optional high-end avatar backend, but current practical deployment expects NVIDIA GPU hardware, large RAM/disk and Docker services. Not part of the lightweight default path.

## Rendering / review / delivery

### HyperFrames
**Useful compositor.** Deterministic HTML/CSS/media-to-MP4 renderer with beat-synced `music-to-video`, captions, overlays, animations and local FFmpeg rendering. Good optional alternative to FFmpeg-only assembly for titles, kinetic lyrics and motion graphics. Requires Node.js 22+.

### Shumai
Reference for media review: scene versions, timestamped comments, approvals and proxy workflows. We implemented lightweight equivalents without its PostgreSQL/S3/Temporal stack.

### MoneyPrinterTurbo
Reference for batch production, subtitles, 16:9/9:16 outputs, API/UI separation and automated composition. Paid/cloud providers are excluded from the default path.

### SRS (Simple Realtime Server)
**Not a generation or super-resolution model.** Useful only if the studio later needs RTMP/WebRTC/HLS live preview, remote review or streaming. It is not required for final video generation.

## Prompt / direction references

### higgsfield-seedance2-jineng
Prompt/director reference for beat synchronization, camera language, lighting and music-video structure. No Higgsfield dependency is required in the main path.

### open-higgsfield
Reference for a model catalog, per-model capabilities, lifecycle states, history and reuse. Its generation platform keys are not part of the free local core.

## Excluded from mandatory core

- MiniMax CLI: requires token plan/API.
- Higgsfield/Seedance hosted generation.
- Kling, Veo, Sora, Runway, MuAPI and other paid generation APIs.

## Current intended free/local pipeline

```text
song + reference
→ librosa / local transcription
→ director
→ identity conditioning (IPAdapter/InstantID)
→ image (ComfyUI)
→ video (ComfyUI or LocalAI)
→ optional Deep-Live-Cam identity refinement
→ lip-sync (Wav2Lip/MuseTalk or optional Duix)
→ upscale (Real-ESRGAN)
→ review/version approval
→ FFmpeg or HyperFrames composition
→ original song master audio
→ final MP4
```
