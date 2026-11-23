from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    niche: str
    run_dir: str
    live: bool                     # False = dry run, nothing is posted
    video_path: Optional[str]      # optional rendered video for TikTok / YouTube
    research: str
    brief: dict[str, Any]          # topic, angle, hook, keywords, cta
    blog: str
    video_script: str
    image_path: Optional[str]
    posts: dict[str, Any]          # one entry per platform
    approved: bool
    publish_results: list[dict[str, str]]
