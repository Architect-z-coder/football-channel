"""Data source: football-data.org (v4), free tier.

Free tier: 12 competitions, current season, scores (full time + half time), league tables,
team results. No in-match stats (possession, shots) and no lineups. Limit: 10 calls per minute,
so every call waits 6.5 seconds.
"""
import re
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


def _table(api: FootballData, code: str) -> dict:
    try:
        return _table_rows(api.get(f"competitions/{code}/standings"))
    except StopPipeline as e:
        log.warning("No table for %s: %s", code, e)
        return {}


def find_candidates(cfg: dict, api: FootballData) -> list[dict]:
    """All finished matches in the look-back window, most interesting first."""
    days = cfg["scout"]["look_back_days"]
    frm, to = (date.today() - timedelta(days=days)).isoformat(), date.today().isoformat()
    used = set(read_json(DATA_DIR / "history.json", {"fixtures": []})["fixtures"])
    out = []
    for comp in cfg["competitions"]:
        code = comp.get("code")
        if not code:
            continue
        data = api.get(f"competitions/{code}/matches", dateFrom=frm, dateTo=to, status="FINISHED")
        matches = data.get("matches", [])
        if not matches:
            continue
        table = _table(api, code)
        positions = {tid: row["position"] for tid, row in table.items()}
        for m in matches:
            out.append({"interest": _interest(m, comp["weight"], positions), "match": m,
                        "competition": comp["name"], "table": table, "done": m["id"] in used})
    out.sort(key=lambda c: c["interest"], reverse=True)
    log.info("%d finished matches found (%d API calls)", len(out), api.calls)
    return out


def describe(c: dict) -> str:
    m = c["match"]
    h, a = _score(m)
    flag = "  (already covered)" if c["done"] else ""
    return (f"{m['id']}  {m['utcDate'][:10]}  {c['competition']}: "
            f"{m['homeTeam'].get('shortName') or m['homeTeam']['name']} {h}-{a} "
            f"{m['awayTeam'].get('shortName') or m['awayTeam']['name']}  "
            f"(interest {c['interest']:.1f}){flag}")


def _names(team: dict) -> list[str]:
    return [str(team.get(k) or "").lower() for k in ("name", "shortName", "tla")]


def _matches_pick(m: dict, words: list[str]) -> bool:
    names = _names(m["homeTeam"]) + _names(m["awayTeam"])
    return all(any(w in n for n in names) for w in words)


def choose(cfg: dict, api: FootballData, pick: str | None) -> tuple[dict, dict, str]:
    """Return (match, table, competition name) for the match you picked.

    pick = a match number from the list ("575383") or team names ("Arsenal Chelsea").
    Without a pick: only picks by itself if config scout.auto_pick is true.
    """
    pick = (pick or "").strip()
    if pick.isdigit():
        m = api.get(f"matches/{pick}")
        m = m.get("match", m)
        if m.get("status") != "FINISHED":
            raise StopPipeline(f"Match {pick} has not finished yet (status: {m.get('status')}).")
        comp = m.get("competition") or {}
        table = _table(api, comp["code"]) if comp.get("code") else {}
        log.info("You picked match %s", pick)
        return m, table, comp.get("name", "")

    candidates = find_candidates(cfg, api)
    if pick:
        words = [w for w in re.split(r"[\s,]+|\bvs?\b|-", pick.lower()) if w and w != "v"]
        hits = [c for c in candidates if _matches_pick(c["match"], words)]
        if not hits:
            raise StopPipeline(
                f"No finished match matching '{pick}' in the last {cfg['scout']['look_back_days']} days. "
                "Run the 'list' mode to see the choices, or use a longer look-back.")
        c = hits[0]
        log.info("You picked: %s", describe(c))
        return c["match"], c["table"], c["competition"]

    if not cfg["scout"].get("auto_pick", False):
        raise StopPipeline("No match chosen. Add one to data/queue.txt, or run the workflow "
                           "with a match. Run the 'list' mode to see this week's choices.")
    fresh = [c for c in candidates if not c["done"]]
    if not fresh or fresh[0]["interest"] < cfg["scout"]["min_score"]:
        raise StopPipeline("No finished match worth a video in the look-back window.")
    log.info("Auto-picked: %s", describe(fresh[0]))
    return fresh[0]["match"], fresh[0]["table"], fresh[0]["competition"]


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


def list_matches(cfg: dict) -> tuple[list[str], list[dict]]:
    """Text lines for the log/Telegram, and the same matches as data for the dashboard."""
    api = FootballData(secret("FOOTBALL_DATA_KEY", required=True))
    cands = find_candidates(cfg, api)
    rows = []
    for c in cands:
        m = c["match"]
        h, a = _score(m)
        ht = (m.get("score") or {}).get("halfTime") or {}
        rows.append({"id": m["id"], "date": m["utcDate"][:10], "competition": c["competition"],
                     "home": m["homeTeam"].get("shortName") or m["homeTeam"]["name"],
                     "away": m["awayTeam"].get("shortName") or m["awayTeam"]["name"],
                     "score": f"{h}-{a}", "half_time": f"{ht.get('home')}-{ht.get('away')}",
                     "interest": round(c["interest"], 1), "done": c["done"]})
    return [describe(c) for c in cands], rows


def scout(cfg: dict, pick: str | None = None) -> dict:
    api = FootballData(secret("FOOTBALL_DATA_KEY", required=True))
    match, table, comp = choose(cfg, api, pick)
    pack = build_pack(match, table, comp, api)
    code = (match.get("competition") or {}).get("code") or next(
        (c.get("code") for c in cfg["competitions"] if c["name"] == comp), None)
    if cfg.get("fotmob", True) and code:          # shots, team stats, ratings, momentum
        from .fotmob import enrich as fotmob_enrich
        pack = fotmob_enrich(pack, match, code)
    if cfg.get("understat", True) and code and not pack.get("shots"):   # backup shot source
        from .understat import enrich
        pack = enrich(pack, match, code)
    log.info("Data pack: %s vs %s (%s), %d facts, %d API calls",
             pack["home"], pack["away"], comp, len(pack["facts"]), api.calls)
    return pack
