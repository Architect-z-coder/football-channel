"""Shorts: 2 vertical clips (20-35 s) cut from each match video's strongest ideas.

Each short is written by the AI from the same data pack, fact-checked the same way, voiced, and
rendered with the same graphics. A short that fails any step is skipped: it never blocks the main video.
"""
import json
from pathlib import Path

from . import factcheck, voice
from .common import ai_pack, log, write_json
from .llm import ask_json

VISUALS = ["momentum", "key_number", "scoreline", "halftime_fulltime", "stat_bars", "shot_map", "xg_timeline",
           "table_snapshot", "form_compare", "history_lens"]

SYSTEM = f"""You write YouTube Shorts for a faceless football analysis channel. Each short is a 20-35 second
vertical clip that stops the scroll with one striking fact and teaches one idea.

RULES
1. Closed book: every number, name, minute and result must come from the data pack. Digits in narration.
2. Hook in the first 5 words: start with the most surprising number or contrast. No greetings, no
   "in this video", no question as the very first words.
3. Narration: 50-80 words, short sentences, one idea, then a one-line payoff. End exactly with:
   "Full breakdown on the channel."
4. "hook": the on-screen headline, 2-6 words, punchy, true.
5. "visual": one of {VISUALS}, using the same parameters as in the main script
   (stat_bars needs "stats"; key_number needs "value" and "label"; history_lens needs "lens" and "metrics").
   Use momentum only if the pack says "momentum_available"; shot_map / xg_timeline only if the pack has "shots"; table_snapshot / form_compare only if the
   pack has those facts. The two shorts must use different visuals and different ideas.
6. "title": under 60 characters, accurate, no hashtags. "fact_ids": the fact ids you used.
7. Never mention politics, transfer rumours, betting, injuries or private lives.
Return ONLY JSON: {{"shorts": [{{"id": 1, "title": str, "hook": str, "narration": str,
  "visual": {{...}}, "fact_ids": [str]}}, {{"id": 2, ...}}]}}"""


def write(cfg: dict, pack: dict, script: dict, feedback: str | None = None) -> list[dict]:
    main = {"title": script["title_options"][0],
            "keys": [sc.get("on_screen") for sc in script["scenes"]]}
    user = (f"DATA PACK:\n{json.dumps(ai_pack(pack), ensure_ascii=False)}\n\n"
            f"THE MAIN VIDEO (for context, do not copy it):\n{json.dumps(main, ensure_ascii=False)}\n")
    if feedback:
        user += f"\nYour previous shorts failed fact-checking. Fix these problems:\n{feedback}\n"
    shorts = ask_json(cfg["writer"]["model"], SYSTEM, user, max_tokens=4000).get("shorts", [])
    out = []
    for i, s in enumerate(shorts[: cfg.get("shorts", {}).get("count", 2)], start=1):
        if s.get("visual", {}).get("type") not in VISUALS:
            s["visual"] = {"type": "scoreline"}
        out.append({**s, "id": i})
    return out


def _as_script(shorts: list[dict]) -> dict:
    return {"scenes": [{"id": s["id"], "narration": s["narration"], "on_screen": s["hook"],
                        "visual": s.get("visual", {}), "fact_ids": s.get("fact_ids", [])} for s in shorts]}


def make(cfg: dict, pack: dict, script: dict, workdir: Path, placeholder: bool) -> list[dict]:
    """Write, check, voice and render the shorts. Returns [{"short": ..., "video": Path}]."""
    if not cfg.get("shorts", {}).get("enabled", True):
        return []
    outdir = workdir / "shorts"
    outdir.mkdir(exist_ok=True)
    try:
        shorts, feedback = [], None
        for _ in range(2):
            shorts = write(cfg, pack, script, feedback)
            report = factcheck.check(cfg, _as_script(shorts), pack)
            if report["ok"]:
                break
            feedback = "\n".join(report["problems"])
        else:
            log.warning("Shorts failed fact-check twice; skipping shorts.")
            return []
        write_json(outdir / "shorts.json", shorts)
        audios = voice.narrate(cfg, {"scenes": [{"id": s["id"], "narration": s["narration"]}
                                                for s in shorts]}, outdir, placeholder=placeholder)
        from .motion import render_short
        made = []
        for s, audio in zip(shorts, audios):
            try:
                made.append({"short": s, "video": render_short(cfg, s, pack, audio, outdir)})
            except Exception as e:
                log.warning("Short %s failed to render: %s", s["id"], e)
        return made
    except Exception as e:  # shorts are a bonus: never stop the main video
        log.warning("Shorts skipped: %s", e)
        return []
