"""Diagnosis: WHY the result happened, from the shot list. Adds plain facts (diag_*) to the pack:

- chance quality: shots, xG, xG per shot, big chances (xG >= 0.3), share of shots from inside the box,
  open play vs set-piece xG;
- finishing: xG vs xGOT (xG on target: where the shot went in the goal; above xG = well placed,
  below = poorly placed or off target);
- goalkeeping: xGOT faced vs goals conceded (goals prevented by the keeper);
- luck: the match's chances replayed 20,000 times (each shot scores with probability = its xG):
  how often each side wins, draws, loses with these exact chances.
Everything is computed here, so every number in the narration can be checked. Never raises.
"""
import random

from .common import log

SET_PIECES = ("SetPiece", "FromCorner", "FreeKick", "ThrowInSetPiece", "Penalty", "DirectFreekick")
BOX_X, BOX_Y0, BOX_Y1 = 1 - 16.5 / 105, (68 - 40.32) / 2 / 68, 1 - (68 - 40.32) / 2 / 68


def _side(shots, side):
    s = [x for x in shots if x["side"] == side]
    xg = sum(x["xg"] for x in s)
    on = [x for x in s if x["result"] in ("Goal", "SavedShot")]
    xgot = sum((x.get("xgot") or 0) for x in on)
    goals = sum(1 for x in s if x["result"] == "Goal")
    inbox = sum(1 for x in s if x["x"] >= BOX_X and BOX_Y0 <= x["y"] <= BOX_Y1)
    sp = sum(x["xg"] for x in s if x.get("situation") in SET_PIECES)
    return {"shots": len(s), "xg": round(xg, 2), "xg_per_shot": round(xg / len(s), 2) if s else 0,
            "big": sum(1 for x in s if x["xg"] >= 0.3), "big_scored": sum(1 for x in s if x["xg"] >= 0.3 and x["result"] == "Goal"),
            "inbox_pct": round(100 * inbox / len(s)) if s else 0, "on_target": len(on),
            "xgot": round(xgot, 2) if any(x.get("xgot") is not None for x in on) else None,
            "goals": goals, "setpiece_xg": round(sp, 2), "openplay_xg": round(xg - sp, 2)}


def _simulate(shots, og_home=0, og_away=0, n=20000, seed=7):
    rnd = random.Random(seed)
    h = [x["xg"] for x in shots if x["side"] == "home"]
    a = [x["xg"] for x in shots if x["side"] == "away"]
    w = d = l = 0
    for _ in range(n):
        gh = og_home + sum(1 for p in h if rnd.random() < p)
        ga = og_away + sum(1 for p in a if rnd.random() < p)
        w += gh > ga; d += gh == ga; l += gh < ga
    return round(100 * w / n), round(100 * d / n), round(100 * l / n)


