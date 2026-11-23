import os

import requests

from agent.publishers.base import Publisher


class LinkedInPublisher(Publisher):
    name = "linkedin"

    def configured(self) -> bool:
        return bool(os.getenv("LINKEDIN_TOKEN") and os.getenv("LINKEDIN_AUTHOR_URN"))

    def run(self, posts: dict, media: dict) -> str:
        headers = {
            "Authorization": f"Bearer {os.environ['LINKEDIN_TOKEN']}",
            "Linkedin-Version": os.getenv("LINKEDIN_API_VERSION", "202506"),
            "X-Restli-Protocol-Version": "2.0.0",
        }
        body = {
            "author": os.environ["LINKEDIN_AUTHOR_URN"],  # urn:li:person:... or urn:li:organization:...
            "commentary": posts["linkedin"],
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                             "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        r = requests.post("https://api.linkedin.com/rest/posts", json=body, headers=headers, timeout=30)
        r.raise_for_status()
        return f"posted (id {r.headers.get('x-restli-id')}); text only in this version"
