"""Fact-checker: two independent checks. Any failure stops the video.

1. Number check (code, no AI): every number in the script must exist in the data pack,
   or be a simple sum/difference of a home/away pair, or a structural number (1-3, 90).
2. Claim check (separate AI pass): flags claims the data cannot support and banned topics.
"""
import json
import re

from .common import log
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
Also flag anything about politics, transfer rumours, betting, injuries or private lives.
Return ONLY JSON: {"ok": bool, "problems": [str, ...]}"""


def claim_check(cfg: dict, script: dict, pack: dict) -> list[str]:
    user = f"DATA PACK:\n{json.dumps(pack, ensure_ascii=False)}\n\nSCRIPT:\n{json.dumps(script, ensure_ascii=False)}"
    result = ask_json(cfg["writer"]["model"], CLAIM_SYSTEM, user, max_tokens=3000)
    return [] if result.get("ok") and not result.get("problems") else list(result.get("problems", []))


def check(cfg: dict, script: dict, pack: dict, use_ai: bool = True) -> dict:
    problems = number_check(script, pack) + banned_check(script, cfg.get("banned_topics", []))
    if use_ai and not problems:
        problems += claim_check(cfg, script, pack)
    report = {"ok": not problems, "problems": problems}
    log.info("Fact-check: %s (%d problems)", "PASS" if report["ok"] else "FAIL", len(problems))
    return report