def add(pack: dict) -> dict:
    shots = pack.get("shots") or []
    if len(shots) < 4:
        return pack
    try:
        f = {x["id"]: x["value"] for x in pack["facts"]}
        H, A = pack["home"], pack["away"]
        res = {"home": _side(shots, "home"), "away": _side(shots, "away")}
        sh, sa = int(f.get("score_home", 0) or 0), int(f.get("score_away", 0) or 0)
        og_home = max(0, sh - res["home"]["goals"])        # goals not from a home shot = own goals for home
        og_away = max(0, sa - res["away"]["goals"])
        hw, dr, aw = _simulate(shots)                       # chances only, own goals left out
        facts = []

        def add_fact(fid, label, value):
            facts.append({"id": fid, "label": label, "value": value})
        for side, team in (("home", H), ("away", A)):
            r, other = res[side], res["away" if side == "home" else "home"]
            add_fact(f"diag_{side}_xg_per_shot", f"{team}: average xG per shot", r["xg_per_shot"])
            add_fact(f"diag_{side}_big_chances", f"{team}: chances worth 0.3 xG or more / scored",
                     f"{r['big']} / {r['big_scored']}")
            add_fact(f"diag_{side}_inbox_pct", f"{team}: % of shots from inside the box", r["inbox_pct"])
            add_fact(f"diag_{side}_setpiece_xg", f"{team}: xG from set pieces / open play",
                     f"{r['setpiece_xg']} / {r['openplay_xg']}")
            add_fact(f"diag_{side}_goals_minus_xg", f"{team}: goals from shots minus xG (finishing over/under)",
                     round(r["goals"] - r["xg"], 2))
            if r["xgot"] is not None:
                add_fact(f"diag_{side}_xgot", f"{team}: xG on target (xGOT) from {r['on_target']} shots on target",
                         r["xgot"])
                add_fact(f"diag_{side}_placement", f"{team}: xGOT minus xG (shot placement: + good, - poor)",
                         round(r["xgot"] - r["xg"], 2))
                keeper = "away" if side == "home" else "home"
                add_fact(f"diag_{keeper}_keeper_prevented",
                         f"{A if keeper == 'away' else H} goalkeeper: goals prevented (xGOT faced minus goals conceded from shots)",
                         round(r["xgot"] - r["goals"], 2))
        # where the threat came from: channel (seen from the attacker) and type of attack
        sit_name = lambda x: ("fast break" if x.get("situation") == "FastBreak" else
                              "set piece" if x.get("situation") in SET_PIECES else "open play")
        # FotMob shot y: high = the attacker's LEFT (checked against line-ups: a left winger shoots at y ~0.7)
        chan = lambda x: "right" if x["y"] < 1 / 3 else "left" if x["y"] > 2 / 3 else "centre"
        threat = {}
        for side, team in (("home", H), ("away", A)):
            s_ = [x for x in shots if x["side"] == side]
            tot = sum(x["xg"] for x in s_) or 1
            by_c = {c: round(sum(x["xg"] for x in s_ if chan(x) == c), 2) for c in ("left", "centre", "right")}
            by_t = {t: round(sum(x["xg"] for x in s_ if sit_name(x) == t), 2) for t in ("fast break", "open play", "set piece")}
            n_t = {t: sum(1 for x in s_ if sit_name(x) == t) for t in ("fast break", "open play", "set piece")}
            threat[side] = {"by_channel": by_c, "by_type": by_t, "shots_by_type": n_t}
            add_fact(f"diag_{side}_xg_by_channel", f"{team}: xG by channel, seen from the attacker (left / centre / right)",
                     f"{by_c['left']} / {by_c['centre']} / {by_c['right']}")
            add_fact(f"diag_{side}_xg_by_type", f"{team}: xG by type of attack (fast break / open play / set piece), shots in brackets",
                     f"{by_t['fast break']} ({n_t['fast break']}) / {by_t['open play']} ({n_t['open play']}) / {by_t['set piece']} ({n_t['set piece']})")
            big = max(by_c, key=by_c.get)
            add_fact(f"diag_{side}_main_channel", f"{team}: channel that produced most xG, and its share",
                     f"{big} ({round(100 * by_c[big] / tot)}%)")
        add_fact("diag_sim_result", f"With these chances, replayed 20,000 times: {H} win / draw / {A} win (%), own goals not counted",
                 f"{hw} / {dr} / {aw}")
        if og_home or og_away:
            add_fact("diag_own_goals", f"Own goals: for {H} / for {A}", f"{og_home} / {og_away}")
        pack["facts"] += facts
        pack["diagnosis"] = {"home": res["home"], "away": res["away"], "sim": [hw, dr, aw], "threat": threat,
                             "own_goals": [og_home, og_away]}
        log.info("Diagnosis: %s xG %.2f (xGOT %s, %d goals), %s xG %.2f; sim %d/%d/%d", H, res["home"]["xg"],
                 res["home"]["xgot"], res["home"]["goals"], A, res["away"]["xg"], hw, dr, aw)
    except Exception as e:
        log.warning("Diagnosis skipped: %s", e)
    return pack
