"""Data source: football-data.org (v4), free tier.

Free tier: 12 competitions, current season, scores (full time + half time), league tables,
team results. No in-match stats (possession, shots) and no lineups. Limit: 10 calls per minute,
so every call waits 6.5 seconds.
"""
import time
from datetime import date, timedelta

import requests

from .common import DATA_DIR, StopPipeline, log, read_json, secret

BASE = "https://api.football-data.org/v4"


class FootballData:
    def __init__(self, key: str):
        self.key = key
        self.calls = 0

    def get(self, path: str, **params) -> dict:
        if self.calls:
            time.sleep(6.5)  # stay under 10 calls per minute
        self.calls += 1
        r = requests.get(f"{BASE}/{path}", headers={"X-Auth-Token": self.key},
                         params=params, timeout=30)
        if r.status_code in (400, 403, 404, 429):
            raise StopPipeline(f"football-data.org {r.status_code} on {path}: {r.text[:300]}")
        r.raise_for_status()
        return r.json()


def _score(m: dict) -> tuple[int, int]:
    ft = m["score"]["fullTime"]
    return ft["home"] or 0, ft["away"] or 0


def _interest(m: dict, weight: float, positions: dict) -> float:
    """Competition weight, goals, closeness, comebacks, big-table clashes, upsets."""
    h, a = _score(m)
    ht = m["score"].get("halfTime") or {}
    hh, ha = ht.get("home") or 0, ht.get("away") or 0
    score = weight + 0.25 * (h + a) + (0.5 if abs(h - a) <= 1 else 0)
    if (hh - ha) * (h - a) < 0:          # leader at half time lost
        score += 1.0
    ph, pa = positions.get(m["homeTeam"]["id"]), positions.get(m["awayTeam"]["id"])
    if ph and pa:
        if ph <= 6 and pa <= 6:          # top-six meeting
            score += 0.8
        if (h < a and ph + 8 <= pa) or (a < h and pa + 8 <= ph):  # upset
            score += 0.8
    return score


def _table_rows(standings: dict) -> dict:
    for block in standings.get("standings", []):
        if block.get("type") == "TOTAL":
            return {row["team"]["id"]: row for row in block["table"]}
    return {}


def find_best(cfg: dict, api: FootballData) -> tuple[dict, dict, str]:
    days = cfg["scout"]["look_back_days"]
    frm, to = (date.today() - timedelta(days=days)).isoformat(), date.today().isoformat()
    used = set(read_json(DATA_DIR / "history.json", {"fixtures": []})["fixtures"])
    best = None
    for comp in cfg["competitions"]:
        code = comp.get("code")
        if not code:
            continue
        data = api.get(f"competitions/{code}/matches", dateFrom=frm, dateTo=to, status="FINISHED")
        matches = [m for m in data.get("matches", []) if m["id"] not in used]
        if not matches:
            continue
        table = {}
        if comp.get("has_table", True):
            try:
                table = _table_rows(api.get(f"competitions/{code}/standings"))
            except StopPipeline as e:
                log.warning("No table for %s: %s", code, e)
        positions = {tid: row["position"] for tid, row in table.items()}
        for m in matches:
            s = _interest(m, comp["weight"], positions)
            if best is None or s > best[0]:
                best = (s, m, comp, table)
    if not best or best[0] < cfg["scout"]["min_score"]:
        raise StopPipeline("No finished match worth a video in the look-back window.")
    log.info("Chosen match %s (interest %.2f) after %d API calls", best[1]["id"], best[0], api.calls)
    return best[1], best[3], best[2]["name"]


def _last5(api: FootballData, team_id: int, before: str) -> list[dict]:
    end = date.fromisoformat(before[:10])
    data = api.get(f"teams/{team_id}/matches", status="FINISHED",
                   dateFrom=(end - timedelta(days=75)).isoformat(), dateTo=end.isoformat())
    ms = [m for m in data.get("matches", []) if m["utcDate"] < before]
    return sorted(ms, key=lambda m: m["utcDate"])[-5:]


def _form(matches: list[dict], team_id: int) -> dict:
    w = d = l = gf = ga = 0
    for m in matches:
        h, a = _score(m)
        mine, theirs = (h, a) if m["homeTeam"]["id"] == team_id else (a, h)
        gf, ga = gf + mine, ga + theirs
        if mine > theirs:
            w += 1
        elif mine == theirs:
            d += 1
        else:
            l += 1
    return {"played": len(matches), "wins": w, "draws": d, "losses": l,
            "goals_for": gf, "goals_against": ga}


def build_pack(match: dict, table: dict, competition: str, api: FootballData) -> dict:
    home, away = match["homeTeam"], match["awayTeam"]
    h, a = _score(match)
    ht = match["score"].get("halfTime") or {}
    facts = []

    def add(fid, label, value):
        if value is not None:
            facts.append({"id": fid, "label": label, "value": value})

    add("score_home", f"{home['name']} goals", h)
    add("score_away", f"{away['name']} goals", a)
    add("ht_home", f"{home['name']} goals at half time", ht.get("home"))
    add("ht_away", f"{away['name']} goals at half time", ht.get("away"))
    add("date", "Match date", match["utcDate"][:10])
    add("matchday", "Matchday", match.get("matchday"))
    add("stage", "Stage", match.get("stage"))

    for side, team in (("home", home), ("away", away)):
        row = table.get(team["id"])
        if row:
            for key in ("position", "points", "playedGames", "won", "draw", "lost",
                        "goalsFor", "goalsAgainst", "goalDifference"):
                snake = "".join("_" + c.lower() if c.isupper() else c for c in key)
                add(f"{side}_{snake}", f"{team['name']} league table (after this round): {key}", row.get(key))
        form = _form(_last5(api, team["id"], match["utcDate"]), team["id"])
        for key, value in form.items():
            add(f"{side}_last5_{key}", f"{team['name']} in the 5 matches before this one: {key}", value)

    return {
        "source": "football-data.org",
        "fixture_id": match["id"],
        "competition": competition,
        "home": home.get("shortName") or home["name"],
        "away": away.get("shortName") or away["name"],
        "facts": facts,
        "note": "No in-match stats (possession, shots, lineups) in this source. "
                "Analyse the result in the context of the table and recent form.",
    }


def scout(cfg: dict) -> dict:
    api = FootballData(secret("FOOTBALL_DATA_KEY", required=True))
    match, table, comp = find_best(cfg, api)
    pack = build_pack(match, table, comp, api)
    log.info("Data pack: %s vs %s (%s), %d facts, %d API calls",
             pack["home"], pack["away"], comp, len(pack["facts"]), api.calls)
    return pack
