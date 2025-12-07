# notifications/ntfy.py
from __future__ import annotations
import requests
from typing import Optional

from .base import Notifier


class NtfyNotifier(Notifier):
    def __init__(self, server: str, topic: str, base_public_url: str):
        self.server = server.rstrip("/")
        self.topic = topic
        self.base_public_url = base_public_url.rstrip("/")

    def _post(self, title: str, body: str) -> None:
        url = f"{self.server}/{self.topic}"
        r = requests.post(
            url,
            data=body.encode("utf-8"),
            headers={"Title": title},
            timeout=5,
        )
        r.raise_for_status()

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

        body = (
            f"{name}\n"
            f"Indexer: {indexer}\n\n"
            f"Approve: {approve_url}\n"
            f"Reject:  {reject_url}"
        )
        self._post("Torrent needs approval", body)

    def send_info(
        self,
        *,
        title: str,
        message: str,
        extra: Optional[dict] = None,
    ) -> None:
        self._post(title, message)
