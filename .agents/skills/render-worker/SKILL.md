# Skill: render-worker

## Purpose
Own the external rendering worker and GPU/media execution layer.

## Scope
- ComfyUI availability and workflows.
- checkpoint/model discovery.
- image generation.
- image-to-video.
- LocalAI fallback.
- face refinement.
- lip-sync tools.
- upscale.
- FFmpeg execution.
- job lifecycle and worker capabilities.

## Required behavior
- expose `/api/health` and `/api/capabilities`;
- expose stable structured job states;
- assign a `job_id` to long-running work;
- make retries idempotent;
- return explicit error codes;
- never require restarting ComfyUI between scenes;
- detect optional tools instead of crashing the whole pipeline;
- persist enough state to recover after worker restart.

## P0 checklist
1. worker can boot unattended;
2. health endpoint verifies real dependencies;
3. checkpoints endpoint is reliable;
4. one known-good image workflow works;
5. one known-good video workflow works;
6. generated output can be located and copied deterministically;
7. status can be polled safely;
8. errors contain stage + code + human message;
9. cancellation/retry does not corrupt project state;
10. worker URL is not hardcoded into source control.

## Contract
Prefer responses shaped like:

```json
{
  "ok": true,
  "version": "1",
  "request_id": "...",
  "job_id": "...",
  "status": "queued|running|completed|failed",
  "result": {},
  "error": null
}
```

## Non-goals
Do not move heavy generation into Vercel serverless functions.