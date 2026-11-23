import os

import requests
from requests_oauthlib import OAuth1

from agent.publishers.base import Publisher


class XPublisher(Publisher):
    name = "x"

    def configured(self) -> bool:
        return all(os.getenv(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"))

    def run(self, posts: dict, media: dict) -> str:
        tweets = posts["x"] if isinstance(posts["x"], list) else [posts["x"]]
        for t in tweets:
            if len(t) > 280:
                raise ValueError(f"tweet over 280 characters: {t[:40]}...")

        auth = OAuth1(
            os.environ["X_API_KEY"], os.environ["X_API_SECRET"],
            os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_SECRET"],
        )
        parent, ids = None, []
        for text in tweets:  # post as a thread: each tweet replies to the previous one
            body = {"text": text}
            if parent:
                body["reply"] = {"in_reply_to_tweet_id": parent}
            r = requests.post("https://api.x.com/2/tweets", json=body, auth=auth, timeout=30)
            r.raise_for_status()
            parent = r.json()["data"]["id"]
            ids.append(parent)
        return f"posted thread of {len(ids)} tweet(s); text only, images are not attached on X in this version"
