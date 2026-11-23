import os

import requests

from agent.publishers.base import GRAPH, Publisher


class FacebookPublisher(Publisher):
    name = "facebook"

    def configured(self) -> bool:
        return bool(os.getenv("FB_PAGE_ID") and os.getenv("FB_PAGE_TOKEN"))

    def run(self, posts: dict, media: dict) -> str:
        page, token = os.environ["FB_PAGE_ID"], os.environ["FB_PAGE_TOKEN"]
        base = f"https://graph.facebook.com/{GRAPH}/{page}"
        message = posts["facebook"]

        if media.get("image"):
            with open(media["image"], "rb") as f:
                r = requests.post(f"{base}/photos", data={"message": message, "access_token": token},
                                  files={"source": f}, timeout=120)
        else:
            r = requests.post(f"{base}/feed", data={"message": message, "access_token": token}, timeout=60)
        r.raise_for_status()
        return f"posted (id {r.json().get('post_id') or r.json().get('id')})"
