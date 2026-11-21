"""Shorts: 2 vertical clips (20-35 s) cut from each match video's strongest ideas.

Each short is written by the AI from the same data pack, fact-checked the same way, voiced, and
rendered with the same graphics. A short that fails any step is skipped: it never blocks the main video.
"""
import json
from pathlib import Path

from . import factcheck, voice
from .common import ai_pack, log, write_json
from .llm import ask_json

VISUALS = ["goal_replay", "diagnosis", "result_odds", "tactics_board", "threat_map", "quote_card", "lineups", "player_ratings", "momentum", "key_number", "scoreline", "halftime_fulltime", "stat_bars", "shot_map", "xg_timeline",
           "table_snapshot", "form_compare", "history_lens"]

SYSTEM = f"""You write 2 YouTube Shorts about one football match for a faceless storytelling channel.
Each Short is its OWN small story (30-45 seconds, 60-95 words), understandable without the main video,
and the two never repeat each other's topic. Formats, one of each:

WRITING STYLE (house voice, modelled on how the best long-form football analysts work; never name or
imitate any real writer, never borrow their phrases):
- Start from one concrete moment, then widen to the idea behind it: what was each coach trying to do,
  and why did it work or fail? Coaches are thinkers with a plan; explain the plan, then judge it.
- Cause and effect, not adjectives: "because the full-back pushed up, the space behind him opened",
  not "a brilliant move".
- Where the pack's history lens fits, place tonight in a longer line of ideas in one or two sentences,
  then come back to the match.
- Calm, exact and fair. No hype, no cliches ("game-changer", "masterclass", "statement win"), no
  exclamation marks. A dry, understated line is allowed once or twice per Short.
- Honest about limits: say what the numbers show, and say plainly what they cannot show.
- The verdict is argued, not shouted: state it in one clear sentence and show the two or three facts
  that carry it.
- Plain spoken English for an international audience: explain a term the first time, short words over
  long ones, one idea per sentence.

1. "player_spotlight" - the best-rated player of the match (from the pack's ratings): who he is in this
   story, what he did (goals, assists, chances, duels from the pack), why it mattered, what it says about
   his team or coach. Hook = his rating or his most striking act.
2. "turning_point" - THE thing that decided this match, the differentiator. First find it, then tell it:
   it may be a goal, but just as well a tactic or pattern (set pieces, a deep block that held then broke,
   a pressing plan), a substitution, a red card, a keeper's night, or a swing in momentum. Use the
   diag_* facts to prove it (set-piece vs open-play xG, finishing vs xG, goals prevented, the 20,000
   replays) and the coaches' or papers' words when they name it. Structure: the situation before ->
   the moment or pattern -> why it changed the match -> what it says. If it is a goal, use a
   goal_replay shot ({{"type": "goal_replay", "minute": <the goal's minute>}}, never for an own goal);
   otherwise momentum, shot_map, diagnosis, result_odds or a stat graphic. Hook = the turning point in
   a few words ("Minute 49 changed everything", "Set pieces won this").

RULES
1. Closed book: every number, name, minute and claim must come from the data pack. Digits in narration.
   No general claims (rare, record, first ever) the pack cannot prove.
2. Hook in the first sentence (under 10 words): the most striking fact, as a scene. No greetings.
3. Shot list: 3-6 shots, each 1-2 short spoken sentences ("text") with the picture on screen
   ("visual"). Show the person's photo when he is the subject ({{"type": "photo", "photo": "<name as in
   the pack's photos list>", "caption": "<true, 2-7 words>"}}); otherwise a graphic: one of {VISUALS}.
   Never the same visual twice in a row. Captions never claim a photo is from this match.
4. End with one question for the comments, then "Full story on the channel."
5. "title": under 60 characters, accurate. "hook": the on-screen headline, 2-6 words.
6. Never mention politics, transfer rumours, betting, injury speculation or private lives.
Never say "the pack" or "the data pack" to the viewer; say "the match data" or just state the fact.
Return ONLY JSON: {{"shorts": [{{"id": 1, "format": "player_spotlight", "title": str, "hook": str,
  "shots": [{{"text": str, "visual": {{...}}}}], "fact_ids": [str]}}, {{"id": 2, "format": "turning_point", ...}}]}}"""


def write(cfg: dict, pack: dict, script: dict, feedback: str | None = None) -> list[dict]:
    main = {"title": script["title_options"][0],
            "keys": [sc.get("on_screen") for sc in script["scenes"]]}
    user = (f"DATA PACK:\n{json.dumps(ai_pack(pack), ensure_ascii=False)}\n\n"
            f"THE MAIN VIDEO (for context: tell DIFFERENT stories, do not copy it):\n{json.dumps(main, ensure_ascii=False)}\n")
    if feedback:
        user += f"\nYour previous shorts failed fact-checking. Fix these problems:\n{feedback}\n"
    shorts = ask_json(cfg["writer"]["model"], SYSTEM, user, max_tokens=12000).get("shorts", [])
    out = []
    for i, s in enumerate(shorts[: cfg.get("shorts", {}).get("count", 2)], start=1):
        shots = [x for x in s.get("shots") or [] if (x.get("text") or "").strip()]
        for x in shots:
            if (x.get("visual") or {}).get("type") not in VISUALS + ["photo"]:
                x["visual"] = {"type": "scoreline"}
        s["shots"] = shots
        s["narration"] = " ".join(x["text"].strip() for x in shots) or s.get("narration", "")
        graphics = [x["visual"] for x in shots if x["visual"].get("type") != "photo"]
        s["visual"] = graphics[0] if graphics else {"type": "scoreline"}
        out.append({**s, "id": i})
    return out


def _as_script(shorts: list[dict]) -> dict:
    return {"scenes": [{"id": s["id"], "narration": s["narration"], "on_screen": s["hook"],
                        "visual": s.get("visual", {}), "shots": s.get("shots", []),
                        "fact_ids": s.get("fact_ids", [])} for s in shorts]}


def prepare(cfg: dict, pack: dict, script: dict) -> list[dict]:
    """Write and fact-check the shorts (no voice, no render). [] if they fail twice."""
    feedback = None
    for _ in range(2):
        shorts = write(cfg, pack, script, feedback)
        report = factcheck.check(cfg, _as_script(shorts), pack)
        if report["ok"]:
            return shorts
        feedback = "\n".join(report["problems"])
    log.warning("Shorts failed fact-check twice; skipping shorts.")
    return []


def make(cfg: dict, pack: dict, script: dict, workdir: Path, placeholder: bool,
         preset: list[dict] | None = None) -> list[dict]:
    """Write, check, voice and render the shorts. Returns [{"short": ..., "video": Path}]."""
    if not cfg.get("shorts", {}).get("enabled", True):
        return []
    outdir = workdir / "shorts"
    outdir.mkdir(exist_ok=True)
    try:
        shorts, feedback = preset or [], None
        for _ in range(0 if preset else 2):
            shorts = write(cfg, pack, script, feedback)
            report = factcheck.check(cfg, _as_script(shorts), pack)
            if report["ok"]:
                break
            feedback = "\n".join(report["problems"])
        else:
            if not preset:
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
