"""Shared test setup. Points storage at a temp folder and replaces OpenAI calls with fakes,
so the tests run offline and never post anywhere."""
import json
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

_TMP = tempfile.mkdtemp(prefix="social-agent-test-")
os.environ["DATA_DIR"] = os.path.join(_TMP, "data")
os.environ["OUTPUT_DIR"] = os.path.join(_TMP, "output")
os.environ["MAKE_IMAGES"] = "true"
os.environ["APP_PASSWORD"] = ""  # tests that need a password set it themselves

from agent import llm  # noqa: E402

POSTS = {
    "x": ["Tweet 1", "Tweet 2"],
    "linkedin": "LinkedIn post",
    "facebook": "Facebook post",
    "instagram": "Caption #one #two",
    "tiktok": "TikTok caption",
    "youtube": {"title": "Title", "description": "Description"},
}


def fake_ask(instructions, prompt, web=False):
    if "research analyst" in instructions:
        assert web is True, "research must use web search"
        return "- trend one"
    if "content strategist" in instructions:
        return json.dumps({"topic": "t", "angle": "a", "hook": "h", "keywords": ["k"], "cta": "c"})
    if "platform-native" in instructions:
        return json.dumps(POSTS)
    if "image generation" in instructions:
        return "a prompt"
    if "video scripts" in instructions:
        return "scene 1"
    return "# Blog"


def fake_image(prompt, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(b"fake-png")
    return out_path


llm.ask = fake_ask
llm.image = fake_image
