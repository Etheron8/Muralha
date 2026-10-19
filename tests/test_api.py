from fastapi.testclient import TestClient

from muralha.main import app

client = TestClient(app)


def test_health_and_catalog_endpoints():
    health = client.get("/v1/health")
    assert health.status_code == 200
    assert health.json()["catalog_loaded"] is True

    listing = client.get("/v1/challenges")
    assert listing.status_code == 200
    assert listing.json()["challenges"][0]["id"] == "authorization-bypass"

    detail = client.get("/v1/challenges/authorization-bypass")
    assert detail.status_code == 200
    assert "src/access_control.py" in detail.json()["files"]


def test_unknown_challenge_is_404():
    response = client.get("/v1/challenges/not-a-real-challenge")
    assert response.status_code == 404


def test_session_creation_and_result_lookup():
    created = client.post("/v1/sessions", json={
        "agent_name": "pytest-agent",
        "provider": "test",
        "model": "fixture",
    })
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    result = client.get(f"/v1/sessions/{session_id}/results")
    assert result.status_code == 200
    assert result.json()["submissions_count"] == 0


def test_submission_without_private_oracle_never_invents_a_score():
    created = client.post("/v1/sessions", json={"agent_name": "no-oracle-test"})
    session_id = created.json()["session_id"]
    response = client.post("/v1/submissions", json={
        "session_id": session_id,
        "challenge_id": "authorization-bypass",
        "finding": {
            "cwe": "CWE-863",
            "severity": "high",
            "file": "src/access_control.py",
            "line": 7,
            "description": "Diagnóstico de teste.",
            "fix_summary": "Correção de teste."
        },
        "candidate_files": {}
    })
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "evaluator_not_configured"
