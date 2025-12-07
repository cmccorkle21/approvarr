import datetime
import json
import os
import time

import requests
from flask import Flask, request
from config import load_config

CFG = load_config("./config.yml")

app = Flask(__name__)


LOGFILE = "received_webhooks.log"

# --- Config via env vars ---
QBT_URL = CFG.qbit.url
QBT_USER = CFG.qbit.username
QBT_PASS = CFG.qbit.password

notifier = #magic load config into notifier class

PUSHOVER_TOKEN =
PUSHOVER_USER = 
BASE_PUBLIC_URL = os.getenv(
    "BASE_PUBLIC_URL", "http://192.168.50.54:5001"
)  # change to your real public URL later

# Indexers that should trigger approval flow
NEEDS_APPROVAL_INDEXERS = {
    # swap this for your TL non-freeleech indexer name
    "BitSearch (Prowlarr)",
    # "TL_full (Prowlarr)",
}

session = requests.Session()


# ---------- qBittorrent helpers ----------


def qbt_post(path, data=None):
    url = f"{QBT_URL}{path}"
    resp = session.post(url, data=data or {}, timeout=5)
    print(f"[QBT] POST {url} -> {resp.status_code} {resp.text[:200]!r}")
    resp.raise_for_status()
    return resp


def qbt_login():
    qbt_post("/api/v2/auth/login", {"username": QBT_USER, "password": QBT_PASS})


def qbt_pause(torrent_hash: str):
    qbt_post("/api/v2/torrents/stop", {"hashes": torrent_hash})
    print(f"pausing hash: {torrent_hash}")


def qbt_add_tags(torrent_hash: str, tags):
    qbt_post(
        "/api/v2/torrents/addTags", {"hashes": torrent_hash, "tags": ",".join(tags)}
    )


def qbt_resume(torrent_hash: str):
    qbt_post("/api/v2/torrents/start", {"hashes": torrent_hash})


def qbt_remove_tag(torrent_hash: str, tag: str):
    qbt_post("/api/v2/torrents/removeTags", {"hashes": torrent_hash, "tags": tag})


def qbt_delete(torrent_hash: str, delete_files: bool = True):
    qbt_post(
        "/api/v2/torrents/delete",
        {"hashes": torrent_hash, "deleteFiles": "true" if delete_files else "false"},
    )


# ---------- Pushover helper ----------


def send_pushover_approval(name: str, torrent_hash: str, indexer: str):
    if not (PUSHOVER_TOKEN and PUSHOVER_USER):
        print("Pushover not configured, skipping notification")
        return

    approve_url = f"{BASE_PUBLIC_URL}/approve/{torrent_hash}"
    reject_url = f"{BASE_PUBLIC_URL}/reject/{torrent_hash}"

    msg = (
        f"Indexer: {indexer}\n"
        f"Release: {name}\n\n"
        f"Approve: {approve_url}\n"
        f"Reject:  {reject_url}"
    )

    resp = session.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": PUSHOVER_TOKEN,
            "user": PUSHOVER_USER,
            "title": "Torrent needs approval",
            "message": msg,
            "priority": 0,
        },
        timeout=5,
    )
    resp.raise_for_status()


# ---------- Webhook + approval endpoints ----------


@app.route("/webhook", methods=["POST"])
def webhook():
    ts = datetime.datetime.now().isoformat()
    headers = dict(request.headers)

    try:
        payload = request.get_json(force=True, silent=True)
    except Exception:
        payload = None

    raw_body = request.data.decode("utf-8", errors="replace")

    entry = {
        "timestamp": ts,
        "headers": headers,
        "payload": payload,
        "raw_body": raw_body,
    }

    # Log everything for debugging
    print("\n===== NEW WEBHOOK =====")
    print(json.dumps(entry, indent=2))
    print("=======================\n")

    with open(LOGFILE, "a") as f:
        f.write(json.dumps(entry, indent=2))
        f.write("\n\n")

    # --- Approvarr logic starts here ---
    if not payload:
        return "No JSON payload", 400

    event_type = payload.get("eventType")
    if event_type != "Grab":
        # Ignore non-Grab events for now
        return "Ignored (not Grab)", 200

    release = payload.get("release") or {}
    indexer = release.get("indexer")
    release_title = release.get("releaseTitle") or release.get("title")

    download_id = payload.get(
        "downloadId"
    )  # this should be the torrent hash for qBittorrent

    print(
        f"eventType={event_type}, indexer={indexer}, title={release_title}, downloadId={download_id}"
    )

    # Only trigger approval for certain indexers
    if indexer not in NEEDS_APPROVAL_INDEXERS:
        print("Indexer not in NEEDS_APPROVAL_INDEXERS, letting it go through normally")
        # return "OK (no approval required)", 200

    if not download_id:
        print("No downloadId present; cannot tag by hash")
        return "OK (no downloadId)", 200

    torrent_hash = download_id

    try:
        qbt_login()

        # Small delay in case Sonarr sent torrent and webhook in parallel
        time.sleep(1)

        # Tag & pause
        qbt_add_tags(torrent_hash, ["needs-approval"])
        qbt_pause(torrent_hash)

        send_pushover_approval(release_title or torrent_hash, torrent_hash, indexer)

        print(f"Tagged & paused torrent {torrent_hash} for approval")

    except Exception as e:
        print(f"Error handling approval flow: {e}")

    return "OK", 200


@app.route("/approve/<torrent_hash>", methods=["GET"])
def approve(torrent_hash):
    try:
        qbt_login()
        qbt_remove_tag(torrent_hash, "needs-approval")
        # optionally you can call setCategory here if you want
        qbt_resume(torrent_hash)
        return f"Approved {torrent_hash}\n", 200
    except Exception as e:
        return f"Error approving: {e}\n", 500


@app.route("/reject/<torrent_hash>", methods=["GET"])
def reject(torrent_hash):
    try:
        qbt_login()
        qbt_delete(torrent_hash, delete_files=True)
        return f"Rejected {torrent_hash}\n", 200
    except Exception as e:
        return f"Error rejecting: {e}\n", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
