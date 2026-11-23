"""Runs the graph in background threads so HTTP requests return right away.

Statuses a run moves through:
  running -> awaiting_approval -> publishing -> published | dry_run_done | rejected
  any step can end in failed (with an error message)
"""
from concurrent.futures import ThreadPoolExecutor

from langgraph.types import Command


class JobRunner:
    def __init__(self, store, graph, workers: int = 2):
        self.store = store
        self.graph = graph
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="agent")

    def start(self, run: dict) -> None:
        state = {
            "niche": run["niche"], "run_dir": run["run_dir"],
            "video_path": run["video_path"], "live": run["live"],
        }
        self.pool.submit(self._drive, run["id"], state)

    def resume(self, run_id: str, decision: dict) -> None:
        self.store.update(run_id, status="publishing")
        self.pool.submit(self._drive, run_id, Command(resume=decision))

    def _drive(self, run_id: str, payload) -> None:
        config = {"configurable": {"thread_id": run_id}}
        try:
            out = self.graph.invoke(payload, config)
            if "__interrupt__" in out:  # reached the review step
                self.store.update(run_id, status="awaiting_approval")
                return
            if not out.get("approved"):
                status = "rejected"
            elif self.store.get(run_id)["live"]:
                status = "published"
            else:
                status = "dry_run_done"
            self.store.update(run_id, status=status, results=out.get("publish_results", []))
        except Exception as exc:
            self.store.update(run_id, status="failed", error=f"{type(exc).__name__}: {exc}")
