from __future__ import annotations

from pathlib import Path
from typing import Any


def transcribe_local(audio_path: Path, model_size: str = "small") -> dict[str, Any]:
    """Transcribe audio locally with faster-whisper when installed.

    Returns a stable payload even when faster-whisper is unavailable so the
    application can keep working with manually supplied lyrics.
    """
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        return {
            "available": False,
            "reason": f"faster-whisper no disponible: {exc}",
            "language": None,
            "segments": [],
            "words": [],
        }

    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments_iter, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
        )
        segments = []
        words = []
        for index, seg in enumerate(segments_iter, start=1):
            item = {
                "id": index,
                "start": round(float(seg.start), 3),
                "end": round(float(seg.end), 3),
                "text": (seg.text or "").strip(),
            }
            segments.append(item)
            for word in seg.words or []:
                words.append({
                    "start": round(float(word.start), 3),
                    "end": round(float(word.end), 3),
                    "word": (word.word or "").strip(),
                    "probability": round(float(word.probability), 4),
                })
        return {
            "available": True,
            "language": getattr(info, "language", None),
            "language_probability": round(float(getattr(info, "language_probability", 0.0)), 4),
            "segments": segments,
            "words": words,
        }
    except Exception as exc:
        return {
            "available": False,
            "reason": str(exc),
            "language": None,
            "segments": [],
            "words": [],
        }


def infer_sections(segments: list[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    """Create deterministic verse/chorus/bridge-like regions without a paid LLM.

    This is intentionally conservative: it partitions the song into musical
    regions that can later be refined using beat/energy analysis or manual edits.
    """
    if duration <= 0:
        return []

    if not segments:
        labels = ["intro", "verse", "chorus", "verse", "chorus", "bridge", "final_chorus", "outro"]
        step = duration / len(labels)
        return [
            {
                "label": label,
                "start": round(i * step, 3),
                "end": round(duration if i == len(labels) - 1 else (i + 1) * step, 3),
            }
            for i, label in enumerate(labels)
        ]

    # Use speech density to identify likely instrumental intro/outro and divide
    # the sung body into repeatable editorial regions.
    first_voice = max(0.0, min(duration, float(segments[0]["start"])))
    last_voice = max(first_voice, min(duration, float(segments[-1]["end"])))
    body = max(0.1, last_voice - first_voice)
    body_labels = ["verse", "chorus", "verse", "chorus", "bridge", "final_chorus"]
    step = body / len(body_labels)

    result: list[dict[str, Any]] = []
    if first_voice > 1.0:
        result.append({"label": "intro", "start": 0.0, "end": round(first_voice, 3)})
    for i, label in enumerate(body_labels):
        start = first_voice + i * step
        end = last_voice if i == len(body_labels) - 1 else first_voice + (i + 1) * step
        result.append({"label": label, "start": round(start, 3), "end": round(end, 3)})
    if duration - last_voice > 1.0:
        result.append({"label": "outro", "start": round(last_voice, 3), "end": round(duration, 3)})
    return result
