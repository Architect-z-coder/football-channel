"""Build data/history_lens.json from StatsBomb open data (free, via mplsoccer).

Each "lens" is one famous team in one season or tournament, with per-match averages that the
writer can use for a brief comparison ("for context, Leicester in 2015/16 averaged ...").
Run it once, or again after editing LENSES:  python scripts/build_history_lens.py

Data: StatsBomb open data (https://github.com/statsbomb/open-data). Credit "StatsBomb" on screen.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mplsoccer import Sbopen

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "history_lens.json"

# id, team (StatsBomb name), competition_id, season_id, label, what it teaches, tags
LENSES = [
    ("leverkusen_2324", "Bayer Leverkusen", 9, 281, "Leverkusen, Bundesliga 2023/24",
     "Unbeaten league season built on control of the ball and steady chance creation.",
     ["possession", "control", "unbeaten", "late goals", "build-up"]),
    ("leicester_1516", "Leicester City", 2, 27, "Leicester, Premier League 2015/16",
     "Won the league with little of the ball: compact defending and fast, direct attacks.",
     ["counter-attack", "low possession", "direct", "underdog", "compact"]),
    ("arsenal_0304", "Arsenal", 2, 44, "Arsenal, Premier League 2003/04",
     "The Invincibles: a full league season unbeaten, with quick transitions.",
     ["unbeaten", "transitions", "counter-attack", "consistency"]),
    ("barcelona_1011", "Barcelona", 11, 22, "Barcelona, La Liga 2010/11",
     "Positional play: long spells of possession and pressing straight after losing the ball.",
     ["possession", "pressing", "positional play", "dominance"]),
    ("argentina_wc22", "Argentina", 43, 106, "Argentina, World Cup 2022",
     "Tournament winners who lost their first match and kept finding a way.",
     ["tournament", "comeback", "resilience", "penalties"]),
    ("morocco_wc22", "Morocco", 43, 106, "Morocco, World Cup 2022",
     "Semi-finalists with a disciplined low block and fast breaks.",
     ["low block", "defending", "underdog", "counter-attack", "compact"]),
    ("spain_euro24", "Spain", 55, 282, "Spain, Euro 2024",
     "Champions who mixed possession with direct wing play.",
     ["wing play", "pressing", "tournament", "possession"]),
    ("ivorycoast_afcon23", "Côte d'Ivoire", 1267, 107, "Côte d'Ivoire, AFCON 2023",
     "Hosts who nearly went out in the group, then won the tournament.",
     ["tournament", "comeback", "resilience", "late goals"]),
]

FULL_SEASON = {"leverkusen_2324": 34, "leicester_1516": 38, "arsenal_0304": 38, "barcelona_1011": 38}
sb = Sbopen()


def match_stats(match_id: int, team: str) -> dict:
    ev = sb.event(match_id)[0]
    ev = ev[ev["period"] <= 4]  # leave out penalty shoot-outs
    mine, opp = ev[ev["team_name"] == team], ev[ev["team_name"] != team]
    shots_m, shots_o = mine[mine["type_name"] == "Shot"], opp[opp["type_name"] == "Shot"]
    passes_m, passes_o = mine[mine["type_name"] == "Pass"], opp[opp["type_name"] == "Pass"]
    def_actions = mine[((mine["type_name"] == "Duel") & (mine["sub_type_name"] == "Tackle"))
                       | mine["type_name"].isin(["Interception", "Foul Committed", "Dribbled Past"])]
    goals = shots_m[shots_m["outcome_name"] == "Goal"]
    return {
        "xg_for": float(shots_m["shot_statsbomb_xg"].sum()),
        "xg_against": float(shots_o["shot_statsbomb_xg"].sum()),
        "shots_for": len(shots_m), "shots_against": len(shots_o),
        "passes": len(passes_m), "passes_opp": len(passes_o),
        "passes_done": int(passes_m["outcome_name"].isna().sum()),
        "opp_passes_own_60": int((passes_o["x"] < 72).sum()),
        "def_actions_high": int((def_actions["x"] > 48).sum()),
        "goal_shots": [{"x": round(float(r.x), 1), "y": round(float(r.y), 1),
                        "xg": round(float(r.shot_statsbomb_xg), 2), "minute": int(r.minute)}
                       for r in goals.itertuples()],
    }


def build(lens) -> dict:
    lid, team, comp, season, label, idea, tags = lens
    m = sb.match(comp, season)
    m = m[(m["home_team_name"] == team) | (m["away_team_name"] == team)]
    w = d = l = gf = ga = 0
    for r in m.itertuples():
        home = r.home_team_name == team
        f, a = (r.home_score, r.away_score) if home else (r.away_score, r.home_score)
        gf, ga = gf + f, ga + a
        w, d, l = w + (f > a), d + (f == a), l + (f < a)
    with ThreadPoolExecutor(8) as pool:
        stats = list(pool.map(lambda mid: match_stats(mid, team), m["match_id"]))
    n = len(stats)
    tot = {k: sum(s[k] for s in stats) for k in stats[0] if k != "goal_shots"}
    per = lambda k, nd=1: round(tot[k] / n, nd)
    facts = {
        "matches": n, "wins": w, "draws": d, "losses": l,
        "goals_for_pm": round(gf / n, 2), "goals_against_pm": round(ga / n, 2),
        "xg_for_pm": per("xg_for", 2), "xg_against_pm": per("xg_against", 2),
        "shots_for_pm": per("shots_for"), "shots_against_pm": per("shots_against"),
        "possession_pct": round(100 * tot["passes"] / (tot["passes"] + tot["passes_opp"]), 1),
        "pass_completion_pct": round(100 * tot["passes_done"] / tot["passes"], 1),
        "ppda": round(tot["opp_passes_own_60"] / max(tot["def_actions_high"], 1), 1),
    }
    full = FULL_SEASON.get(lid, n)
    if n < full:   # StatsBomb has only some of the matches: no season record, averages only
        for k in ("wins", "draws", "losses"):
            facts.pop(k)
    goals = [g for s in stats for g in s["goal_shots"]]
    print(f"  {label}: {n} matches, {w}W {d}D {l}L", file=sys.stderr)
    return {"id": lid, "team": team, "label": label,
            "coverage": f"all {n} matches" if n >= full else f"{n} of {full} matches", "idea": idea, "tags": tags,
            "source": "StatsBomb open data", "facts": facts, "goal_shots": goals}


def main():
    lenses = [build(x) for x in LENSES]
    OUT.write_text(json.dumps({"note": "Built by scripts/build_history_lens.py from StatsBomb open data. "
                               "Results are after 90 or 120 minutes (shoot-outs count as draws). Possession = share of passes. PPDA = opponent passes in their own 60% "
                               "per tackle, challenge, interception or foul in that area (lower = more pressing).",
                               "lenses": lenses}, indent=1, ensure_ascii=False), encoding="utf-8")
    print("Wrote", OUT, file=sys.stderr)


if __name__ == "__main__":
    main()
