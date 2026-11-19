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


def ai_pack(pack: dict) -> dict:
    """The data pack as the AI sees it: the momentum series is replaced by a short summary."""
    out = {k: v for k, v in pack.items() if k != "momentum"}
    if pack.get("player_stats"):   # per-player stats, only the labels that help a diagnosis
        from .fotmob import LINE_STATS
        keep = set(LINE_STATS) | {"Goals", "Assists", "Total shots", "Shots on target", "Expected goals (xG)",
                                  "Expected assists (xA)", "Big chances missed", "Saves", "Goals conceded"}
        out["player_stats"] = [{**{k: p[k] for k in ("player", "team", "line")},
                                "stats": {k: v for k, v in p["stats"].items() if k in keep}}
                               for p in pack["player_stats"]]
    if pack.get("reviews"):   # what the AI needs of each press cut (not the screenshot geometry)
        out["reviews"] = [{k: r.get(k) for k in ("outlet", "author", "date", "headline", "quote", "quote_en",
                                                 "point", "kind")} for r in pack["reviews"]]
    mom = pack.get("momentum")
    if mom:
        def share(lo, hi):
            pts = [p["value"] for p in mom if lo <= p["minute"] < hi]
            return round(100 * sum(1 for v in pts if v > 0) / len(pts)) if pts else None
        out["momentum_available"] = True
        out["momentum_note"] = ("FotMob momentum: percent of minutes in which the HOME team was on top "
                                "(the rest the away team)")
        out["momentum_home_on_top_pct"] = {"first_half": share(0, 46), "second_half": share(46, 200)}
    return out
