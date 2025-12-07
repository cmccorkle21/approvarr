# notifications/pushover.py
from __future__ import annotations

from typing import Optional

import requests

from .base import Notifier


class PushoverNotifier(Notifier):
    def __init__(self, token: str, user: str, base_public_url: str):
        self.token = token
        self.user = user
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
        reject_url = f"{self.base_public_url}/reject/{torrent_hash}"

        msg = (
            f"Indexer: {indexer}\n"
            f"Release: {name}\n\n"
            f"Approve: {approve_url}\n"
            f"Reject:  {reject_url}"
        )

        r = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": self.token,
                "user": self.user,
                "title": "Torrent needs approval",
                "message": msg,
                "priority": 0,
            },
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
        r = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": self.token,
                "user": self.user,
                "title": title,
                "message": message,
                "priority": 0,
            },
            timeout=5,
        )
        r.raise_for_status()
