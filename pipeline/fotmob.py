"""FotMob: extra post-match detail from the data behind FotMob's public match pages (no key needed).

Adds, when FotMob has them: every shot with xG and position, team stats (possession, big chances,
xG on target, passing...), formations, FotMob player ratings and player of the match, and the
momentum graph. One list request plus one match request per video; credit "FotMob" on screen.
Unofficial: it can change or be blocked at any time, so it never raises and never stops a video.
"""
from datetime import date, timedelta

import requests

from .common import log
from .understat import _similar

BASE = "https://www.fotmob.com/api/data"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
           "Accept": "application/json", "Referer": "https://www.fotmob.com/"}
# football-data.org competition code -> FotMob league id
LEAGUES = {"PL": 47, "PD": 87, "SA": 55, "BL1": 54, "FL1": 53, "CL": 42, "EC": 50, "WC": 77}

# FotMob team-stat title -> (fact id suffix, label). Values come as [home, away].
TEAM_STATS = {
    "Ball possession": ("possession", "possession, percent"),
    "Expected goals (xG)": ("xg", "expected goals (FotMob)"),
    "Expected goals on target (xGOT)": ("xgot", "expected goals on target (FotMob)"),
    "Total shots": ("shots", "shots"),
    "Shots on target": ("shots_on_target", "shots on target"),
    "Big chances": ("big_chances", "big chances"),
    "Big chances missed": ("big_chances_missed", "big chances missed"),
    "Accurate passes": ("accurate_passes", "accurate passes"),
    "Touches in opposition box": ("box_touches", "touches in the opposition box"),
    "Corners": ("corners", "corners"),
    "Fouls committed": ("fouls", "fouls committed"),
    "Duels won": ("duels_won", "duels won"),
    "Tackles": ("tackles", "tackles"),
    "Interceptions": ("interceptions", "interceptions"),
    "Keeper saves": ("saves", "goalkeeper saves"),
}
RESULT = {"Goal": "Goal", "AttemptSaved": "SavedShot", "Miss": "MissedShots", "Post": "ShotOnPost"}


