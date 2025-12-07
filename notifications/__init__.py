# notifications/__init__.py
from __future__ import annotations
from typing import Optional

from config import ApprovarrConfig
from .base import Notifier
from .pushover import PushoverNotifier
from .ntfy import NtfyNotifier
from .discord import DiscordNotifier


def build_notifier(cfg: ApprovarrConfig) -> Optional[Notifier]:
    provider = cfg.notifications.provider.lower()

    base_public_url = cfg.server.get("external_url") or cfg.server.get("base_public_url")
    if not base_public_url:
        # You can still operate without notifications if you want
        # WARN: no you can't?
        return None

    if provider == "pushover":
        po = cfg.notifications.pushover or {}
        return PushoverNotifier(
            token=po["token"],
            user=po["user"],
            base_public_url=base_public_url,
        )

    if provider == "ntfy":
        nt = cfg.notifications.ntfy or {}
        return NtfyNotifier(
            server=nt.get("server", "https://ntfy.sh"),
            topic=nt["topic"],
            base_public_url=base_public_url,
        )

    if provider == "discord":
        dc = cfg.notifications.discord or {}
        return DiscordNotifier(
            webhook_url=dc["webhook_url"],
            base_public_url=base_public_url,
        )

    raise ValueError(f"Unknown notification provider: {provider}")
