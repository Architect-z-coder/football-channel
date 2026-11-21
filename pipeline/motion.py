"""Motion graphics: renders the video with Remotion (animated scenes, captions, transitions, SFX)."""
import json
import math
import os
import shutil
import subprocess
from pathlib import Path

from . import history
from .common import ROOT, StopPipeline, log, write_json
from .render import PAD, add_music
from .voice import duration

VIDEO_DIR = ROOT / "video"
FPS = 30


def _events(pack: dict) -> list[dict]:
    out = []
    for f in pack["facts"]:   # FotMob-only packs list goals as goal_1, goal_2, ...
        if f["id"].startswith("goal_") and isinstance(f["value"], dict):
            v = f["value"]
            out.append({"kind": "goal", "side": "home" if v.get("team") == pack["home"] else "away",
                        "minute": v.get("minute"), "extra": v.get("added_time"), "player": v.get("player")})
    for f in pack["facts"]:
        if not f["id"].startswith("event_") or not isinstance(f["value"], dict):
            continue
        label = f["label"]
        kind = "goal" if "Goal" in label else "red" if "Red Card" in label else None
        if not kind:
            continue
        side = "home" if label.startswith(pack["home"]) else "away"
        out.append({"kind": kind, "side": side, "minute": f["value"].get("minute"),
                    "extra": f["value"].get("extra"), "player": f["value"].get("player")})
    return out


def _quote_frames(pack: dict, vis: dict, tokens: list[str], starts, shot_from: int) -> list[int]:
    """Frames (from the shot start) at which each spoken word of the quote is said, for the highlight."""
    import re as _re
    revs = pack.get("reviews") or []
    i = vis.get("review_index", 0)
    if not (0 <= i < len(revs)):
        return []
    norm = lambda w: _re.sub(r"[^a-z0-9]", "", w.lower())
    idx = [(j, norm(t)) for j, t in enumerate(tokens) if norm(t)]     # skip dashes and lone marks
    toks = [t for _, t in idx]
    for key in ("quote", "quote_en"):
        q = [norm(w) for w in (revs[i].get(key) or "").split() if norm(w)]
        if len(q) < 3:
            continue
        for a in range(len(toks) - len(q) + 1):
            if toks[a:a + len(q)] == q:
                pos = [idx[a + j][0] for j in range(len(q))]
                if starts and len(starts) == len(tokens):
                    return [max(0, int(starts[p] * FPS) - shot_from) for p in pos]
                return [p * 9 for p in pos]      # no timings: about 3.3 words a second
    return []


import re as _re2

_OOH = _re2.compile(r"^(saves?|saved|miss(es|ed)?|wide|post|crossbar|bar|blocked|denied|keeps?)$")
_ROAR = _re2.compile(r"^(scores?|scored|equalises?|equalizes?|equaliser|winner)$")


def crowd_cues(narration: str, starts, frames: int, visuals=()) -> list[dict]:
    """Where a stadium 'ooh' (save, miss) or roar (goal) plays: at the spoken word, max 2 per scene."""
    toks = narration.split()
    if not starts or len(starts) != len(toks):
        starts = [i / max(1, len(toks)) * frames / FPS for i in range(len(toks))]
    cues, last = [], -999
    for w, t in zip(toks, starts):
        k = _re2.sub(r"[^a-z]", "", w.lower())
        kind = "roar" if _ROAR.match(k) else "ooh" if _OOH.match(k) else None
        f = int(t * FPS)
        if kind and f - last > 4 * FPS and f + 30 < frames:
            cues.append({"from": f, "kind": kind}); last = f
        if len(cues) >= 2:
            break
    return cues


def ensure_sfx(cfg: dict) -> None:
    """Download the crowd sounds (made once with Everygen) into the video's public folder."""
    import requests
    for name, url in ((cfg.get("sfx") or {}).get("files") or {}).items():
        dest = VIDEO_DIR / "public" / "sfx" / f"{name}.mp3"
        if dest.exists():
            continue
        try:
            r = requests.get(url, timeout=60); r.raise_for_status(); dest.write_bytes(r.content)
        except Exception as e:
            log.warning("Sound %s not downloaded (%s)", name, e)


