from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pipeline import PROJECTS, load_project, save_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    row = next((x for x in meta.get("storyboard", []) if int(x.get("id", -1)) == scene_id), None)
    if row is None:
        raise KeyError(scene_id)
    return row


def add_scene_version(project_id: str, scene_id: int, file_path: str, stage: str, note: str = "") -> dict[str, Any]:
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = _scene(meta, scene_id)
    versions = scene.setdefault("versions", [])
    item = {
        "id": len(versions) + 1,
        "file": file_path,
        "stage": stage,
        "note": note,
        "created_at": _now(),
        "approved": False,
    }
    versions.append(item)
    save_json(project_dir / "project.json", meta)
    return item


def add_review_comment(project_id: str, scene_id: int, text: str, timestamp: float | None = None) -> dict[str, Any]:
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = _scene(meta, scene_id)
    comments = scene.setdefault("review_comments", [])
    item = {
        "id": len(comments) + 1,
        "text": text.strip(),
        "timestamp": None if timestamp is None else round(float(timestamp), 3),
        "created_at": _now(),
    }
    comments.append(item)
    save_json(project_dir / "project.json", meta)
    return item


def approve_version(project_id: str, scene_id: int, version_id: int) -> dict[str, Any]:
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = _scene(meta, scene_id)
    found = None
    for version in scene.setdefault("versions", []):
        version["approved"] = int(version.get("id", -1)) == version_id
        if version["approved"]:
            found = version
    if found is None:
        raise KeyError(version_id)
    scene["approved_version"] = version_id
    scene["approved_asset"] = found.get("file")
    scene["approved"] = True
    scene["status"] = "approved"
    save_json(project_dir / "project.json", meta)
    return found


def review_summary(project_id: str) -> dict[str, Any]:
    meta = load_project(project_id)
    rows = []
    for scene in meta.get("storyboard", []):
        rows.append({
            "scene_id": scene.get("id"),
            "status": scene.get("status"),
            "approved": bool(scene.get("approved")),
            "approved_version": scene.get("approved_version"),
            "versions": len(scene.get("versions", [])),
            "comments": len(scene.get("review_comments", [])),
        })
    return {"project_id": project_id, "scenes": rows}
