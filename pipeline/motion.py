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
        scenes.append({"id": sc["id"], "durationInFrames": frames, "audio": f"run/{audio.name}",
                       "wordStarts": word_starts,
                       "visual": sc.get("visual") or {}, "on_screen": sc.get("on_screen", ""),
                       "narration": sc.get("narration", "")})
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
        "press": pack.get("press") or [],
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
    props, durs = build_props(cfg, script, pack, audios)
    props_file = workdir / "props.json"
    write_json(props_file, props)
    raw = workdir / "motion.mp4"
    log.info("Rendering motion graphics with Remotion (%d scenes, %.1f min)...",
             len(props["scenes"]), sum(durs) / 60)
    _remotion("Match", props_file, raw)
    final = add_music(raw, workdir / "video.mp4")
    shutil.rmtree(VIDEO_DIR / "public" / "run", ignore_errors=True)
    return final, durs


def render_short(cfg: dict, short: dict, pack: dict, audio: Path, outdir: Path) -> Path:
    """One vertical short (1080x1920) with the same graphics, captions and data credit."""
    run_dir = VIDEO_DIR / "public" / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(audio, run_dir / f"short_{short['id']}.mp3")
    timed = audio.with_suffix(".words.json")
    word_starts = ([w["start"] for w in json.loads(timed.read_text(encoding="utf-8"))]
                   if timed.exists() else None)
    frames = math.ceil((duration(audio) + 0.3) * FPS) + 45  # + closing card
    fake_script = {"scenes": [{"visual": short.get("visual", {})}]}
    props = {
        "channel": cfg["channel"]["name"], "competition": pack["competition"],
        "home": pack["home"], "away": pack["away"],
        "source": pack.get("source", "API-Football") + (" + StatsBomb" if history.used_in(fake_script) else ""),
        "facts": {f["id"]: f["value"] for f in pack["facts"]}, "events": _events(pack),
        "shots": pack.get("shots", []), "momentum": pack.get("momentum") or [],
        "history": history.used_in(fake_script),
        "scenes": [],
        "short": {"hook": short["hook"], "narration": short["narration"], "visual": short.get("visual", {}),
                  "audio": f"run/short_{short['id']}.mp3", "wordStarts": word_starts,
                  "durationInFrames": frames},
    }
    props_file = outdir / f"short_{short['id']}_props.json"
    write_json(props_file, props)
    raw = outdir / f"short_{short['id']}_raw.mp4"
    log.info("Rendering short %s (%.0f s)...", short["id"], frames / FPS)
    _remotion("Short", props_file, raw)
    final = add_music(raw, outdir / f"short_{short['id']}.mp4")
    shutil.rmtree(run_dir, ignore_errors=True)
    return final
