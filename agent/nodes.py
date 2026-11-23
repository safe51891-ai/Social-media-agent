"""Graph nodes. Each node takes the state and returns only the keys it changes."""
import json
import os
import re

from langgraph.types import interrupt

from agent import llm
from agent.publishers import PUBLISHERS


def _parse_json(text: str) -> dict:
    """Parse model output that should be JSON, tolerating ```json fences."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return json.loads(cleaned)


def _save(run_dir: str, name: str, content: str) -> None:
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, name), "w", encoding="utf-8") as f:
        f.write(content)


# ---- Research and planning ------------------------------------------------

def research(state):
    notes = llm.ask(
        "You are a social media research analyst. Prefer recent, dated sources and flag anything uncertain.",
        f"Research the niche: {state['niche']}.\n"
        "Find what is trending now, the questions the audience asks, what competitors already cover, "
        "and the gaps nobody covers well. Answer as bullet points and list the sources you used.",
        web=True,
    )
    return {"research": notes}


def plan(state):
    raw = llm.ask(
        "You are a content strategist. Reply with JSON only.",
        f"Niche: {state['niche']}\n\nResearch:\n{state['research']}\n\n"
        "Pick the single best content idea. Return JSON: "
        '{"topic": str, "angle": str, "hook": str, "keywords": [str], "cta": str}',
    )
    return {"brief": _parse_json(raw)}


# ---- Content creation (these three run in parallel after plan) ------------

def write_blog(state):
    b = state["brief"]
    blog = llm.ask(
        "You write accurate, readable blog posts in Markdown.",
        f"Write an 800-900 word blog post.\nTopic: {b['topic']}\nAngle: {b['angle']}\n"
        f"Opening hook: {b['hook']}\nKeywords: {', '.join(b['keywords'])}\n"
        f"End with this call to action: {b['cta']}\n"
        "Start with an H1 title and a one-line meta description. Do not invent statistics; "
        "mark any figure that needs checking with [verify].",
    )
    _save(state["run_dir"], "blog.md", blog)
    return {"blog": blog}


def write_video(state):
    b = state["brief"]
    script = llm.ask(
        "You write short-form video scripts with scene timing.",
        "Write a 45-second vertical video script for TikTok, Reels and Shorts.\n"
        f"Topic: {b['topic']}\nHook: {b['hook']}\n"
        "Format each scene as: scene number, duration, on-screen text, voiceover, visual note. "
        "Finish with a YouTube title and a short description.",
    )
    _save(state["run_dir"], "video_script.md", script)
    return {"video_script": script}


def make_images(state):
    from agent.config import settings  # local import keeps tests free of config side effects

    if not settings.make_images:
        return {"image_path": None}
    b = state["brief"]
    prompt = llm.ask(
        "You write image generation prompts. Reply with the prompt text only.",
        f"One square social media image for this topic: {b['topic']}. "
        "Clean, modern, no text, no logos, no real people.",
    )
    path = os.path.join(state["run_dir"], "image.png")
    llm.image(prompt.strip(), path)
    return {"image_path": path}


def write_posts(state):
    b = state["brief"]
    raw = llm.ask(
        "You write platform-native social posts. Output only JSON.",
        f"Topic: {b['topic']}\nAngle: {b['angle']}\nHook: {b['hook']}\nCTA: {b['cta']}\n"
        f"Blog excerpt:\n{state['blog'][:2000]}\n\n"
        "Return JSON with these keys:\n"
        '- "x": array of up to 4 tweets (each 270 characters or fewer), forming a thread\n'
        '- "linkedin": professional post, 600-1200 characters\n'
        '- "facebook": friendly conversational post\n'
        '- "instagram": caption ending with 5-10 relevant hashtags\n'
        '- "tiktok": caption of 150 characters or fewer\n'
        '- "youtube": {"title": 70 characters or fewer, "description": string}',
    )
    posts = _parse_json(raw)
    _save(state["run_dir"], "posts.json", json.dumps(posts, indent=2, ensure_ascii=False))
    return {"posts": posts}


# ---- Human review and publishing -------------------------------------------

def approve(state):
    """Pause for a human. The caller resumes with {"approve": bool, "posts": edited_or_None}."""
    decision = interrupt({
        "posts": state["posts"],
        "image_path": state.get("image_path"),
        "run_dir": state["run_dir"],
    })
    if isinstance(decision, dict):
        approved = bool(decision.get("approve"))
        edited = decision.get("posts")
    else:  # plain True/False, used by the CLI
        approved, edited = bool(decision), None

    if approved and edited:  # keep the reviewer's edits as the saved record
        _save(state["run_dir"], "posts.json", json.dumps(edited, indent=2, ensure_ascii=False))
        return {"approved": True, "posts": edited}
    return {"approved": approved}


def route_after_approval(state):
    return "publish" if state.get("approved") else "end"


def publish(state):
    live = bool(state.get("live"))
    media = {"image": state.get("image_path"), "video": state.get("video_path")}
    results = []
    for name, publisher in PUBLISHERS.items():
        try:
            status = publisher.publish(state["posts"], media, dry_run=not live)
        except Exception as exc:  # one platform failing must not stop the others
            status = f"error: {exc}"
        results.append({"platform": name, "status": status})
    return {"publish_results": results}
