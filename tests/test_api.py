
from fastapi.testclient import TestClient

from api import main as api_module


client = TestClient(api_module.app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_empty_request_is_rejected():
    response = client.post(
        "/requests",
        json={"message": ""},
    )

    assert response.status_code == 422


def test_equipment_request(monkeypatch):
    class FakeGraph:
        async def ainvoke(self, input, config):
            return {
                "final_response": (
                    "Machine M-103 requires maintenance."
                )
            }

    monkeypatch.setattr( # temporarily replaces the real LangGraph instance with a test implementation. Because we want to verify FastAPI's HTTP behavior without spending money on LLM calls or depending on external services.
        api_module,
        "graph",
        FakeGraph(),
    )

    response = client.post(
        "/requests",
        json={
            "message": "Check machine M-103."
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "completed"
    assert data["thread_id"]
    assert "M-103" in data["response"]