def build_props(cfg: dict, script: dict, pack: dict, audios: list[Path]) -> tuple[dict, list[float]]:
    run_dir = VIDEO_DIR / "public" / "run"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    scenes, durs = [], []
    for sc, audio in zip(script["scenes"], audios):
        shutil.copy(audio, run_dir / audio.name)
        seconds = duration(audio) + PAD
        frames = math.ceil(seconds * FPS)
        durs.append(frames / FPS)
        timed = audio.with_suffix(".words.json")
        word_starts = ([w["start"] for w in json.loads(timed.read_text(encoding="utf-8"))]
                       if timed.exists() else None)
        # shot list: each shot starts when its first word is spoken
        shots, n = [], 0
        total_words = max(1, len(sc.get("narration", "").split()))
        for sh in sc.get("shots") or []:
            k = len((sh.get("text") or "").split())
            if word_starts and n < len(word_starts):
                start = int(word_starts[n] * FPS)
            else:
                start = int(n / total_words * (frames - 15))
            frm = 0 if not shots else max(start - 4, shots[-1]["from"] + 20)
            vis = dict(sh.get("visual") or {})
            if vis.get("type") == "tactics_board":     # highlight steps land on their spoken word
                toks = [_re2.sub(r"[^a-z0-9]", "", w.lower()) for w in (sh.get("text") or "").split()]
                ws = word_starts[n:n + k] if word_starts else None
                for st in vis.get("steps") or []:
                    key = _re2.sub(r"[^a-z0-9]", "", str(st.get("word", "")).lower())
                    j = toks.index(key) if key in toks else None
                    if j is not None and ws and len(ws) == len(toks):
                        st["from"] = max(0, int(ws[j] * FPS) - frm)
                    elif j is not None:
                        st["from"] = j * 9
                    else:
                        st.setdefault("from", 30 * (1 + (vis.get("steps") or []).index(st)))
            if vis.get("type") == "press_cut":
                vis["hl"] = _quote_frames(pack, vis, (sh.get("text") or "").split(),
                                          word_starts[n:n + k] if word_starts else None, frm)
            shots.append({"from": frm, "visual": vis})
            n += k
        scenes.append({"id": sc["id"], "durationInFrames": frames, "audio": f"run/{audio.name}",
                       "wordStarts": word_starts, "shots": shots,
                       "visual": sc.get("visual") or {}, "on_screen": sc.get("on_screen", ""),
                       "narration": sc.get("narration", "")})
    from . import nametags
    offs, acc = [], 0.0
    for d in durs:
        offs.append(acc); acc += d
    tag_lists = nametags.tags_for(pack, [{"narration": s["narration"], "word_starts": s["wordStarts"],
                                          "frames": s["durationInFrames"], "offset_s": o}
                                         for s, o in zip(scenes, offs)])
    for s, t in zip(scenes, tag_lists):
        s["tags"] = t
        s["crowd"] = crowd_cues(s["narration"], s["wordStarts"], s["durationInFrames"])
    props = {
        "channel": cfg["channel"]["name"],
        "competition": pack["competition"],
        "home": pack["home"],
        "away": pack["away"],
        "source": pack.get("source", "API-Football") + (" + StatsBomb" if history.used_in(script) else ""),
        "facts": {f["id"]: f["value"] for f in pack["facts"]},
        "events": _events(pack),
        "shots": pack.get("shots", []),
        "momentum": pack.get("momentum") or [],
        "ratings": pack.get("ratings") or [],
        "lineups": pack.get("lineups") or {}, "subs": pack.get("subs") or [],
        "photos": pack.get("photos") or [],
        "press": pack.get("press") or [],
        "reviews": pack.get("reviews") or [],
        "crowdVolume": (cfg.get("sfx") or {}).get("crowd_volume", 0.32),
        "diagnosis": pack.get("diagnosis") or {},
        "goals": [f["value"] for f in pack["facts"] if f["id"].startswith("goal_") and isinstance(f["value"], dict)],
        "history": history.used_in(script),
        "scenes": scenes,
    }
    return props, durs


