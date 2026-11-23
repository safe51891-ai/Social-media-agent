"""Command-line runner. The web UI does the same thing with a browser.

  python main.py "home coffee brewing"               # dry run: drafts only
  python main.py "AI agents for small business" --video clip.mp4
  python main.py "home coffee brewing" --live        # post after you approve
"""
import argparse
import json
import os
import time
import uuid

from langgraph.types import Command

from agent.config import settings
from agent.graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Social media content agent")
    parser.add_argument("niche", help="the niche or topic to research and post about")
    parser.add_argument("--video", help="rendered video file, used for TikTok and YouTube")
    parser.add_argument("--live", action="store_true", help="actually post (default is dry run)")
    args = parser.parse_args()

    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    run_dir = os.path.join(settings.output_dir, run_id)
    state = {"niche": args.niche, "run_dir": run_dir, "video_path": args.video, "live": args.live}
    config = {"configurable": {"thread_id": run_id}}

    app = build_graph()
    print(f"Mode: {'LIVE' if args.live else 'DRY RUN'} | Output: {run_dir}")
    result = app.invoke(state, config)

    while "__interrupt__" in result:  # the graph paused for review
        review = result["__interrupt__"][0].value
        print("\n=== REVIEW ===")
        print(json.dumps(review["posts"], indent=2, ensure_ascii=False))
        answer = input("\nPublish these posts? [y/N] ").strip().lower()
        result = app.invoke(Command(resume=answer in ("y", "yes")), config)

    print("\n=== RESULTS ===")
    for r in result.get("publish_results") or [{"platform": "-", "status": "not published"}]:
        print(f"{r['platform']:10} {r['status']}")
    print(f"\nDrafts saved in: {run_dir}")


if __name__ == "__main__":
    main()
