"""Editor: turns scene images + narration into one MP4, with optional cleared music and captions."""
import random
import subprocess
from pathlib import Path

from .common import ASSETS_DIR, log
from .voice import duration

FPS = 30
PAD = 0.4  # seconds of breathing room after each scene


def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def scene_clip(image: Path, audio: Path, out: Path) -> float:
    dur = duration(audio) + PAD
    frames = int(dur * FPS)
    vf = (f"scale=2112:1188,zoompan=z='min(zoom+0.0004,1.05)':x='iw/2-(iw/zoom/2)':"
          f"y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={FPS},format=yuv420p")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(image), "-i", str(audio),
          "-filter_complex", f"[0:v]{vf}[v];[1:a]apad=pad_dur={PAD}[a]",
          "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast",
          "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-r", str(FPS), str(out)])
    return dur


def assemble(images: list[Path], audios: list[Path], workdir: Path) -> tuple[Path, list[float]]:
    clips, durs = [], []
    for i, (img, aud) in enumerate(zip(images, audios)):
        clip = workdir / f"clip_{i:02d}.mp4"
        durs.append(scene_clip(img, aud, clip))
        clips.append(clip)
    listing = workdir / "clips.txt"
    listing.write_text("".join(f"file '{c.name}'\n" for c in clips))
    joined = workdir / "joined.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
          "-c", "copy", str(joined)])

    final = add_music(joined, workdir / "video.mp4")
    for c in clips:
        c.unlink()
    log.info("Video rendered: %.1f minutes", sum(durs) / 60)
    return final, durs


MUSIC_CACHE = ASSETS_DIR / "music" / "cache"


def _music_track(kind: str, team: str = "") -> Path | None:
    """The bed for this video: tracks listed in config.yaml (music.tracks), downloaded once and cached.
    kind = "main" or "short"; a track whose "teams" list names the home team is preferred."""
    import requests
    from .common import load_config
    tracks = [t for t in (load_config().get("music") or {}).get("tracks", []) if t.get("kind") == kind]
    if not tracks:
        local = sorted((ASSETS_DIR / "music").glob("*.mp3"))
        return random.choice(local) if local else None
    team_l = (team or "").lower()
    fitting = [t for t in tracks if any(x.lower() in team_l for x in t.get("teams", []))]
    pick = random.choice(fitting or [t for t in tracks if not t.get("teams")] or tracks)
    MUSIC_CACHE.mkdir(parents=True, exist_ok=True)
    path = MUSIC_CACHE / f"{pick['name']}.mp3"
    if not path.exists():
        try:
            r = requests.get(pick["url"], timeout=60)
            r.raise_for_status()
            path.write_bytes(r.content)
        except Exception as e:
            log.warning("Music %s not downloaded (%s); no music bed.", pick["name"], e)
            return None
    return path


def _duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def add_music(src: Path, dst: Path, kind: str = "main", team: str = "") -> Path:
    """Mix the music bed under the narration: it ducks while the voice speaks, fades in and out."""
    from .common import load_config
    mcfg = load_config().get("music") or {}
    track = _music_track(kind, team) if mcfg.get("enabled", True) else None
    if not track:
        src.rename(dst)
        return dst
    vol = mcfg.get("volume_short" if kind == "short" else "volume", 0.16)
    dur = _duration(src)
    fade_out = max(0.0, dur - 2.5)
    log.info("Adding music bed: %s (ducked under the voice)", track.name)
    graph = (f"[0:a]asplit=2[voice][sc];"
             f"[1:a]volume={vol},afade=t=in:st=0:d=2,afade=t=out:st={fade_out:.2f}:d=2.5[m];"
             f"[m][sc]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=450:makeup=1[duck];"
             f"[voice][duck]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-stream_loop", "-1", "-i", str(track),
          "-filter_complex", graph, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
          str(dst)])
    src.unlink()
    return dst


def _ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def captions(script: dict, durs: list[float], path: Path, words_per_line: int = 9,
             workdir: Path | None = None) -> Path:
    """SRT captions: exact word timings from the voice when we have them, otherwise estimated."""
    import json
    lines, t, n = [], 0.0, 1
    for sc, d in zip(script["scenes"], durs):
        timed = workdir / f"voice_{sc['id']:02d}.words.json" if workdir else None
        if timed and timed.exists():
            ws = json.loads(timed.read_text(encoding="utf-8"))
            for i in range(0, len(ws), words_per_line):
                chunk = ws[i:i + words_per_line]
                lines.append(f"{n}\n{_ts(t + chunk[0]['start'])} --> {_ts(t + chunk[-1]['end'])}\n"
                             f"{' '.join(w['w'] for w in chunk)}\n")
                n += 1
            t += d
            continue
        words = sc["narration"].split()
        speak = max(0.5, d - PAD)
        chunks = [words[i:i + words_per_line] for i in range(0, len(words), words_per_line)]
        for chunk in chunks:
            span = speak * len(chunk) / max(1, len(words))
            lines.append(f"{n}\n{_ts(t)} --> {_ts(t + span)}\n{' '.join(chunk)}\n")
            t += span
            n += 1
        t += PAD
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
