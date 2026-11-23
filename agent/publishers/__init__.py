from agent.publishers.base import ManualPublisher
from agent.publishers.facebook import FacebookPublisher
from agent.publishers.instagram import InstagramPublisher
from agent.publishers.linkedin import LinkedInPublisher
from agent.publishers.x import XPublisher


class TikTok(ManualPublisher):
    name = "tiktok"
    key = "tiktok"


class YouTube(ManualPublisher):
    name = "youtube"
    key = "youtube"


PUBLISHERS = {p.name: p for p in [
    XPublisher(),
    LinkedInPublisher(),
    FacebookPublisher(),
    InstagramPublisher(),
    TikTok(),
    YouTube(),
]}
