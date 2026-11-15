"""Scout: find the best finished match to analyse and build its data pack.

Uses API-Football (v3). Free plan: 100 requests per day, so every call is counted.
"""
from datetime import date, timedelta

import requests

from .common import DATA_DIR, StopPipeline, log, read_json, secret

BASE = "https://v3.football.api-sports.io"


class ApiFootball:
    def __init__(self, key: str):
        self.key = key
        self.calls = 0

    def get(self, path: str, **params) -> list:
        self.calls += 1
        r = requests.get(f"{BASE}/{path}", headers={"x-apisports-key": self.key},
                         params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            # The API reports plan limits (e.g. season not allowed) here, not as HTTP errors.
            raise StopPipeline(f"API-Football error on {path}: {body['errors']}")
        return body.get("response", [])


def _score_fixture(fx: dict, weight: float, bonus: float) -> float:
    """Simple interest score: competition weight, goals, closeness, priority team."""
    gh = fx["goals"]["home"] or 0
    ga = fx["goals"]["away"] or 0
    goals = gh + ga
    close = 1.0 if abs(gh - ga) <= 1 else 0.0
    return weight + 0.25 * goals + 0.5 * close + bonus


def find_candidates(cfg: dict, api: ApiFootball) -> list[dict]:
    days = cfg["scout"]["look_back_days"]
    frm = (date.today() - timedelta(days=days)).isoformat()
    to = date.today().isoformat()
    used = set(read_json(DATA_DIR / "history.json", {"fixtures": []})["fixtures"])
    priority = {t["name"].lower(): t["bonus"] for t in cfg.get("priority_teams", [])}

    candidates = []
    for comp in cfg["competitions"]:
        fixtures = api.get("fixtures", league=comp["id"], season=comp["season"],
                           **{"from": frm, "to": to, "status": "FT-AET-PEN"})
        for fx in fixtures:
            fid = fx["fixture"]["id"]
            if fid in used:
                continue
            names = {fx["teams"]["home"]["name"].lower(), fx["teams"]["away"]["name"].lower()}
            bonus = max([priority.get(n, 0) for n in names] + [0])
            candidates.append({"fixture": fx, "competition": comp["name"],
                               "score": _score_fixture(fx, comp["weight"], bonus)})

    # Priority national teams (friendlies, qualifiers, tournaments)
    for team in cfg.get("priority_teams", []):
        found = api.get("teams", search=team["name"])
        national = [t for t in found if t["team"].get("national")]
        if not national:
            continue
        fixtures = api.get("fixtures", team=national[0]["team"]["id"],
                           **{"from": frm, "to": to, "status": "FT-AET-PEN"})
        for fx in fixtures:
            if fx["fixture"]["id"] in used or any(
                    c["fixture"]["fixture"]["id"] == fx["fixture"]["id"] for c in candidates):
                continue
            candidates.append({"fixture": fx, "competition": fx["league"]["name"],
                               "score": _score_fixture(fx, 0.8, team["bonus"])})

    candidates.sort(key=lambda c: c["score"], reverse=True)
    log.info("Scout found %d candidate matches (%d API calls)", len(candidates), api.calls)
    return candidates


def build_datapack(candidate: dict, api: ApiFootball) -> dict:
    """Everything the writer is allowed to state. Nothing outside this pack."""
    fx = candidate["fixture"]
    fid = fx["fixture"]["id"]
    stats = api.get("fixtures/statistics", fixture=fid)
    events = api.get("fixtures/events", fixture=fid)
    lineups = api.get("fixtures/lineups", fixture=fid)
    return assemble_pack(fx, candidate["competition"], stats, events, lineups)


def assemble_pack(fx, competition, stats, events, lineups) -> dict:
    home, away = fx["teams"]["home"]["name"], fx["teams"]["away"]["name"]
    facts = []

    def add(fid, label, value):
        if value is None:
            return
        facts.append({"id": fid, "label": label, "value": value})

    add("score_home", f"{home} goals", fx["goals"]["home"])
    add("score_away", f"{away} goals", fx["goals"]["away"])
    add("date", "Match date", fx["fixture"]["date"][:10])
    add("venue", "Venue", (fx["fixture"].get("venue") or {}).get("name"))
    add("round", "Round", fx["league"].get("round"))

    for block in stats:
        team = block["team"]["name"]
        side = "home" if team == home else "away"
        for s in block.get("statistics", []):
            key = s["type"].lower().replace(" ", "_").replace("%", "pct")
            add(f"{side}_{key}", f"{team}: {s['type']}", s["value"])

    for i, ev in enumerate(events):
        minute = ev["time"]["elapsed"]
        extra = ev["time"].get("extra")
        add(f"event_{i}", f"{ev['team']['name']} {ev['type']} ({ev.get('detail')})",
            {"minute": minute, "extra": extra, "player": (ev.get("player") or {}).get("name"),
             "assist": (ev.get("assist") or {}).get("name")})

    for lu in lineups:
        side = "home" if lu["team"]["name"] == home else "away"
        add(f"{side}_formation", f"{lu['team']['name']} formation", lu.get("formation"))
        add(f"{side}_coach", f"{lu['team']['name']} coach", (lu.get("coach") or {}).get("name"))

    return {
        "fixture_id": fx["fixture"]["id"],
        "competition": competition,
        "home": home,
        "away": away,
        "facts": facts,
    }


def scout(cfg: dict) -> dict:
    api = ApiFootball(secret("API_FOOTBALL_KEY", required=True))
    candidates = find_candidates(cfg, api)
    if not candidates or candidates[0]["score"] < cfg["scout"]["min_score"]:
        raise StopPipeline("No match worth a video in the look-back window.")
    pack = build_datapack(candidates[0], api)
    log.info("Chosen: %s vs %s (%s), %d facts, %d API calls total",
             pack["home"], pack["away"], pack["competition"], len(pack["facts"]), api.calls)
    return pack
