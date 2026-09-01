from __future__ import annotations

from pathlib import Path
from typing import Any


def analyze_audio(path: Path) -> dict[str, Any]:
    """Analyze tempo, beats and rough musical sections locally.

    Uses librosa when available. If librosa is not installed or decoding fails,
    returns a safe fallback payload so the rest of the app still works.
    """
    try:
        import librosa
        import numpy as np

        y, sr = librosa.load(str(path), sr=22050, mono=True)
        if y.size == 0:
            raise ValueError("empty audio")

        duration = float(librosa.get_duration(y=y, sr=sr))
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
        tempo_value = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 0.0
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        rms_times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=512)
        if len(rms):
            lo = float(np.percentile(rms, 25))
            hi = float(np.percentile(rms, 75))
        else:
            lo = hi = 0.0

        # Novelty from chroma change gives useful approximate section boundaries
        # without an LLM or cloud service.
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        if chroma.shape[1] > 2:
            delta = np.linalg.norm(np.diff(chroma, axis=1), axis=0)
            threshold = float(np.percentile(delta, 88))
            candidate_frames = np.where(delta >= threshold)[0] + 1
            candidate_times = librosa.frames_to_time(candidate_frames, sr=sr).tolist()
        else:
            candidate_times = []

        min_gap = 8.0
        boundaries = [0.0]
        for t in candidate_times:
            t = float(t)
            if t - boundaries[-1] >= min_gap and duration - t >= 4.0:
                boundaries.append(t)
        if duration - boundaries[-1] > 1.0:
            boundaries.append(duration)
        elif boundaries:
            boundaries[-1] = duration

        sections = []
        for idx in range(max(0, len(boundaries) - 1)):
            start, end = float(boundaries[idx]), float(boundaries[idx + 1])
            mask = (rms_times >= start) & (rms_times < end)
            energy = float(rms[mask].mean()) if mask.any() else 0.0
            if energy >= hi:
                level = "high"
            elif energy <= lo:
                level = "low"
            else:
                level = "medium"
            sections.append({
                "id": idx + 1,
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "energy": level,
                "energy_value": round(energy, 6),
            })

        return {
            "engine": "librosa",
            "duration": round(duration, 3),
            "bpm": round(tempo_value, 2),
            "beats": [round(float(x), 3) for x in beat_times],
            "sections": sections,
        }
    except Exception as exc:
        return {
            "engine": "fallback",
            "bpm": None,
            "beats": [],
            "sections": [],
            "warning": str(exc),
        }
