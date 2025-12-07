# notifications/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional


class Notifier(Protocol):
    def send_approval(
        self,
        *,
        name: str,
        size: str,
        torrent_hash: str,
        indexer: str,
        extra: Optional[dict] = None,
    ) -> None:
        ...

    def send_info(
        self,
        *,
        title: str,
        message: str,
        extra: Optional[dict] = None,
    ) -> None:
        ...
