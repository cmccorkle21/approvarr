# qbittorrent_client.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import requests

from config import QbitConfig, ApprovarrConfig


@dataclass
class QbitClient:
    cfg: QbitConfig
    session: requests.Session = field(default_factory=requests.Session)
    _logged_in: bool = False

    @property
    def base_url(self) -> str:
        # no trailing slash
        return self.cfg.url.rstrip("/")

    def _post(
        self, path: str, data: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """Internal helper for POST requests."""
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, data=data or {}, timeout=5)
        print(f"[QBT] POST {url} -> {resp.status_code} {resp.text[:200]!r}")
        return resp

    def _get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """Internal helper for GET requests."""
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params or {}, timeout=5)
        print(f"[QBT] GET {url} -> {resp.status_code} {resp.text[:200]!r}")
        return resp

    def login(self) -> None:
        """Login once; reuse session cookie."""
        if self._logged_in:
            return

        resp = self._post(
            "/api/v2/auth/login",
            data={"username": self.cfg.username, "password": self.cfg.password},
        )
        resp.raise_for_status()
        if resp.text.strip() != "Ok.":
            raise RuntimeError(f"qBittorrent login failed: {resp.text}")
        self._logged_in = True

    def ensure_login(self) -> None:
        """Call before operations; re-login if needed."""
        try:
            self.login()
        except Exception as e:
            # could add smarter logic here if you want
            raise

    # ------------- Public API methods -------------

    def add_tags(self, torrent_hash: str, tags: list[str]) -> None:
        self.ensure_login()
        resp = self._post(
            "/api/v2/torrents/addTags",
            data={"hashes": torrent_hash, "tags": ",".join(tags)},
        )
        resp.raise_for_status()

    def remove_tag(self, torrent_hash: str, tag: str) -> None:
        self.ensure_login()
        resp = self._post(
            "/api/v2/torrents/removeTags",
            data={"hashes": torrent_hash, "tags": tag},
        )
        resp.raise_for_status()

    def pause(self, torrent_hash: str) -> None:
        """Pause/stop torrent; supports qBittorrent v5 (stop) and v4 (pause)."""
        self.ensure_login()
        data = {"hashes": torrent_hash}

        # Try v5-style endpoint first
        resp = self._post("/api/v2/torrents/stop", data)
        if resp.status_code == 404:
            # fall back to legacy pause
            resp = self._post("/api/v2/torrents/pause", data)

        resp.raise_for_status()

    def resume(self, torrent_hash: str) -> None:
        """Resume/start torrent; supports v5 (start) and v4 (resume)."""
        self.ensure_login()
        data = {"hashes": torrent_hash}

        resp = self._post("/api/v2/torrents/start", data)
        if resp.status_code == 404:
            resp = self._post("/api/v2/torrents/resume", data)

        resp.raise_for_status()

    def delete(self, torrent_hash: str, delete_files: bool = True) -> None:
        self.ensure_login()
        resp = self._post(
            "/api/v2/torrents/delete",
            data={
                "hashes": torrent_hash,
                "deleteFiles": "true" if delete_files else "false",
            },
        )
        resp.raise_for_status()

    def list_all(self) -> list[dict[str, Any]]:
        """Optional helper if you ever want to search torrents by name/size/etc."""
        self.ensure_login()
        resp = self._get("/api/v2/torrents/info")
        resp.raise_for_status()
        return resp.json()


# ---------- Factory for the rest of your app ----------


def build_qbit_client(cfg: ApprovarrConfig) -> QbitClient:
    return QbitClient(cfg.qbit)
