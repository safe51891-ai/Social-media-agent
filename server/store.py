"""A small SQLite table with one row per run. The graph's own checkpoints live in a separate file."""
import json
import os
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,
    niche       TEXT NOT NULL,
    live        INTEGER NOT NULL,
    status      TEXT NOT NULL,
    error       TEXT,
    video_path  TEXT,
    run_dir     TEXT NOT NULL,
    results     TEXT,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
)
"""


class RunStore:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")  # readers do not block the writer
        self._db.execute(SCHEMA)
        self._db.commit()

    def create(self, run: dict) -> None:
        now = time.time()
        row = {
            "id": run["id"], "niche": run["niche"], "live": int(run["live"]),
            "status": "running", "error": None, "video_path": run["video_path"],
            "run_dir": run["run_dir"], "results": None, "created_at": now, "updated_at": now,
        }
        with self._lock:
            self._db.execute(
                f"INSERT INTO runs ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
                tuple(row.values()),
            )
            self._db.commit()

    def update(self, run_id: str, **fields) -> None:
        # Column names come from this code, never from user input, so the f-string is safe.
        fields["updated_at"] = time.time()
        if "results" in fields:
            fields["results"] = json.dumps(fields["results"])
        assignments = ", ".join(f"{column} = ?" for column in fields)
        with self._lock:
            self._db.execute(f"UPDATE runs SET {assignments} WHERE id = ?", (*fields.values(), run_id))
            self._db.commit()

    def get(self, run_id: str) -> dict | None:
        row = self._db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return self._to_dict(row) if row else None

    def list(self, limit: int = 50) -> list[dict]:
        rows = self._db.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._to_dict(r) for r in rows]

    @staticmethod
    def _to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["live"] = bool(d["live"])
        d["results"] = json.loads(d["results"]) if d["results"] else []
        return d
