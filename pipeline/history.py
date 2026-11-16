"""History lens: famous teams' per-match numbers from StatsBomb open data (data/history_lens.json).

The writer may use one lens for a brief comparison that teaches something about the current match.
Build or refresh the file with: python scripts/build_history_lens.py
"""
from .common import DATA_DIR, read_json

FILE = DATA_DIR / "history_lens.json"


def lenses() -> list[dict]:
    return read_json(FILE, {"lenses": []}).get("lenses", [])


def menu() -> list[dict]:
    """What the writer sees: everything except the goal coordinates."""
    return [{k: v for k, v in lens.items() if k != "goal_shots"} for lens in lenses()]


def used_in(script: dict) -> dict:
    """Full lens data for the lenses the script's scenes use (for the video renderer)."""
    wanted = {sc.get("visual", {}).get("lens") for sc in script.get("scenes", [])
              if sc.get("visual", {}).get("type") == "history_lens"}
    return {lens["id"]: lens for lens in lenses() if lens["id"] in wanted}
