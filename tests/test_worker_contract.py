from fastapi.testclient import TestClient

from app.main_v2 import app

client = TestClient(app)


def test_v1_health_has_contract_fields():
    response = client.get("/api/v1/health", headers={"x-request-id": "test-request-123"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["version"] == "1.0"
    assert payload["request_id"] == "test-request-123"
    assert payload["service"] == "ai-music-video-studio-worker"
    assert payload["status"] in {"ready", "degraded"}
    assert "comfyui" in payload
    assert response.headers["x-request-id"] == "test-request-123"
    assert response.headers["x-worker-version"] == "0.14.0"


def test_v1_capabilities_documents_core_contract():
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["version"] == "1.0"
    assert payload["request_id"]
    assert payload["capabilities"]["project_persistence"] is True
    assert payload["capabilities"]["image_generation"] is True
    assert payload["capabilities"]["video_generation"] is True
    assert "scene_generate" in payload["contract"]
    assert "assemble" in payload["contract"]


def test_legacy_health_remains_available():
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "comfyui" in payload
    assert response.headers.get("x-request-id")
