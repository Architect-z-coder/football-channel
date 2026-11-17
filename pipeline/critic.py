"""Critic: a second AI pass that judges the script as a YouTube editor would (hook, pacing, clarity).

It never changes facts. If the script scores below the bar, the writer gets the critic's notes and
rewrites once; the rewrite must pass the fact-check again, otherwise the original script is kept.
"""
import json

from .common import log
from .llm import ask_json

CRITIC_SYSTEM = """You are a senior YouTube editor for a football analysis channel. You judge scripts for
viewer retention, not for facts (facts are checked separately and must not change).

Score each from 1 to 10:
- hook: do the first 2 sentences of scene 1 give a concrete, surprising fact AND an open question that
  makes a football fan need the answer? Vague openers ("In this video...", "Let's talk about...") score 3 or less.
- payoff: is it a STORY - clear characters, stakes, a turning point and a satisfying reveal - with the
  data used as evidence, not a list of statistics? Does the ending answer the opening question?
  A script that reads like a stats report scores 4 or less.
- pace: short sentences, no repetition, no filler, each scene moves the story forward.
- clarity: a casual fan understands every term (xG etc. explained once, simply).

Then give at most 6 short, specific, actionable notes (one sentence each) (quote the weak line and say what to do instead).
Notes may only use numbers and facts already in the script or data pack.
Return ONLY JSON: {"hook": int, "payoff": int, "pace": int, "clarity": int, "notes": [str, ...]}"""


def review(cfg: dict, script: dict, pack: dict) -> dict:
    slim = {k: v for k, v in pack.items() if k not in ("history",)}
    user = (f"DATA PACK:\n{json.dumps(slim, ensure_ascii=False)}\n\n"
            f"SCRIPT:\n{json.dumps(script, ensure_ascii=False)}")
    r = ask_json(cfg["writer"]["model"], CRITIC_SYSTEM, user, max_tokens=6000)
    scores = {k: int(r.get(k, 0) or 0) for k in ("hook", "payoff", "pace", "clarity")}
    return {**scores, "notes": [str(n) for n in r.get("notes", [])][:6]}


def needs_rewrite(cfg: dict, report: dict) -> bool:
    bar = cfg.get("critic", {})
    return (report["hook"] < bar.get("min_hook", 8)
            or min(report["payoff"], report["pace"], report["clarity"]) < bar.get("min_other", 7))


def feedback(report: dict) -> str:
    log.info("Critic: hook %d, payoff %d, pace %d, clarity %d", report["hook"], report["payoff"],
             report["pace"], report["clarity"])
    return ("An editor reviewed your draft for viewer retention. Keep every fact and number exactly as "
            "supported by the data pack, keep the structure and rules, and improve the script using "
            "these notes:\n- " + "\n- ".join(report["notes"]))
