"""End-to-end API test: create a run, review it, edit, approve, and check the results."""
import time

from fastapi.testclient import TestClient

from server import app as server_app


client = TestClient(server_app.app)


def wait_for(run_id, statuses, timeout=20.0):
    deadline = time.time() + timeout
    run = {}
    while time.time() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in statuses:
            return run
        time.sleep(0.1)
    raise AssertionError(f"timed out; last status {run.get('status')} error={run.get('error')}")


def test_health_and_ui_served():
    assert client.get("/api/health").json()["ok"] is True
    assert "Social Media Agent" in client.get("/").text


def test_run_review_edit_and_approve():
    res = client.post("/api/runs", json={"niche": "home coffee brewing", "live": False})
    assert res.status_code == 202
    run_id = res.json()["id"]

    run = wait_for(run_id, {"awaiting_approval", "failed"})
    assert run["status"] == "awaiting_approval", run.get("error")
    assert run["posts"]["x"] == ["Tweet 1", "Tweet 2"]
    assert run["blog"].startswith("# Blog")
    assert run["has_image"] is True
    assert client.get(f"/api/runs/{run_id}/image").status_code == 200

    edited = dict(run["posts"], linkedin="Edited by a human")
    assert client.post(f"/api/runs/{run_id}/approve", json={"approve": True, "posts": edited}).status_code == 202

    done = wait_for(run_id, {"dry_run_done", "published", "failed"})
    assert done["status"] == "dry_run_done", done.get("error")
    assert len(done["results"]) == 6
    assert done["posts"]["linkedin"] == "Edited by a human"  # the edit is the saved record
    # Approving a finished run is a conflict
    assert client.post(f"/api/runs/{run_id}/approve", json={"approve": True}).status_code == 409


def test_reject_run():
    run_id = client.post("/api/runs", json={"niche": "budget travel"}).json()["id"]
    wait_for(run_id, {"awaiting_approval"})
    client.post(f"/api/runs/{run_id}/approve", json={"approve": False})
    assert wait_for(run_id, {"rejected", "failed"})["status"] == "rejected"


def test_input_validation():
    assert client.get("/api/runs/not-a-run").status_code == 404
    assert client.post("/api/runs", json={"niche": "x"}).status_code == 422  # too short
    bad = client.post("/api/uploads", files={"file": ("notes.txt", b"hi", "text/plain")})
    assert bad.status_code == 400
    assert client.post("/api/runs", json={"niche": "abc", "video_id": "../../etc/passwd"}).status_code == 400


def test_password_protects_everything_except_health(monkeypatch):
    monkeypatch.setattr(server_app.settings, "app_password", "s3cret")
    assert client.get("/api/runs").status_code == 401
    assert client.get("/api/health").status_code == 200
    import base64
    token = base64.b64encode(b"user:s3cret").decode()
    assert client.get("/api/runs", headers={"Authorization": f"Basic {token}"}).status_code == 200
