import datetime
import json
import time

from flask import Flask, request

from config import load_config
from notifications import build_notifier
from qbittorrent_client import build_qbit_client

app = Flask(__name__)

LOGFILE = "received_webhooks.log"
CFG = load_config("./config.yml")
notifier = build_notifier(CFG)
qbt = build_qbit_client(CFG)
rules = CFG.rules

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
    app = payload.get("instanceName")
    indexer = release.get("indexer")
    release_title = release.get("releaseTitle") or release.get("title")
    gib_size = int(release.get("size")) / (1024 ** 3)
    release_size = f"{gib_size:.2f} GiB"

    download_id = payload.get("downloadId")

    print(
        f"eventType={event_type}, indexer={indexer}, title={release_title}, downloadId={download_id}"
    )

    if not indexer:
        return "no indexer", 400

    # decide if needs approval or not
    needs_approval = False
    needs_pause = False
    tags = []  # could be from multiple rules, though that would be weird
    for rule in rules:
        if (
            rule.notify
            and app.lower() in [app.lower() for app in rule.apps]
            and indexer
            in rule.indexer_matches  # TODO: use matcher fn here for either direct match or regex
        ):
            # these only apply if the rules matches!
            needs_approval = True
            if rule.pause_torrent:  # as soon as one rule wants pause, we do it.
                needs_pause = True
            for tag in rule.tags_to_add:
                tags.append(tag)

    if not download_id:
        print("No downloadId present; cannot tag by hash")
        return "OK (no downloadId)", 200

    torrent_hash = download_id

    try:
        qbt.login()

        # Small delay in case Sonarr sent torrent and webhook in parallel
        time.sleep(1)

        # Tag & pause
        if tags:
            qbt.add_tags(torrent_hash, tags)
            print("tags added")
        if needs_pause:
            qbt.pause(torrent_hash)
            print("torrent paused")

        if notifier and needs_approval and release_title:
            notifier.send_approval(
                name=release_title, size=release_size, torrent_hash=torrent_hash, indexer=indexer
            )

    except Exception as e:
        print(f"Error handling approval flow: {e}")

    return "OK", 200


@app.route("/approve/<torrent_hash>", methods=["GET"])
def approve(torrent_hash):
    try:
        qbt.login()
        qbt.remove_tag(torrent_hash, "needs-approval")
        # optionally you can call setCategory here if you want
        qbt.add_tags(torrent_hash, ["approved"])
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
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)
