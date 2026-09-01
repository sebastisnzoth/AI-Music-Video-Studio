from __future__ import annotations

import json
import math
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"
PROJECTS.mkdir(exist_ok=True)


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Command failed")
    return proc.stdout.strip()


def duration(path: Path) -> float:
    out = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])
    return float(out)


def safe_suffix(name: str | None, fallback: str) -> str:
    if not name:
        return fallback
    suffix = Path(name).suffix.lower()
    return suffix if suffix and len(suffix) <= 10 else fallback


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_project(project_id: str) -> dict[str, Any]:
    path = PROJECTS / project_id / "project.json"
    if not path.exists():
        raise FileNotFoundError(project_id)
    return json.loads(path.read_text(encoding="utf-8"))


def _nearest_beat(value: float, beats: list[float], max_distance: float = 1.0) -> float:
    if not beats:
        return value
    nearest = min(beats, key=lambda x: abs(x - value))
    return float(nearest) if abs(nearest - value) <= max_distance else value


def _scene_prompt(style: str, lyric: str, scene_id: int, energy: str) -> str:
    subject = f"visual interpretation of lyric: {lyric}" if lyric else f"instrumental music-video shot {scene_id}"
    movement = {
        "high": "energetic camera movement, stronger performance, dramatic motion",
        "low": "intimate slow camera movement, restrained performance, atmospheric detail",
    }.get(energy, "cinematic camera movement, expressive performance")
    return (
        f"{style}, premium cinematic music video, {subject}, {movement}, "
        "consistent artist identity, realistic face, coherent wardrobe, professional lighting, "
        "natural motion, filmic depth of field, no text, no watermark"
    )


def make_storyboard(
    song_duration: float,
    lyrics: str,
    style: str,
    analysis: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    analysis = analysis or {}
    beats = [float(x) for x in analysis.get("beats", [])]
    sections = analysis.get("sections", []) or []
    raw_lines = [line.strip() for line in lyrics.splitlines() if line.strip() and not line.strip().startswith("[")]

    if raw_lines:
        ideal = song_duration / max(1, len(raw_lines))
        target = max(3.0, min(8.0, ideal))
        scenes: list[dict[str, Any]] = []
        t = 0.0
        for i, line in enumerate(raw_lines):
            raw_end = song_duration if i == len(raw_lines) - 1 else min(song_duration, t + target)
            end = song_duration if i == len(raw_lines) - 1 else _nearest_beat(raw_end, beats)
            if end <= t + 1.0:
                end = raw_end
            midpoint = (t + end) / 2
            energy = "medium"
            for section in sections:
                if float(section.get("start", 0)) <= midpoint < float(section.get("end", song_duration)):
                    energy = str(section.get("energy", "medium"))
                    break
            scenes.append({
                "id": i + 1,
                "start": round(t, 3),
                "end": round(end, 3),
                "duration": round(max(0.1, end - t), 3),
                "lyrics": line,
                "energy": energy,
                "prompt": _scene_prompt(style, line, i + 1, energy),
                "status": "planned",
                "approved": False,
                "generation_engine": "reference",
            })
            t = end
            if t >= song_duration:
                break
        if scenes:
            scenes[-1]["end"] = round(song_duration, 3)
            scenes[-1]["duration"] = round(song_duration - float(scenes[-1]["start"]), 3)
        return scenes

    # Prefer musically detected sections when there are no lyrics.
    if sections:
        scenes = []
        for i, section in enumerate(sections):
            start = float(section["start"])
            end = float(section["end"])
            energy = str(section.get("energy", "medium"))
            scenes.append({
                "id": i + 1,
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "lyrics": "",
                "energy": energy,
                "prompt": _scene_prompt(style, "", i + 1, energy),
                "status": "planned",
                "approved": False,
                "generation_engine": "reference",
            })
        return scenes

    scene_len = 6.0
    count = max(1, math.ceil(song_duration / scene_len))
    scenes = []
    for i in range(count):
        start = i * scene_len
        end = min(song_duration, (i + 1) * scene_len)
        scenes.append({
            "id": i + 1,
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
            "lyrics": "",
            "energy": "medium",
            "prompt": _scene_prompt(style, "", i + 1, "medium"),
            "status": "planned",
            "approved": False,
            "generation_engine": "reference",
        })
    return scenes


def update_scene(project_id: str, scene_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    meta = load_project(project_id)
    allowed = {"prompt", "approved", "status", "generation_engine"}
    scene = next((x for x in meta.get("storyboard", []) if int(x.get("id", -1)) == scene_id), None)
    if scene is None:
        raise KeyError(scene_id)
    for key, value in updates.items():
        if key in allowed:
            scene[key] = value
    save_json(PROJECTS / project_id / "project.json", meta)
    return scene


def render_reference(project_dir: Path, audio: Path, visual: Path, visual_kind: str, aspect: str, quality: str) -> Path:
    output = project_dir / "final.mp4"
    d = duration(audio)

    if aspect == "9:16":
        w, h = 1080, 1920
    else:
        w, h = 1920, 1080

    crf = {"preview": "25", "final": "19", "master": "16"}.get(quality, "19")
    preset = "veryfast" if quality == "preview" else "medium"

    if visual_kind == "image":
        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan=z='min(zoom+0.0005,1.10)':d=150:s={w}x{h}:fps=25,"
            "format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(visual), "-i", str(audio),
            "-t", f"{d:.3f}", "-vf", vf,
            "-c:v", "libx264", "-preset", preset, "-crf", crf,
            "-c:a", "aac", "-b:a", "256k", "-shortest", str(output),
        ]
    else:
        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(visual), "-i", str(audio),
            "-t", f"{d:.3f}", "-map", "0:v:0", "-map", "1:a:0", "-vf", vf,
            "-c:v", "libx264", "-preset", preset, "-crf", crf,
            "-c:a", "aac", "-b:a", "256k", "-shortest", str(output),
        ]
    run(cmd)
    return output


def create_project_files(title: str, style: str, aspect: str, quality: str, lyrics: str) -> tuple[str, Path, dict[str, Any]]:
    project_id = uuid.uuid4().hex[:12]
    project_dir = PROJECTS / project_id
    project_dir.mkdir(parents=True)
    metadata: dict[str, Any] = {
        "id": project_id,
        "title": title.strip() or "Mi videoclip",
        "style": style.strip() or "cinematic",
        "aspect": aspect,
        "quality": quality,
        "lyrics": lyrics,
        "status": "created",
        "progress": 5,
        "analysis": {},
        "storyboard": [],
    }
    save_json(project_dir / "project.json", metadata)
    return project_id, project_dir, metadata


def copy_upload(src, dst: Path) -> None:
    with dst.open("wb") as fh:
        shutil.copyfileobj(src, fh)
