import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal

import yaml

# -------------------------
# Dataclass Models
# -------------------------

ArrType = Literal["sonarr", "radarr"]


@dataclass
class ArrInstance:
    name: str
    type: ArrType
    url: str
    api_key: str


@dataclass
class QbitConfig:
    url: str
    username: str
    password: str


@dataclass
class NotificationConfig:
    provider: str  # "pushover", "ntfy", "discord"
    pushover: Optional[Dict[str, Any]] = None
    ntfy: Optional[Dict[str, Any]] = None
    discord: Optional[Dict[str, Any]] = None


@dataclass
class BehaviorConfig:
    default_on_error: str = "allow"  # allow | deny | require_approval
    creation_delay_seconds: float = 1.0


@dataclass
class RuleConfig:
    name: str
    apps: List[str]
    indexer_matches: List[str] = field(default_factory=list)
    tags_to_add: List[str] = field(default_factory=list)
    pause_torrent: bool = True
    notify: bool = True
    on_error: Optional[str] = None


@dataclass
class ApprovarrConfig:
    qbit: QbitConfig
    server: Dict[str, Any]
    notifications: NotificationConfig
    behavior: BehaviorConfig
    rules: List[RuleConfig]
    arr: List[ArrInstance]


# -------------------------
# Loader
# -------------------------


def load_config(path: Optional[str] = None) -> ApprovarrConfig:
    """
    Loads YAML into dataclasses with basic validation.
    """

    if path is None:
        # Support env var override
        path = os.getenv("APPROVARR_CONFIG", "config.yml")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file '{path}' not found")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    # ---- qbit ----
    q = raw.get("qbit", {})
    qbit_cfg = QbitConfig(url=q["url"], username=q["username"], password=q["password"])

    # ---- notifications ----
    notif = raw.get("notifications", {})
    notif_cfg = NotificationConfig(
        provider=notif["provider"],
        pushover=notif.get("pushover"),
        ntfy=notif.get("ntfy"),
        discord=notif.get("discord"),
    )

    # ---- behavior ----
    beh = raw.get("behavior", {})
    behavior_cfg = BehaviorConfig(
        default_on_error=beh.get("default_on_error", "allow"),
        creation_delay_seconds=beh.get("creation_delay_seconds", 1.0),
    )

    # ---- rules ----
    rules_raw = raw.get("rules", [])
    rules: List[RuleConfig] = []
    for r in rules_raw:
        rules.append(
            RuleConfig(
                name=r["name"],
                apps=r["apps"],
                indexer_matches=r.get("indexer_matches", []),
                tags_to_add=r.get("tags_to_add", []),
                pause_torrent=r.get("pause_torrent", True),
                notify=r.get("notify", True),
                on_error=r.get("on_error"),
            )
        )

    # ---- server ----
    server_cfg = raw.get("server", {})

    # ---- arr client ----
    arr_raw = raw.get("arr", [])
    arr: List[ArrInstance] = []
    for client in arr_raw:
        arr.append(
            ArrInstance(
                name=client["name"],
                type=client["type"],
                url=client["url"],
                api_key=client["api_key"],
            )
        )

    # ---- final object ----
    config = ApprovarrConfig(
        qbit=qbit_cfg,
        server=server_cfg,
        notifications=notif_cfg,
        behavior=behavior_cfg,
        rules=rules,
        arr=arr,
    )

    validate_config(config)
    return config


# -------------------------
# Basic Validation
# -------------------------

VALID_DEFAULT_BEHAVIORS = {"allow", "deny", "require_approval"}


def validate_config(cfg: ApprovarrConfig):
    """
    Validate certain fields are present and correct.
    This is where you'd catch user mistakes early.
    """

    if cfg.notifications.provider not in ("pushover", "ntfy", "discord"):
        raise ValueError(
            f"Unknown notification provider '{cfg.notifications.provider}'"
        )

    if cfg.behavior.default_on_error not in VALID_DEFAULT_BEHAVIORS:
        raise ValueError(f"default_on_error must be one of {VALID_DEFAULT_BEHAVIORS}")

    for rule in cfg.rules:
        if rule.on_error and rule.on_error not in VALID_DEFAULT_BEHAVIORS:
            raise ValueError(
                f"Rule '{rule.name}' has invalid on_error '{rule.on_error}'"
            )

    # You can add much more depending on how strict you want v1 to be.
    # TODO: warn on no provided arr clients

    return True
