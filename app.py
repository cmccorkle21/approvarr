import datetime
import json
import os
import time

import requests
from flask import Flask, request

from config import load_config
from notifications import build_notifier
from download_clients import qbittorrent as qbt

CFG = load_config("./config.yml")

app = Flask(__name__)


LOGFILE = "received_webhooks.log"

# --- Config via env vars ---
QBT_URL = CFG.qbit.url
QBT_USER = CFG.qbit.username
QBT_PASS = CFG.qbit.password


NOTIFIER = build_notifier(CFG)

# Indexers that should trigger approval flow
NEEDS_APPROVAL_INDEXERS = {
    # swap this for your TL non-freeleech indexer name
    "BitSearch (Prowlarr)",
    # "TL_full (Prowlarr)",
}

session = requests.Session()

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

    # TODO: use rules from CFG here
    # Only trigger approval for certain indexers
    if indexer not in NEEDS_APPROVAL_INDEXERS:
        print("Indexer not in NEEDS_APPROVAL_INDEXERS, letting it go through normally")
        # return "OK (no approval required)", 200

    if not download_id:
        print("No downloadId present; cannot tag by hash")
        return "OK (no downloadId)", 200

    torrent_hash = download_id

    try:
        qbt.login()

        # Small delay in case Sonarr sent torrent and webhook in parallel
        time.sleep(1)

        # Tag & pause
        qbt.add_tags(torrent_hash, ["needs-approval"])
        qbt.pause(torrent_hash)

        send_pushover_approval(release_title or torrent_hash, torrent_hash, indexer)

        print(f"Tagged & paused torrent {torrent_hash} for approval")

    except Exception as e:
        print(f"Error handling approval flow: {e}")

    return "OK", 200


@app.route("/approve/<torrent_hash>", methods=["GET"])
def approve(torrent_hash):
    try:
        qbt.login()
        qbt.remove_tag(torrent_hash, "needs-approval")
        # optionally you can call setCategory here if you want
        qbt.resume(torrent_hash)
        return f"Approved {torrent_hash}\n", 200
    except Exception as e:
        return f"Error approving: {e}\n", 500


@app.route("/reject/<torrent_hash>", methods=["GET"])
def reject(torrent_hash):
    try:
        qbt.login()
        qbt.delete(torrent_hash, delete_files=True)
        return f"Rejected {torrent_hash}\n", 200
    except Exception as e:
        return f"Error rejecting: {e}\n", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
