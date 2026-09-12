# Skill: music-video-pipeline

## Purpose
Own the creative/media pipeline from song input to final approved MP4.

## Scope
- audio analysis;
- transcription/timestamps;
- storyboard;
- visual direction;
- scene packages;
- identity consistency;
- image generation inputs;
- image-to-video inputs;
- lip-sync decision;
- scene review/versioning;
- captions;
- assembly and master audio.

## Pipeline invariant

```text
input
→ analysis
→ storyboard
→ approved storyboard
→ scene generation
→ review
→ approved scenes
→ assembly
→ final MP4
```

Never skip a required state implicitly.

## Scene contract
Each scene should have, at minimum:
- stable scene id;
- start/end/duration;
- energy/section context;
- visual prompt;
- negative prompt when supported;
- seed;
- model/workflow metadata;
- reference assets;
- `needs_lipsync`;
- generation status;
- versions;
- approved version id;
- error info.

## Rules
- preserve original song as master audio unless user requests otherwise;
- do not regenerate approved scenes unnecessarily;
- make scene regeneration isolated;
- do not auto-approve generated material;
- keep storyboard and render parameters reproducible;
- prefer preview-quality iteration before expensive final render;
- final assembly must fail clearly if required scenes are missing/unapproved.

## Quality checks
Before final assembly verify:
1. all scene durations cover the intended timeline;
2. no missing media;
3. approved version exists per required scene;
4. output aspect ratio is consistent;
5. audio duration and final timeline are compatible;
6. captions are valid if enabled;
7. FFmpeg result is playable and non-empty.