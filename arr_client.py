# arr_client.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, List, Any, Dict

import requests

from config import ApprovarrConfig


ArrType = Literal["sonarr", "radarr"]


@dataclass
class ArrInstance:
    name: str
    type: ArrType
    url: str
    api_key: str


@dataclass
class ArrClient:
    instances: List[ArrInstance]
    session: requests.Session = field(default_factory=requests.Session)

    def _base_url(self, inst: ArrInstance) -> str:
        return inst.url.rstrip("/")

    def _headers(self, inst: ArrInstance) -> Dict[str, str]:
        return {"X-Api-Key": inst.api_key}

    def _get_queue(self, inst: ArrInstance) -> list[dict[str, Any]]:
        resp = self.session.get(
            f"{self._base_url(inst)}/api/v3/queue",
            headers=self._headers(inst),
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()

    def remove_by_download_id(
        self,
        download_id: str,
        blocklist: bool = True,
        remove_from_client: bool = False,
    ) -> None:
        """
        For each configured *Arr instance:
        - Find any queue items whose downloadId == torrent hash
        - DELETE them from the queue, optionally blocklisting.
        """
        for inst in self.instances:
            try:
                queue = self._get_queue(inst)
            except Exception as e:
                print(f"[ARR] Failed to fetch queue from {inst.name}: {e}")
                continue

            for item in queue:
                if item.get("downloadId") != download_id:
                    continue

                qid = item.get("id")
                if qid is None:
                    continue

                params = {
                    "removeFromClient": str(remove_from_client).lower(),
                    "blocklist": str(blocklist).lower(),
                }

                try:
                    resp = self.session.delete(
                        f"{self._base_url(inst)}/api/v3/queue/{qid}",
                        headers=self._headers(inst),
                        params=params,
                        timeout=5,
                    )
                    print(
                        f"[ARR] DELETE queue/{qid} on {inst.name} "
                        f"-> {resp.status_code} {resp.text[:200]!r}"
                    )
                    resp.raise_for_status()
                except Exception as e:
                    print(f"[ARR] Failed to delete queue item {qid} from {inst.name}: {e}")


def build_arr_client(cfg: ApprovarrConfig) -> ArrClient:
    instances: list[ArrInstance] = []

    for raw in cfg.__dict__.get("arr", []) if hasattr(cfg, "arr") else []:
        # if you wire 'arr' into ApprovarrConfig properly, this becomes just cfg.arr
        instances.append(
            ArrInstance(
                name=raw["name"],
                type=raw.get("type", "sonarr"),
                url=raw["url"],
                api_key=raw["api_key"],
            )
        )

    return ArrClient(instances)