def _get(path: str, params: dict) -> dict:
    r = requests.get(f"{BASE}/{path}", params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def _walk(node):
    """Every dict inside a JSON tree (FotMob moves sections around, so we search instead of indexing)."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def find_match(fd_match: dict, code: str) -> int | None:
    league = LEAGUES.get(code)
    if not league:
        return None
    day = date.fromisoformat(fd_match["utcDate"][:10])
    home = [fd_match["homeTeam"].get(k) or "" for k in ("name", "shortName")]
    away = [fd_match["awayTeam"].get(k) or "" for k in ("name", "shortName")]
    best, best_score = None, 0.0
    for d in (day, day - timedelta(days=1), day + timedelta(days=1)):
        data = _get("matches", {"date": d.strftime("%Y%m%d")})
        for lg in data.get("leagues", []):
            if league not in (lg.get("primaryId"), lg.get("id"), lg.get("parentLeagueId")):
                continue
            for m in lg.get("matches", []):
                h = [m["home"].get("name", ""), m["home"].get("shortName", "")]
                a = [m["away"].get("name", ""), m["away"].get("shortName", "")]
                score = max(_similar(home, x) for x in h if x) + max(_similar(away, x) for x in a if x)
                if score > best_score:
                    best, best_score = m["id"], score
        if best_score >= 1.3:
            break
    return best if best_score >= 1.1 else None


ALIASES = {"turkey": "turkiye", "türkiye": "turkiye", "usa": "united states", "korea republic": "south korea",
           "holland": "netherlands", "czech republic": "czechia", "ivory coast": "cote d'ivoire",
           "côte d'ivoire": "cote d'ivoire", "bosnia": "bosnia and herzegovina"}


def find_by_names(text: str, days: int = 7) -> int | None:
    """'France Turkey' or 'France v Turkey' -> the FotMob id of their most recent finished match."""
    import re
    import unicodedata

    def plain(t):
        t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower().strip()
        return ALIASES.get(t, t)
    words = [w for w in re.split(r"\s+(?:v|vs|-|x)\s+|\s+", text.strip(), flags=re.I) if w]
    best, best_score = None, 0.0
    for back in range(0, days + 1):
        d = date.today() - timedelta(days=back)
        try:
            data = _get("matches", {"date": d.strftime("%Y%m%d")})
        except Exception:
            continue
        for lg in data.get("leagues", []):
            for m in lg.get("matches", []):
                st = m.get("status") or {}
                if not st.get("finished"):
                    continue
                names = [plain(m["home"].get("name")), plain(m["away"].get("name"))]
                # every word of the request must belong to one of the two team names
                hits = sum(1 for w in words if any(plain(w) in n or n in plain(w) for n in names))
                both = all(any(plain(w) in n or n in plain(w) for w in words) for n in names)
                exact = sum(1 for n in names if any(plain(w) == n for w in words))
                score = hits / max(1, len(words)) + (1 if both else 0) + 0.25 * exact
                if score > best_score:
                    best, best_score = m["id"], score
        if best_score >= 2:
            break
    if best_score >= 2:
        log.info("FotMob: '%s' is match %s", text, best)
        return int(best)
    return None


def _num(v):
    """'410 (85%)' -> (410, 85); '2.02' -> 2.02; 57 -> 57."""
    if isinstance(v, (int, float)):
        return v, None
    s = str(v).strip()
    pct = None
    if "(" in s and "%" in s:
        pct = s[s.index("(") + 1:s.index("%")].strip()
        s = s[:s.index("(")].strip()
    try:
        n = float(s)
        n = int(n) if n.is_integer() else round(n, 2)
    except ValueError:
        return None, None
    try:
        pct = int(float(pct)) if pct is not None else None
    except ValueError:
        pct = None
    return n, pct


def team_stats(data: dict) -> dict:
    out = {}
    for d in _walk(data.get("content", {}).get("stats", data.get("content", {}))):
        title, vals = d.get("title"), d.get("stats")
        if title in TEAM_STATS and isinstance(vals, list) and len(vals) == 2 and title not in out:
            out[title] = vals
    return out


def shots(data: dict, home_id: int) -> list[dict]:
    raw = []
    for d in _walk(data.get("content", {})):
        if isinstance(d.get("shots"), list) and d["shots"] and "expectedGoals" in d["shots"][0]:
            raw = d["shots"]
            break
    out = []
    for s in raw:
        if s.get("isOwnGoal"):
            continue
        result = "BlockedShot" if s.get("isBlocked") and s.get("eventType") != "Goal" else \
            RESULT.get(s.get("eventType"), s.get("eventType"))
        out.append({
            "side": "home" if s.get("teamId") == home_id else "away",
            "minute": int(s.get("min") or 0),
            "x": round(float(s["x"]) / 105, 4), "y": round(float(s["y"]) / 68, 4),  # 0-1, attacking x = 1
            "xg": round(float(s.get("expectedGoals") or 0), 2),
            "xgot": round(float(s["expectedGoalsOnTarget"]), 2) if s.get("expectedGoalsOnTarget") is not None else None,
            "result": result, "player": s.get("playerName"), "situation": s.get("situation"),
            "body_part": s.get("shotType"),
            "goal_y": round(float(s["goalCrossedY"]) / 68, 3) if s.get("goalCrossedY") is not None else None,
            "goal_z": round(float(s["goalCrossedZ"]), 2) if s.get("goalCrossedZ") is not None else None,
        })
    out.sort(key=lambda s: s["minute"])
    return out


def momentum(data: dict) -> list[dict] | None:
    for d in _walk(data.get("content", {})):
        m = d.get("momentum")
        if isinstance(m, dict):
            pts = (m.get("main") or {}).get("data") or m.get("data")
            if isinstance(pts, list) and pts and "value" in pts[0]:
                # FotMob: positive = home on top, negative = away on top
                return [{"minute": float(p["minute"]), "value": float(p["value"])} for p in pts]
    return None


def enrich(pack: dict, fd_match: dict, code: str) -> dict:
    """Add FotMob detail to the data pack. Never raises."""
    try:
        mid = find_match(fd_match, code)
        if not mid:
            log.info("FotMob: match not found.")
            return pack
        data = _get("matchDetails", {"matchId": mid})
    except Exception as e:
        log.warning("FotMob unavailable, continuing without it: %s", e)
        return pack
    try:
        return _apply(pack, data, mid)
    except Exception as e:  # page format changed: keep what we had
        log.warning("FotMob data could not be read (%s); continuing without it.", e)
        return pack


LINES = {0: "goalkeeper", 1: "defenders", 2: "midfielders", 3: "forwards"}
# stats worth totalling by line (FotMob labels; whatever exists in the reply is used)
LINE_STATS = ["Touches", "Touches in opposition box", "Recoveries", "Tackles won", "Duels won", "Duels lost",
              "Interceptions", "Clearances", "Blocks", "Aerial duels won", "Ground duels won",
              "Passes into final third", "Accurate passes", "Successful dribbles", "Dispossessed",
              "Defensive actions", "Chances created", "Crosses", "Accurate long balls", "Was fouled", "Fouls committed",
              "Line breaking passes"]
KEEPER_STATS = ["Saves", "Saves inside box", "Goals prevented", "xGOT faced", "Diving save", "High claim",
                "Acted as sweeper", "Punches"]


def _stat_value(st: dict):
    """FotMob stat -> (value, total or None). Handles plain numbers and 'x/y' style stats."""
    v = (st or {}).get("stat") or {}
    val, tot = v.get("value"), v.get("total")
    try:
        val = float(val)
        val = int(val) if val.is_integer() else round(val, 2)
    except (TypeError, ValueError):
        return None, None
    try:
        tot = int(float(tot)) if tot is not None else None
    except (TypeError, ValueError):
        tot = None
    return val, tot


def _player_stats(pack: dict, data: dict, home_id, teams, add) -> None:
    """Every player's FotMob match stats (no positions: FotMob has none), and totals by line."""
    ps = (data.get("content") or {}).get("playerStats") or {}
    players, labels = [], set()
    for pid, p in ps.items():
        if not isinstance(p, dict):
            continue
        side = "home" if p.get("teamId") == home_id else "away"
        row = {"player": p.get("name"), "team": pack[side], "side": side,
               "line": LINES.get(p.get("usualPosition", p.get("positionId"))), "stats": {}}
        for grp in p.get("stats") or []:
            for label, st in ((grp or {}).get("stats") or {}).items():
                val, tot = _stat_value(st)
                if val is None or label in ("FotMob rating",):
                    continue
                row["stats"][label] = f"{val}/{tot}" if tot else val
                labels.add(label)
        if row["player"] and row["stats"]:
            players.append(row)
    if not players:
        return
    pack["player_stats"] = players
    log.info("FotMob player stats: %d players, labels: %s", len(players), ", ".join(sorted(labels)))
    for side, team in teams:
        for p in players:
            if p["side"] == side and p["line"] == "goalkeeper":
                for label in KEEPER_STATS:
                    if label in p["stats"]:
                        add(f"{side}_keeper_{label.lower().replace(' ', '_')}",
                            f"{team} goalkeeper {p['player']}: {label} (FotMob)", p["stats"][label])
        for line in ("defenders", "midfielders", "forwards"):
            group = [p for p in players if p["side"] == side and p["line"] == line]
            if not group:
                continue
            for label in LINE_STATS:
                vals = [p["stats"][label] for p in group if label in p["stats"]]
                nums = [v if isinstance(v, (int, float)) else float(str(v).split("/")[0]) for v in vals]
                if nums:
                    key = label.lower().replace(" ", "_")
                    total = sum(nums)
                    add(f"{side}_{line}_{key}", f"{team} {line} ({len(group)} players): {label}, total (FotMob)",
                        int(total) if float(total).is_integer() else round(total, 2))


def _apply(pack: dict, data: dict, mid: int) -> dict:
    facts = pack["facts"]
    have = {f["id"] for f in facts}

    def add(fid, label, value):
        if fid not in have and value is not None:
            facts.append({"id": fid, "label": label, "value": value})
            have.add(fid)

    general = data.get("general", {})
    home_id = (general.get("homeTeam") or {}).get("id")
    teams = (("home", pack["home"]), ("away", pack["away"]))

    for title, vals in team_stats(data).items():
        key, label = TEAM_STATS[title]
        for (side, team), raw in zip(teams, vals):
            n, pct = _num(raw)
            add(f"{side}_{key}", f"{team} {label} (FotMob)", n)
            if pct is not None:
                add(f"{side}_{key}_pct", f"{team} {label}, percent (FotMob)", pct)

    _player_stats(pack, data, home_id, teams, add)

    lineup = data.get("content", {}).get("lineup") or {}
    for side, team in teams:
        t = lineup.get(f"{side}Team") or {}
        add(f"{side}_formation", f"{team} formation", t.get("formation"))
        rated = [p for p in t.get("starters", []) + t.get("subs", [])
                 if (p.get("performance") or {}).get("rating")]
        if rated:
            top = max(rated, key=lambda p: p["performance"]["rating"])
            add(f"{side}_top_rated", f"{team} highest FotMob player rating",
                {"player": top.get("name"), "rating": top["performance"]["rating"]})
    ratings = []
    for side, team in teams:
        t = lineup.get(f"{side}Team") or {}
        for p in t.get("starters", []) + t.get("subs", []):
            perf = p.get("performance") or {}
            if perf.get("rating"):
                subs = perf.get("substitutionEvents") or []
                ratings.append({"side": side, "team": team, "player": p.get("name"),
                                "rating": round(float(perf["rating"]), 1),
                                "started": p in t.get("starters", []),
                                "subbed_off": any(e.get("type") == "subOut" for e in subs)})
    # substitutions with their minute (who came on, who went off): for the momentum graph
    changes = []
    for side, team in teams:
        t = lineup.get(f"{side}Team") or {}
        for p in t.get("starters", []) + t.get("subs", []):
            for e in (p.get("performance") or {}).get("substitutionEvents") or []:
                try:
                    minute = int(str(e.get("time", "")).split("+")[0].strip("'"))
                except ValueError:
                    continue
                changes.append({"side": side, "team": team, "minute": minute, "player": p.get("name"),
                                "type": "on" if e.get("type") == "subIn" else "off"})
    if changes:
        pairs = {}
        for c in changes:
            pairs.setdefault((c["side"], c["minute"]), {"side": c["side"], "team": c["team"], "minute": c["minute"],
                                                         "on": [], "off": []})[c["type"]].append(c["player"])
        pack["subs"] = sorted(pairs.values(), key=lambda x: x["minute"])
        for i, s_ in enumerate(pack["subs"], 1):
            add(f"sub_{i}", f"Substitution ({s_['team']}, minute {s_['minute']})",
                {"minute": s_["minute"], "team": s_["team"], "on": ", ".join(s_["on"]), "off": ", ".join(s_["off"])})
    if ratings:
        pack["ratings"] = sorted(ratings, key=lambda r: -r["rating"])
        starters = [r for r in ratings if r["started"]]
        for i, r in enumerate(sorted(starters, key=lambda r: -r["rating"])[:3], 1):
            add(f"best_player_{i}", "Highest FotMob rating among starters", {k: r[k] for k in ("player", "team", "rating")})
        for i, r in enumerate(sorted(starters, key=lambda r: r["rating"])[:3], 1):
            add(f"worst_player_{i}", "Lowest FotMob rating among starters",
                {k: r[k] for k in ("player", "team", "rating", "subbed_off")})
    # lineups, coaches and confirmed absentees (injured / suspended), with market values
    lu = {}
    for side, team in teams:
        t = lineup.get(f"{side}Team") or {}
        coach = t.get("coach") or {}
        coach = coach[0] if isinstance(coach, list) and coach else coach
        if isinstance(coach, dict) and coach.get("name"):
            add(f"{side}_coach", f"{team} head coach", coach["name"])
        starters = []
        for p in t.get("starters", []):
            lay = p.get("horizontalLayout") or {}
            starters.append({"player": p.get("name"), "shirt": p.get("shirtNumber"),
                             "x": lay.get("x"), "y": lay.get("y"),
                             "rating": (p.get("performance") or {}).get("rating"),
                             "value_m_eur": round((p.get("marketValue") or 0) / 1e6) or None,
                             "value_eur": p.get("marketValue")})
        missing = []
        for p in t.get("unavailable", []) or []:
            u = p.get("unavailability") or {}
            missing.append({"player": p.get("name"),
                            "reason": u.get("type") or "unavailable",       # injury / suspension ...
                            "value_eur": p.get("marketValue")})
        missing.sort(key=lambda m: -(m["value_eur"] or 0))
        lu[side] = {"team": team, "formation": t.get("formation"), "starters": starters, "missing": missing}
        if starters:
            add(f"{side}_starting_xi", f"{team} starting eleven",
                ", ".join(f"{x['player']}" for x in starters))
        for i, m in enumerate(missing[:4], 1):
            add(f"{side}_absent_{i}", f"{team} player missing this match (FotMob; value = market value, EUR)",
                {"player": m["player"], "reason": m["reason"],
                 "market_value_m_eur": round((m["value_eur"] or 0) / 1e6) or None})
        if starters and any(x["value_eur"] for x in starters):
            add(f"{side}_xi_market_value_m_eur", f"{team} starting eleven total market value, million EUR",
                round(sum(x["value_eur"] or 0 for x in starters) / 1e6))
    form = (data.get("content", {}).get("matchFacts") or {}).get("teamForm") or []
    for (side, team), games in zip(teams, form if len(form) == 2 else []):
        res = [g.get("resultString") for g in games if g.get("resultString")]
        if res:
            add(f"{side}_form_last{len(res)}", f"{team} results in the previous {len(res)} matches, oldest first",
                " ".join(res))
            add(f"{side}_form_record", f"{team} record in those {len(res)} matches",
                {"won": res.count("W"), "drawn": res.count("D"), "lost": res.count("L")})
            add(f"{side}_form_games", f"{team} previous {len(res)} matches, oldest first",
                [{"date": (g.get("date") or {}).get("utcTime", "")[:10],
                  "match": f"{g['tooltipText']['homeTeam']} {g['tooltipText']['homeScore']}-"
                           f"{g['tooltipText']['awayScore']} {g['tooltipText']['awayTeam']}"}
                 for g in games if g.get("tooltipText")])
    if any(v["starters"] for v in lu.values()):
        pack["lineups"] = lu
    info = (data.get("content", {}).get("matchFacts") or {}).get("infoBox") or {}
    stadium = info.get("Stadium") or {}
    if stadium.get("name"):
        add("stadium", "Stadium", f"{stadium['name']}, {stadium.get('city', '')}".strip(", "))
    if info.get("Attendance"):
        add("attendance", "Attendance", info["Attendance"])
    potm = (data.get("content", {}).get("matchFacts") or {}).get("playerOfTheMatch") or {}
    if potm.get("name"):
        add("player_of_the_match", "Player of the match (FotMob)",
            {"player": potm["name"].get("fullName"), "team": potm.get("teamName"),
             "rating": (potm.get("rating") or {}).get("num")})

    added_shots = False
    if not pack.get("shots"):
        sh = shots(data, home_id)
        if sh:
            pack["shots"] = sh
            added_shots = True
            for side, team in teams:
                mine = [s for s in sh if s["side"] == side]
                add(f"{side}_xg", f"{team} expected goals (FotMob)", round(sum(s["xg"] for s in mine), 2))
                if mine:
                    best = max(mine, key=lambda s: s["xg"])
                    add(f"{side}_best_chance", f"{team} best single chance (FotMob)",
                        {"player": best["player"], "minute": best["minute"], "xg": best["xg"],
                         "result": best["result"]})
    mom = momentum(data)
    if mom:
        pack["momentum"] = mom

    pack["fotmob_id"] = mid
    try:
        _focus_form(pack, data, add)
    except Exception as e:  # never stop a video for this extra
        log.warning("Player form (last matches) skipped: %s", e)
    pack["source"] = pack.get("source", "") + " + FotMob"
    log.info("FotMob: match %s, %d facts, %s shots, momentum %s", mid, len(facts),
             len(pack.get("shots", [])) if added_shots else "no new", "yes" if mom else "no")
    return pack


def build_pack(mid: int) -> dict:
    """A full data pack from FotMob alone, for matches our main source does not cover
    (Nations League, internationals, cups, AFCON...). Pick it with "fotmob:<match id>"."""
    data = _get("matchDetails", {"matchId": mid})
    g, header = data.get("general", {}), data.get("header", {})
    teams = header.get("teams") or []
    if len(teams) != 2 or not (header.get("status") or {}).get("finished"):
        from .common import StopPipeline
        raise StopPipeline(f"FotMob match {mid} is not a finished match.")
    home, away = teams[0]["name"], teams[1]["name"]
    facts = []

    def add(fid, label, value):
        if value is not None:
            facts.append({"id": fid, "label": label, "value": value})

    add("score_home", f"{home} goals", teams[0].get("score"))
    add("score_away", f"{away} goals", teams[1].get("score"))
    events = ((data.get("content", {}).get("matchFacts") or {}).get("events") or {}).get("events") or []
    ht = next((e for e in events if e.get("type") == "Half" and e.get("halfStrShort") == "HT"), None)
    if ht:
        add("ht_home", f"{home} goals at half time", ht.get("homeScore"))
        add("ht_away", f"{away} goals at half time", ht.get("awayScore"))
    add("date", "Match date", (g.get("matchTimeUTCDate") or "")[:10] or None)
    add("competition_round", "Round", g.get("leagueRoundName"))
    n = 0
    for e in events:
        if e.get("type") == "Goal":
            n += 1
            minute = e.get("time")
            extra = e.get("overloadTime")
            add(f"goal_{n}", f"Goal {n}", {
                "team": home if e.get("isHome") else away, "player": (e.get("player") or {}).get("name"),
                "minute": minute, "added_time": extra or None,
                "type": "own goal" if e.get("ownGoal") else (e.get("goalDescription") or "open play"),
                "assist": (e.get("assistInput") or None), "score_after": e.get("newScore")})
        elif e.get("type") == "Card" and e.get("card") in ("Red", "YellowRed"):
            add(f"red_card_{e.get('time')}", "Red card", {
                "team": home if e.get("isHome") else away,
                "player": (e.get("player") or {}).get("name"), "minute": e.get("time")})
    pack = {
        "source": "FotMob",
        "fixture_id": f"fotmob-{mid}",
        "competition": g.get("parentLeagueName") or g.get("leagueName") or "",
        "home": home, "away": away, "facts": facts,
        "note": "Data from FotMob only: no league table or recent-form facts for this match.",
    }
    pack = _apply(pack, data, mid)
    pack["source"] = "FotMob"
    return pack


# Work-rate numbers for chosen players (config.yaml fotmob.focus_players) across their recent matches.
FORM_STATS = ["Minutes played", "Distance covered", "Running", "Sprinting", "Number of sprints", "Top speed",
              "Touches", "Touches in opposition box", "Total shots", "Expected goals (xG)", "Goals",
              "Duels won", "Duels lost", "Recoveries", "Tackles won", "Interceptions", "Clearances", "Blocks",
              "Dribbled past", "Aerial duels won", "Ground duels won", "Accurate passes", "Accurate long balls",
              "Passes into final third", "Line breaking passes", "Dispossessed", "Fouls committed", "FotMob rating"]


def _plain(t: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower().strip()


def _find_player(data: dict, name: str):
    for p in ((data.get("content") or {}).get("playerStats") or {}).values():
        if isinstance(p, dict) and _plain(name) in _plain(p.get("name")):
            row = {}
            for grp in p.get("stats") or []:
                for label, st in ((grp or {}).get("stats") or {}).items():
                    if label in FORM_STATS:
                        val, tot = _stat_value(st)
                        if val is not None:
                            row[label] = f"{val}/{tot}" if tot else val
            return p, row
    return None, None


def _form_match_ids(game: dict):
    import re
    for k in ("id", "matchId"):
        if str(game.get(k) or "").isdigit():
            return int(game[k])
    m = re.search(r"(\d{6,})", str(game.get("linkToMatch") or game.get("pageUrl") or ""))
    return int(m.group(1)) if m else None


def _focus_form(pack: dict, data: dict, add) -> None:
    from .common import load_config
    names = load_config().get("focus_players") or []
    form = (data.get("content", {}).get("matchFacts") or {}).get("teamForm") or []
    if not names or len(form) != 2:
        return
    general = data.get("general", {})
    home_id = (general.get("homeTeam") or {}).get("id")
    if form[0] and form[0][0]:
        log.info("teamForm game keys: %s", sorted(form[0][0].keys()))
    for name in names:
        p, today = _find_player(data, name)
        if not p:
            continue
        side = 0 if p.get("teamId") == home_id else 1
        games = []
        for g in form[side][-5:]:
            mid = _form_match_ids(g)
            if not mid:
                continue
            try:
                d = _get("matchDetails", {"matchId": mid})
            except Exception as e:
                log.warning("Form match %s not read: %s", mid, e)
                continue
            _, row = _find_player(d, name)
            tt = g.get("tooltipText") or {}
            games.append({"date": (d.get("general", {}).get("matchTimeUTCDate") or "")[:10],
                          "match": f"{tt.get('homeTeam')} {tt.get('homeScore')}-{tt.get('awayScore')} {tt.get('awayTeam')}",
                          "played": bool(row), "stats": row or {}})
        games.append({"date": (general.get("matchTimeUTCDate") or "")[:10], "match": "this match",
                      "played": True, "stats": today})
        full = p.get("name") or name
        pack.setdefault("player_form", []).append({"player": full, "games": games})
        add(f"form_{_plain(full).replace(' ', '_')}",
            f"{full}: work rate and output, previous {len(games) - 1} matches then this one, oldest first "
            f"(FotMob; distance, running and sprinting in metres, top speed in km/h)", games)
        import json as _json
        log.info("Player form: %s %s", full, _json.dumps(games, ensure_ascii=False))
