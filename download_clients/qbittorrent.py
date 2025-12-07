def post(path, data=None):
    url = f"{QBT_URL}{path}"
    resp = session.post(url, data=data or {}, timeout=5)
    print(f"[QBT] POST {url} -> {resp.status_code} {resp.text[:200]!r}")
    resp.raise_for_status()
    return resp


def login():
    post("/api/v2/auth/login", {"username": QBT_USER, "password": QBT_PASS})


def pause(torrent_hash: str):
    post("/api/v2/torrents/stop", {"hashes": torrent_hash})
    print(f"pausing hash: {torrent_hash}")


def add_tags(torrent_hash: str, tags):
    post(
        "/api/v2/torrents/addTags", {"hashes": torrent_hash, "tags": ",".join(tags)}
    )


def resume(torrent_hash: str):
    post("/api/v2/torrents/start", {"hashes": torrent_hash})


def remove_tag(torrent_hash: str, tag: str):
    post("/api/v2/torrents/removeTags", {"hashes": torrent_hash, "tags": tag})


def delete(torrent_hash: str, delete_files: bool = True):
    post(
        "/api/v2/torrents/delete",
        {"hashes": torrent_hash, "deleteFiles": "true" if delete_files else "false"},
    )