def _remotion(composition: str, props_file: Path, out: Path) -> None:
    cmd = ["npx", "remotion", "render", "src/index.jsx", composition, str(out),
           f"--props={props_file}", "--codec=h264", "--crf=20", "--log=error"]
    browser = os.environ.get("REMOTION_BROWSER")
    if browser:
        cmd.append(f"--browser-executable={browser}")
    concurrency = os.environ.get("REMOTION_CONCURRENCY")
    if concurrency:
        cmd.append(f"--concurrency={concurrency}")
    result = subprocess.run(cmd, cwd=VIDEO_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise StopPipeline(f"Remotion render failed:\n{(result.stderr or result.stdout)[-1500:]}")


def render(cfg: dict, script: dict, pack: dict, audios: list[Path], workdir: Path):
    ensure_sfx(cfg)
    props, durs = build_props(cfg, script, pack, audios)
    from .common import slugify as _slug
    press_dir = Path(__file__).resolve().parent.parent / "data" / "cache" / "press" / _slug(str(pack["fixture_id"]))
    for r in pack.get("reviews") or []:          # newspaper screenshots
        for f in (r.get("files") or {}).values():
            if (press_dir / f).exists():
                shutil.copy(press_dir / f, VIDEO_DIR / "public" / "run" / f)
    for ph in pack.get("photos") or []:          # free-licence photos from Wikimedia Commons
        src = workdir / "photos" / ph["file"]
        if src.exists():
            shutil.copy(src, VIDEO_DIR / "public" / "run" / ph["file"])
    props_file = workdir / "props.json"
    write_json(props_file, props)
    raw = workdir / "motion.mp4"
    log.info("Rendering motion graphics with Remotion (%d scenes, %.1f min)...",
             len(props["scenes"]), sum(durs) / 60)
    _remotion("Match", props_file, raw)
    final = add_music(raw, workdir / "video.mp4", "main", pack.get("home", ""), str(pack.get("fixture_id", "")))
    shutil.rmtree(VIDEO_DIR / "public" / "run", ignore_errors=True)
    return final, durs


def render_short(cfg: dict, short: dict, pack: dict, audio: Path, outdir: Path) -> Path:
    """One vertical short (1080x1920) with the same graphics, captions and data credit."""
    run_dir = VIDEO_DIR / "public" / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(audio, run_dir / f"short_{short['id']}.mp3")
    for ph in pack.get("photos") or []:
        src = outdir.parent / "photos" / ph["file"]
        if src.exists():
            shutil.copy(src, run_dir / ph["file"])
    timed = audio.with_suffix(".words.json")
    word_starts = ([w["start"] for w in json.loads(timed.read_text(encoding="utf-8"))]
                   if timed.exists() else None)
    frames = math.ceil((duration(audio) + 0.3) * FPS) + 45  # + closing card
    speak = frames - 45
    shots, n = [], 0
    total_words = max(1, len(short["narration"].split()))
    for sh in short.get("shots") or []:
        start = int(word_starts[n] * FPS) if word_starts and n < len(word_starts) else int(n / total_words * speak)
        shots.append({"from": 0 if not shots else max(start - 4, shots[-1]["from"] + 20), "visual": sh.get("visual") or {}})
        n += len((sh.get("text") or "").split())
    from . import nametags
    short_tags = nametags.tags_for(pack, [{"narration": short["narration"], "word_starts": word_starts,
                                           "frames": speak}])[0]
    short_crowd = crowd_cues(short["narration"], word_starts, speak)
    ensure_sfx(cfg)
    fake_script = {"scenes": [{"visual": short.get("visual", {})}]}
    props = {
        "channel": cfg["channel"]["name"], "competition": pack["competition"],
        "home": pack["home"], "away": pack["away"],
        "source": pack.get("source", "API-Football") + (" + StatsBomb" if history.used_in(fake_script) else ""),
        "facts": {f["id"]: f["value"] for f in pack["facts"]}, "events": _events(pack),
        "shots": pack.get("shots", []), "momentum": pack.get("momentum") or [],
        "ratings": pack.get("ratings") or [], "lineups": pack.get("lineups") or {}, "subs": pack.get("subs") or [],
        "diagnosis": pack.get("diagnosis") or {},
        "photos": pack.get("photos") or [], "press": pack.get("press") or [],
        "goals": [f["value"] for f in pack["facts"] if f["id"].startswith("goal_") and isinstance(f["value"], dict)],
        "history": history.used_in(fake_script),
        "crowdVolume": (cfg.get("sfx") or {}).get("crowd_volume", 0.32),
        "scenes": [],
        "short": {"hook": short["hook"], "narration": short["narration"], "visual": short.get("visual", {}),
                  "audio": f"run/short_{short['id']}.mp3", "wordStarts": word_starts, "shots": shots,
                  "tags": short_tags, "crowd": short_crowd,
                  "durationInFrames": frames},
    }
    props_file = outdir / f"short_{short['id']}_props.json"
    write_json(props_file, props)
    raw = outdir / f"short_{short['id']}_raw.mp4"
    log.info("Rendering short %s (%.0f s)...", short["id"], frames / FPS)
    _remotion("Short", props_file, raw)
    final = add_music(raw, outdir / f"short_{short['id']}.mp4", "short", pack.get("home", ""),
                      str(pack.get("fixture_id", "")))
    shutil.rmtree(run_dir, ignore_errors=True)
    return final
