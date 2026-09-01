from __future__ import annotations

from pathlib import Path
from typing import Any

from .pipeline import PROJECTS, load_project, run, save_json


def _fmt_srt_time(value: float) -> str:
    ms = max(0, int(round(value * 1000)))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def build_lyrics_srt(project_id: str) -> dict[str, Any]:
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    rows: list[str] = []
    index = 1
    for scene in meta.get("storyboard", []):
        text = str(scene.get("lyrics", "")).strip()
        if not text:
            continue
        start = float(scene.get("start", 0.0))
        end = float(scene.get("end", start + 2.0))
        rows.extend([
            str(index),
            f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}",
            text,
            "",
        ])
        index += 1

    if index == 1:
        raise RuntimeError("No lyric text is available for subtitles")

    path = project_dir / "lyrics.srt"
    path.write_text("\n".join(rows), encoding="utf-8")
    meta["lyrics_srt"] = path.name
    save_json(project_dir / "project.json", meta)
    return {"project_id": project_id, "path": str(path), "count": index - 1}


def burn_subtitles(project_id: str, source_name: str = "final-ai.mp4") -> dict[str, Any]:
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    source = project_dir / source_name
    if not source.exists():
        source = project_dir / "final.mp4"
    if not source.exists():
        raise FileNotFoundError("No video available for subtitle burn-in")

    srt = project_dir / "lyrics.srt"
    if not srt.exists():
        build_lyrics_srt(project_id)

    output = project_dir / "final-subtitled.mp4"
    escaped_srt = str(srt.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    style = "FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=50"
    run([
        "ffmpeg", "-y", "-i", str(source),
        "-vf", f"subtitles='{escaped_srt}':force_style='{style}'",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", str(output),
    ])
    meta["subtitled_output"] = output.name
    save_json(project_dir / "project.json", meta)
    return {"project_id": project_id, "output": str(output)}
