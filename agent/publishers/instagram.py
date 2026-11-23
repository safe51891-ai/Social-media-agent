import os

import requests

from agent.config import settings
from agent.publishers.base import GRAPH, Publisher


class InstagramPublisher(Publisher):
    """Instagram Graph API. It needs a business account and a PUBLIC image URL,
    so the image folder must be served at PUBLIC_MEDIA_BASE_URL."""

    name = "instagram"

    def configured(self) -> bool:
        return all(os.getenv(k) for k in ("IG_USER_ID", "IG_ACCESS_TOKEN", "PUBLIC_MEDIA_BASE_URL"))

    def publish(self, posts: dict, media: dict, dry_run: bool) -> str:
        if not media.get("image"):
            return "skipped: Instagram needs an image"
        return super().publish(posts, media, dry_run)

    def run(self, posts: dict, media: dict) -> str:
        token, uid = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
        rel = os.path.relpath(media["image"], settings.output_dir).replace(os.sep, "/")
        image_url = os.environ["PUBLIC_MEDIA_BASE_URL"].rstrip("/") + "/" + rel
        base = f"https://graph.facebook.com/{GRAPH}/{uid}"

        c = requests.post(f"{base}/media", data={"image_url": image_url, "caption": posts["instagram"],
                                                 "access_token": token}, timeout=60)
        c.raise_for_status()
        p = requests.post(f"{base}/media_publish", data={"creation_id": c.json()["id"],
                                                         "access_token": token}, timeout=60)
        p.raise_for_status()
        return f"posted (id {p.json().get('id')})"
