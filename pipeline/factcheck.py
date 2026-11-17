"""Fact-checker: two independent checks. Any failure stops the video.

1. Number check (code, no AI): every number in the script must exist in the data pack,
   or be a simple sum/difference of a home/away pair, or a structural number (1-3, 90).
2. Claim check (separate AI pass): flags claims the data cannot support and banned topics.
"""
import json
import re

from .common import ai_pack, log
from .llm import ask_json

NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
STRUCTURAL = {1.0, 2.0, 3.0, 90.0, 45.0}


def _numbers_in(value) -> list[float]:
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        return [n for v in value.values() for n in _numbers_in(v)]
    if isinstance(value, list):
        return [n for v in value for n in _numbers_in(v)]
    return [float(m) for m in NUM.findall(str(value))]


def allowed_numbers(pack: dict) -> set[float]:
    allowed = set(STRUCTURAL)
    by_id = {f["id"]: f["value"] for f in pack["facts"]}
    for v in by_id.values():
        allowed.update(_numbers_in(v))
    for shot in pack.get("shots", []):  # Understat shot list (minute, xG)
        allowed.update(_numbers_in({"minute": shot.get("minute"), "xg": shot.get("xg")}))
    allowed.update(_numbers_in(ai_pack(pack).get("momentum_home_on_top_pct", {})))
    allowed.update(_numbers_in(pack.get("press", [])))
    allowed.update(_numbers_in(pack.get("context", {})))
    for side in (pack.get("lineups") or {}).values():   # shirt numbers, ratings, values
        allowed.update(_numbers_in(side))
    for lens in pack.get("history", []):  # StatsBomb history lens facts, plus years in its label
        allowed.update(_numbers_in(lens.get("facts", {})))
        allowed.update(_numbers_in(lens.get("label", "")))
        allowed.update(_numbers_in(lens.get("coverage", "")))
    # sums and differences of matching home/away pairs (e.g. "8 more shots")
    for fid, v in by_id.items():
        if fid.startswith("home_"):
            other = by_id.get("away_" + fid[5:])
            a, b = _numbers_in(v), _numbers_in(other)
            if a and b:
                allowed.add(round(a[0] + b[0], 2))
                allowed.add(round(abs(a[0] - b[0]), 2))
    sh, sa = by_id.get("score_home"), by_id.get("score_away")
    if isinstance(sh, int) and isinstance(sa, int):
        allowed.update({float(sh + sa), float(abs(sh - sa))})
    return {round(x, 2) for x in allowed}


def script_text_items(script: dict):
    for sc in script["scenes"]:
        yield sc["id"], "narration", sc.get("narration", "")
        yield sc["id"], "on_screen", sc.get("on_screen", "")
        vis = sc.get("visual", {})
        for k in ("value", "label", "title", "subtitle", "heading"):
            if k in vis:
                yield sc["id"], f"visual.{k}", str(vis[k])
        for k in ("lines", "items"):
            for line in vis.get(k, []):
                yield sc["id"], f"visual.{k}", str(line)
    for t in script.get("title_options", []):
        yield "title", "title", t


def number_check(script: dict, pack: dict) -> list[str]:
    allowed = allowed_numbers(pack)
    problems = []
    for sid, field, text in script_text_items(script):
        for n in _numbers_in(text):
            if round(n, 2) not in allowed:
                problems.append(f"Scene {sid} {field}: number {n:g} is not in the data pack.")
    return problems


def banned_check(script: dict, banned: list[str]) -> list[str]:
    words = {"politic", "rumour", "rumor", "betting", "odds", "bookmaker"}
    problems = []
    for sid, field, text in script_text_items(script):
        low = text.lower()
        for w in words:
            if w in low:
                problems.append(f"Scene {sid} {field}: banned topic word '{w}'.")
    return problems


CLAIM_SYSTEM = """You are a strict football fact-checker. You receive a data pack and a script.
List every statement in the script that the data pack does not support: wrong numbers, wrong names,
wrong minutes, events that are not in the pack, or tactical claims stated as fact that the numbers
cannot show. Reading of the numbers phrased as interpretation ("this suggests") is acceptable.
Statements about coaches' appointments, promises and choices are supported only by the pack's
"context" (each with a source). Quotes must appear word for word in the pack's "press" or "context", attributed to the same speaker.
The pack's "history" list is reference data from StatsBomb about past teams: statements about a
history-lens team are supported only by that lens's facts, label, coverage and "idea" line.
Also flag anything about politics, transfer rumours, betting, injuries or private lives.
Return ONLY JSON: {"ok": bool, "problems": [str, ...]}"""


def claim_check(cfg: dict, script: dict, pack: dict) -> list[str]:
    user = f"DATA PACK:\n{json.dumps(ai_pack(pack), ensure_ascii=False)}\n\nSCRIPT:\n{json.dumps(script, ensure_ascii=False)}"
    result = ask_json(cfg["writer"]["model"], CLAIM_SYSTEM, user, max_tokens=3000)
    return [] if result.get("ok") and not result.get("problems") else list(result.get("problems", []))


def check(cfg: dict, script: dict, pack: dict, use_ai: bool = True) -> dict:
    problems = number_check(script, pack) + banned_check(script, cfg.get("banned_topics", []))
    if use_ai and not problems:
        problems += claim_check(cfg, script, pack)
    report = {"ok": not problems, "problems": problems}
    log.info("Fact-check: %s (%d problems)", "PASS" if report["ok"] else "FAIL", len(problems))
    return report
