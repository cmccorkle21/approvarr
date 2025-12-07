# notifications/discord.py
from __future__ import annotations
import requests
from typing import Optional

from .base import Notifier


class DiscordNotifier(Notifier):
    def __init__(self, webhook_url: str, base_public_url: str):
        self.webhook_url = webhook_url
        self.base_public_url = base_public_url.rstrip("/")

    def send_approval(
        self,
        *,
        name: str,
        torrent_hash: str,
        indexer: str,
        extra: Optional[dict] = None,
    ) -> None:
        approve_url = f"{self.base_public_url}/approve/{torrent_hash}"
        reject_url  = f"{self.base_public_url}/reject/{torrent_hash}"

        content = (
            f"**Torrent needs approval**\n"
            f"**Name:** {name}\n"
            f"**Indexer:** {indexer}\n\n"
            f"[✅ Approve]({approve_url}) | [🗑️ Reject]({reject_url})"
        )
        r = requests.post(
            self.webhook_url,
            json={"content": content},
            timeout=5,
        )
        r.raise_for_status()

    def send_info(
        self,
        *,
        title: str,
        message: str,
        extra: Optional[dict] = None,
    ) -> None:
        content = f"**{title}**\n{message}"
        r = requests.post(
            self.webhook_url,
            json={"content": content},
            timeout=5,
        )
        r.raise_for_status()
