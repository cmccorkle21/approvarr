import logging
import os
import time
from logging.handlers import RotatingFileHandler


def find_project_root(marker="app.py"):
    dirpath = os.path.abspath(os.path.dirname(__file__))
    while True:
        if os.path.exists(os.path.join(dirpath, marker)):
            return dirpath
        parent = os.path.dirname(dirpath)
        if parent == dirpath:
            raise RuntimeError(f"Project root with {marker} not found")
        dirpath = parent


def make_rotating_logger(
    name: str, path: str, max_mb: int = 50, backups: int = 10
) -> logging.Logger:
    """
    Create/get a logger that writes to `path`, rotates at ~max_mb with built-in 1-based suffixes.
    Keeps `backups` rotated files: path.1 .. path.backups
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    os.makedirs(os.path.dirname(path), exist_ok=True)

    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        filename=path,
        mode="a",
        maxBytes=max_mb * 1024 * 1024,
        backupCount=backups,
        encoding="utf-8",
        delay=True,
    )
    formatter = logging.Formatter(
        "%(asctime)s UTC - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


# --- initialize ---
project_root = find_project_root()

# Set timestamps to UTC for all formatters
logging.Formatter.converter = time.gmtime

# API Logger (api.log, rotates to api.log.1, api.log.2, …)
api_log_path = os.path.join(project_root, "api.log")
logger = make_rotating_logger("project_logger", api_log_path, max_mb=50, backups=10)

# DB Logger (db_manager.log, rotates to db_manager.log.1, db_manager.log.2, …)
db_log_path = os.path.join(project_root, "db_manager.log")
db_logger = make_rotating_logger(
    "db_manager_logger", db_log_path, max_mb=50, backups=10
)
