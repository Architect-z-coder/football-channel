"""Understat: shot-by-shot data and xG for the big five European leagues (current season included).

Unofficial source: Understat has no public API. This module reads the same data the website
loads. If anything fails, the pipeline carries on without shot data. Credit "Understat" on screen.
"""
import difflib
import json
import re
import unicodedata
from datetime import date, timedelta

import requests

from .common import log

BASE = "https://understat.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/126.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}
LEAGUES = {"PL": "EPL", "PD": "La_liga", "BL1": "Bundesliga", "SA": "Serie_A", "FL1": "Ligue_1"}


def _get(url: str) -> requests.Response:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r


def _page_var(html: str, name: str):
    m = re.search(name + r"\s*=\s*JSON\.parse\('(.+?)'\)", html)
    if not m:
        return None
    return json.loads(m.group(1).encode("utf-8").decode("unicode_escape"))


def league_matches(league: str, season: int) -> list[dict]:
    try:  # newer site: JSON endpoint
        data = _get(f"{BASE}/getLeagueData/{league}/{season}").json()
        dates = data.get("dates") if isinstance(data, dict) else None
        if dates:
            return dates
    except Exception as e:
        log.info("Understat league endpoint not usable (%s); trying the page", e)
    html = _get(f"{BASE}/league/{league}/{season}").text
    return _page_var(html, "datesData") or []


def match_shots(match_id: str) -> dict:
    try:
        data = _get(f"{BASE}/getMatchData/{match_id}").json()
        shots = data.get("shots") if isinstance(data, dict) else None
        if shots:
            return shots
    except Exception as e:
        log.info("Understat match endpoint not usable (%s); trying the page", e)
    html = _get(f"{BASE}/match/{match_id}").text
    return _page_var(html, "shotsData") or {}


def _norm(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    name = re.sub(r"\b(fc|afc|cf|sc|ac|ssc|as|rc|ogc|club|de|calcio|1\.)\b", " ", name)
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", name).split())


def _similar(a: list[str], b: str) -> float:
    return max(difflib.SequenceMatcher(None, _norm(x), _norm(b)).ratio() for x in a if x)


def find_match(fd_match: dict, code: str) -> dict | None:
    league = LEAGUES.get(code)
    if not league:
        return None
    day = date.fromisoformat(fd_match["utcDate"][:10])
    season = day.year if day.month >= 7 else day.year - 1
    home_names = [fd_match["homeTeam"].get(k) or "" for k in ("name", "shortName")]
    away_names = [fd_match["awayTeam"].get(k) or "" for k in ("name", "shortName")]
    best, best_score = None, 0.0
    for m in league_matches(league, season):
        if not m.get("isResult"):
            continue
        mday = date.fromisoformat(m["datetime"][:10])
        if abs((mday - day).days) > 1:
            continue
        s = _similar(home_names, m["h"]["title"]) + _similar(away_names, m["a"]["title"])
        if s > best_score:
            best, best_score = m, s
    if best is None or best_score < 1.1:
        log.warning("No matching Understat match found (best similarity %.2f)", best_score)
        return None
    log.info("Understat match %s: %s v %s (similarity %.2f)", best["id"], best["h"]["title"],
             best["a"]["title"], best_score)
    return best


def enrich(pack: dict, fd_match: dict, code: str) -> dict:
    """Add xG facts and a shot list to the data pack. Never raises."""
    try:
        um = find_match(fd_match, code)
        if not um:
            return pack
        shots = match_shots(um["id"])
    except Exception as e:
        log.warning("Understat unavailable, continuing without shot data: %s", e)
        return pack

    out = []
    for side in ("h", "a"):
        for s in shots.get(side, []):
            out.append({
                "side": "home" if side == "h" else "away",
                "minute": int(s["minute"]),
                "x": float(s["X"]), "y": float(s["Y"]),       # 0-1, attacking towards x = 1
                "xg": round(float(s["xG"]), 2),
                "result": s["result"],                       # Goal, SavedShot, MissedShots, ...
                "player": s["player"],
                "situation": s.get("situation"),
            })
    out.sort(key=lambda s: s["minute"])
    if not out:
        return pack

    facts = pack["facts"]

    def add(fid, label, value):
        facts.append({"id": fid, "label": label, "value": value})

    for side, team in (("home", pack["home"]), ("away", pack["away"])):
        mine = [s for s in out if s["side"] == side]
        xg = round(sum(s["xg"] for s in mine), 2)
        add(f"{side}_xg", f"{team} expected goals (Understat)", xg)
        add(f"{side}_shots", f"{team} shots (Understat)", len(mine))
        add(f"{side}_shots_on_target", f"{team} shots on target incl. goals (Understat)",
            sum(1 for s in mine if s["result"] in ("Goal", "SavedShot")))
        add(f"{side}_big_chances", f"{team} chances worth 0.3 xG or more (Understat)",
            sum(1 for s in mine if s["xg"] >= 0.3))
        if mine:
            best = max(mine, key=lambda s: s["xg"])
            add(f"{side}_best_chance", f"{team} best single chance (Understat)",
                {"player": best["player"], "minute": best["minute"], "xg": best["xg"],
                 "result": best["result"]})
    pack["shots"] = out
    pack["source"] = pack.get("source", "") + " + Understat"
    log.info("Understat: %d shots added (xG %s - %s)", len(out),
             next(f["value"] for f in facts if f["id"] == "home_xg"),
             next(f["value"] for f in facts if f["id"] == "away_xg"))
    return pack
