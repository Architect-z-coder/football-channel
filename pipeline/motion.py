"""Motion graphics: renders the video with Remotion (animated scenes, captions, transitions, SFX)."""
import math
import os
import shutil
import subprocess
from pathlib import Path

from .common import ROOT, StopPipeline, log, write_json
from .render import PAD, add_music
from .voice import duration

VIDEO_DIR = ROOT / "video"
FPS = 30


def _events(pack: dict) -> list[dict]:
    out = []
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
        scenes.append({"id": sc["id"], "durationInFrames": frames, "audio": f"run/{audio.name}",
                       "visual": sc.get("visual") or {}, "on_screen": sc.get("on_screen", ""),
                       "narration": sc.get("narration", "")})
    props = {
        "channel": cfg["channel"]["name"],
        "competition": pack["competition"],
        "home": pack["home"],
        "away": pack["away"],
        "source": pack.get("source", "API-Football"),
        "facts": {f["id"]: f["value"] for f in pack["facts"]},
        "events": _events(pack),
        "shots": pack.get("shots", []),
        "scenes": scenes,
    }
    return props, durs


def render(cfg: dict, script: dict, pack: dict, audios: list[Path], workdir: Path):
    props, durs = build_props(cfg, script, pack, audios)
    props_file = workdir / "props.json"
    write_json(props_file, props)
    raw = workdir / "motion.mp4"
    cmd = ["npx", "remotion", "render", "src/index.jsx", "Match", str(raw),
           f"--props={props_file}", "--codec=h264", "--crf=20", "--log=error"]
    browser = os.environ.get("REMOTION_BROWSER")
    if browser:
        cmd.append(f"--browser-executable={browser}")
    concurrency = os.environ.get("REMOTION_CONCURRENCY")
    if concurrency:
        cmd.append(f"--concurrency={concurrency}")
    log.info("Rendering motion graphics with Remotion (%d scenes, %.1f min)...",
             len(props["scenes"]), sum(durs) / 60)
    result = subprocess.run(cmd, cwd=VIDEO_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise StopPipeline(f"Remotion render failed:\n{(result.stderr or result.stdout)[-1500:]}")
    final = add_music(raw, workdir / "video.mp4")
    shutil.rmtree(VIDEO_DIR / "public" / "run", ignore_errors=True)
    return final, durs
