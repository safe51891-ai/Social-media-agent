"""HTTP API and web UI.

Run locally:  python -m server        then open http://127.0.0.1:8000
API docs:     http://127.0.0.1:8000/docs
"""
import base64
import json
import os
import re
import secrets
import sqlite3
import time
import uuid

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import BaseModel, Field

from agent.config import settings
from agent.graph import build_graph
from server.jobs import JobRunner
from server.store import RunStore

UPLOAD_DIR = os.path.join(settings.data_dir, "uploads")
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "web")
RUN_ID_PATTERN = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")
VIDEO_ID_PATTERN = re.compile(r"^[0-9a-f]{32}\.(mp4|mov|webm)$")
MAX_VIDEO_BYTES = 500 * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)
store = RunStore(os.path.join(settings.data_dir, "runs.db"))
checkpointer = SqliteSaver(
    sqlite3.connect(os.path.join(settings.data_dir, "checkpoints.db"), check_same_thread=False)
)
jobs = JobRunner(store, build_graph(checkpointer))

app = FastAPI(title="Social Media Agent", version="1.0")


# ---- Optional password (HTTP Basic). Set APP_PASSWORD before exposing the app. ----

@app.middleware("http")
async def require_password(request: Request, call_next):
    password = settings.app_password
    if password and request.url.path != "/api/health":
        header = request.headers.get("authorization", "")
        ok = False
        if header.startswith("Basic "):
            try:
                _, supplied = base64.b64decode(header[6:]).decode().split(":", 1)
                ok = secrets.compare_digest(supplied, password)
            except ValueError:
                ok = False
        if not ok:
            return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="social-agent"'})
    return await call_next(request)


# ---- Helpers ----------------------------------------------------------------

def _get_run(run_id: str) -> dict:
    run = store.get(run_id) if RUN_ID_PATTERN.match(run_id) else None
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


def _public(run: dict) -> dict:
    """Hide server file paths from API responses."""
    out = {k: v for k, v in run.items() if k not in ("run_dir", "video_path")}
    out["video"] = bool(run.get("video_path"))
    return out


def _read_text(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---- API --------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"ok": True, "openai_key_set": bool(settings.openai_api_key)}


class RunCreate(BaseModel):
    niche: str = Field(min_length=2, max_length=200)
    live: bool = False
    video_id: str | None = None


class Decision(BaseModel):
    approve: bool
    posts: dict | None = None  # reviewer's edited drafts; omit to publish as generated


@app.post("/api/uploads", status_code=201)
async def upload_video(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".mp4", ".mov", ".webm"):
        raise HTTPException(status_code=400, detail="Video must be .mp4, .mov or .webm")
    video_id = uuid.uuid4().hex + ext
    path = os.path.join(UPLOAD_DIR, video_id)
    size = 0
    try:
        with open(path, "wb") as out:
            while chunk := await file.read(1 << 20):
                size += len(chunk)
                if size > MAX_VIDEO_BYTES:
                    raise HTTPException(status_code=413, detail="Video is larger than 500 MB")
                out.write(chunk)
    except HTTPException:
        os.remove(path)
        raise
    return {"video_id": video_id}


@app.post("/api/runs", status_code=202)
def create_run(body: RunCreate):
    video_path = None
    if body.video_id:
        if not VIDEO_ID_PATTERN.match(body.video_id):
            raise HTTPException(status_code=400, detail="Unknown video_id")
        video_path = os.path.join(UPLOAD_DIR, body.video_id)
        if not os.path.exists(video_path):
            raise HTTPException(status_code=400, detail="Unknown video_id")

    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    run = {
        "id": run_id, "niche": body.niche.strip(), "live": body.live,
        "video_path": video_path, "run_dir": os.path.join(settings.output_dir, run_id),
    }
    store.create(run)
    jobs.start(run)
    return _public(store.get(run_id))


@app.get("/api/runs")
def list_runs():
    return [_public(r) for r in store.list()]


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = _get_run(run_id)
    run_dir = run["run_dir"]
    posts_text = _read_text(os.path.join(run_dir, "posts.json"))
    return {
        **_public(run),
        "posts": json.loads(posts_text) if posts_text else None,
        "blog": _read_text(os.path.join(run_dir, "blog.md")),
        "video_script": _read_text(os.path.join(run_dir, "video_script.md")),
        "has_image": os.path.exists(os.path.join(run_dir, "image.png")),
    }


@app.post("/api/runs/{run_id}/approve", status_code=202)
def decide(run_id: str, body: Decision):
    run = _get_run(run_id)
    if run["status"] != "awaiting_approval":
        raise HTTPException(status_code=409, detail=f"run is '{run['status']}', not awaiting approval")
    jobs.resume(run_id, {"approve": body.approve, "posts": body.posts})
    return {"ok": True}


@app.get("/api/runs/{run_id}/image")
def get_image(run_id: str):
    run = _get_run(run_id)
    path = os.path.join(run["run_dir"], "image.png")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="no image for this run")
    return FileResponse(path, media_type="image/png")


# ---- Web UI (must be mounted last so /api routes win) -----------------------

app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
