import os


GRAPH = os.getenv("GRAPH_VERSION", "v21.0")  # check Meta's current Graph API version


class Publisher:
    name = ""

    def configured(self) -> bool:
        return False

    def run(self, posts: dict, media: dict) -> str:
        raise NotImplementedError

    def publish(self, posts: dict, media: dict, dry_run: bool) -> str:
        if not self.configured():
            return "skipped: credentials not set in .env"
        if dry_run:
            return f"dry-run: would post to {self.name}"
        return self.run(posts, media)


class ManualPublisher(Publisher):
    """For platforms that need a video file and an app review before API posting.
    The agent prepares the package; you upload it yourself."""

    key = ""  # key in posts.json holding the caption / title

    def publish(self, posts: dict, media: dict, dry_run: bool) -> str:
        if not media.get("video"):
            return f"skipped: {self.name} needs a rendered video (pass --video)"
        return f"manual: upload {media['video']} to {self.name} using posts.json['{self.key}']"
