from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VisualLanguage:
    palette: str
    lighting: str
    camera: str
    texture: str


GENRE_LANGUAGE: dict[str, VisualLanguage] = {
    "rock": VisualLanguage(
        palette="deep reds, black, charcoal, burnt orange",
        lighting="hard spotlights, rim light, smoke, high contrast",
        camera="handheld pushes, low angles, whip pans, dramatic close-ups",
        texture="film grain, haze, raw stage energy",
    ),
    "pop": VisualLanguage(
        palette="saturated pink, cyan, amber and clean neutrals",
        lighting="bright controlled key light with colorful practicals",
        camera="smooth dolly, orbit, crane-like reveals, rhythmic cuts",
        texture="polished, glossy, fashion-forward",
    ),
    "urban": VisualLanguage(
        palette="black, gold, deep purple, neon accents",
        lighting="hard shadows, street practicals, selective neon",
        camera="low-angle tracking, snap zooms, whip pans, intimate close-ups",
        texture="gritty concrete, wet streets, cinematic haze",
    ),
    "romantic": VisualLanguage(
        palette="warm gold, amber, muted rose, soft blue",
        lighting="soft backlight, golden-hour glow, practical bokeh",
        camera="slow dolly, gentle orbit, intimate portrait close-ups",
        texture="soft diffusion, subtle film grain, elegant depth of field",
    ),
    "cinematic": VisualLanguage(
        palette="controlled cinematic contrast with motivated color accents",
        lighting="motivated key light, volumetric depth, shaped shadows",
        camera="dolly, orbit, crane-like reveal, restrained handheld when emotional",
        texture="anamorphic feel, film grain, atmospheric depth",
    ),
}

CAMERA_BY_ENERGY = {
    "low": "locked or slow push-in, long lens, shallow depth of field",
    "medium": "gentle tracking and orbit movement, medium shot to close-up transitions",
    "high": "dynamic tracking, whip-pan accents, fast push-ins and wider movement",
    "peak": "rapid but readable camera changes, orbital motion and impact cuts on downbeats",
}


def _energy_band(value: float) -> str:
    if value >= 0.86:
        return "peak"
    if value >= 0.64:
        return "high"
    if value >= 0.38:
        return "medium"
    return "low"


def _genre(style: str) -> str:
    value = style.lower()
    for key in GENRE_LANGUAGE:
        if key in value:
            return key
    return "cinematic"


def classify_scene_strategy(section: str, lyrics: str, energy: float) -> str:
    sec = (section or "").lower()
    if lyrics.strip() and sec in {"verse", "chorus", "refrain", "pre-chorus", "bridge"}:
        return "performance" if energy >= 0.42 else "performance_intimate"
    if sec in {"intro", "outro", "instrumental", "interlude"}:
        return "narrative" if energy < 0.68 else "abstract"
    return "narrative"


def build_director_prompt(scene: dict[str, Any], style: str) -> dict[str, Any]:
    language = GENRE_LANGUAGE[_genre(style)]
    energy = float(scene.get("energy", 0.5) or 0.5)
    band = _energy_band(energy)
    section = str(scene.get("section", "scene"))
    lyrics = str(scene.get("lyrics", "")).strip()
    strategy = classify_scene_strategy(section, lyrics, energy)
    start = float(scene.get("start", 0.0) or 0.0)
    end = float(scene.get("end", start + 4.0) or start + 4.0)

    if section.lower() in {"chorus", "refrain"}:
        hook = "Deliver a memorable visual hook in the first two seconds, then escalate motion on strong beats."
    elif section.lower() == "bridge":
        hook = "Change the visual grammar from the previous section: new framing, palette emphasis, or location mood."
    elif section.lower() == "outro":
        hook = "Resolve the visual idea with a strong final image; reduce unnecessary movement near the end."
    else:
        hook = "Open with one immediately readable image and preserve continuity with the surrounding shots."

    subject_rule = (
        "Keep the reference artist identity consistent: same face, age, hair, body proportions and wardrobe continuity."
    )
    performance_rule = (
        "If the artist is visibly singing, frame the mouth clearly enough for lip-sync and avoid occluding the lower face."
        if strategy.startswith("performance")
        else "Do not force singing performance; prioritize cinematic storytelling and visual metaphor."
    )

    prompt = (
        f"Music-video shot from {start:.2f}s to {end:.2f}s. "
        f"Section: {section}. Strategy: {strategy}. Energy: {band}. "
        f"Style: {style}. "
        f"Palette: {language.palette}. Lighting: {language.lighting}. "
        f"Camera: {CAMERA_BY_ENERGY[band]}; overall camera language: {language.camera}. "
        f"Texture: {language.texture}. {hook} {subject_rule} {performance_rule} "
        f"Keep motion physically coherent, avoid face deformation, duplicate people, warped hands, flicker, text and logos."
    )
    if lyrics:
        prompt += f" Emotional meaning of the lyric: {lyrics}"

    return {
        "strategy": strategy,
        "energy_band": band,
        "needs_lipsync": strategy.startswith("performance") and bool(lyrics),
        "camera": CAMERA_BY_ENERGY[band],
        "palette": language.palette,
        "lighting": language.lighting,
        "director_prompt": prompt,
        "negative_prompt": (
            "identity drift, deformed face, extra fingers, duplicate person, bad anatomy, flicker, frame warping, "
            "unreadable mouth, random text, watermark, logo, low detail, oversharpening"
        ),
    }


def direct_storyboard(storyboard: list[dict[str, Any]], style: str) -> list[dict[str, Any]]:
    directed: list[dict[str, Any]] = []
    for scene in storyboard:
        enriched = dict(scene)
        enriched.update(build_director_prompt(scene, style))
        directed.append(enriched)
    return directed
