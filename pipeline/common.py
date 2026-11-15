"""Shared helpers: config, paths, secrets, logging."""
import json
import logging
import os
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "out"
ASSETS_DIR = ROOT / "assets"
SAMPLES_DIR = ROOT / "samples"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pipeline")


class StopPipeline(Exception):
    """Raised when a safety check fails. The run stops and you get an alert."""


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    override = os.environ.get("LOOK_BACK_DAYS", "").strip()
    if override.isdigit():  # e.g. to test during an international break
        cfg["scout"]["look_back_days"] = int(override)
    return cfg


def secret(name: str, required: bool = False) -> str | None:
    value = os.environ.get(name, "").strip() or None
    if required and not value:
        raise StopPipeline(f"Missing secret: {name}")
    return value


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
