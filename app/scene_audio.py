from __future__ import annotations

from pathlib import Path

from .pipeline import run


def extract_scene_audio(song_path: Path, project_dir: Path, scene: dict, sample_rate: int = 48000) -> Path:
    """Extract the exact source-song segment for a storyboard scene.

    The final edit always keeps the untouched original song; these WAV snippets
    are conditioning inputs for local lip-sync/audio-to-video models only.
    """
    scene_id = int(scene["id"])
    start = float(scene["start"])
    length = max(0.05, float(scene["end"]) - start)
    out_dir = project_dir / "segments"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"scene-{scene_id:03d}.wav"
    run([
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{start:.6f}",
        "-i", str(song_path),
        "-t", f"{length:.6f}",
        "-vn", "-ac", "2", "-ar", str(sample_rate),
        "-c:a", "pcm_s16le",
        str(output),
    ])
    return output


def extract_all_scene_audio(song_path: Path, project_dir: Path, storyboard: list[dict]) -> list[str]:
    return [extract_scene_audio(song_path, project_dir, scene).name for scene in storyboard]
