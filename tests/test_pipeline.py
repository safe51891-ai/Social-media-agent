"""Graph-level test: the workflow pauses for review, resumes, and dry runs post nothing."""
import os
import tempfile

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agent.graph import build_graph


def test_graph_pauses_for_review_then_dry_run_posts_nothing():
    app = build_graph(MemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}}
    run_dir = os.path.join(tempfile.mkdtemp(), "run")

    out = app.invoke({"niche": "n", "run_dir": run_dir, "live": False}, cfg)
    assert "__interrupt__" in out, "graph should pause at approval"
    assert out["__interrupt__"][0].value["posts"]["x"] == ["Tweet 1", "Tweet 2"]
    assert os.path.exists(os.path.join(run_dir, "blog.md"))
    assert os.path.exists(os.path.join(run_dir, "posts.json"))

    out = app.invoke(Command(resume=True), cfg)
    results = {r["platform"]: r["status"] for r in out["publish_results"]}
    assert not any(s.startswith("posted") for s in results.values()), results
    assert results["tiktok"].startswith("skipped"), results  # no video was given


def test_rejecting_skips_publishing():
    app = build_graph(MemorySaver())
    cfg = {"configurable": {"thread_id": "t2"}}
    run_dir = os.path.join(tempfile.mkdtemp(), "run")
    app.invoke({"niche": "n", "run_dir": run_dir, "live": True}, cfg)
    out = app.invoke(Command(resume={"approve": False}), cfg)
    assert out.get("publish_results") is None
