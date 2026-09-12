# Skill: studio-cto

## Purpose
Orchestrate AI Music Video Studio toward a working product.

## Trigger
Use for architecture, roadmap, prioritization, cross-cutting changes, or when the next task is unclear.

## Mission
Always answer:

> What prevents a real user from producing a finished music video today?

Then attack the highest-impact blocker.

## Checklist
- Read `CTO_MASTER.md` and `AGENTS.md`.
- Inspect current implementation before proposing replacements.
- Preserve free/local core.
- Keep Vercel as control plane and heavy rendering on worker.
- Prefer completing existing flows over adding integrations.
- Route worker issues to `render-worker`.
- Route media pipeline issues to `music-video-pipeline`.
- Route verification to `studio-qa`.
- Route production/deploy issues to `studio-deploy`.

## Decision rules
1. P0 reliability beats new features.
2. A resumable working scene beats a sophisticated non-resumable pipeline.
3. One known-good model/workflow beats many unverified models.
4. Structured state beats UI-only state.
5. Automated verification is part of implementation.

## Output expectation
For each cycle leave the repo closer to an end-to-end successful render, with code/tests/docs as appropriate.