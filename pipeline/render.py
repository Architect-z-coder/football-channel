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

    final = workdir / "video.mp4"
    music = sorted((ASSETS_DIR / "music").glob("*.mp3")) if (ASSETS_DIR / "music").exists() else []
    if music:
        track = random.choice(music)
        log.info("Adding music bed: %s", track.name)
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined), "-stream_loop", "-1",
              "-i", str(track), "-filter_complex",
              "[1:a]volume=0.07[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
              "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", str(final)])
    else:
        joined.rename(final)
    for c in clips:
        c.unlink()
    log.info("Video rendered: %.1f minutes", sum(durs) / 60)
    return final, durs


def _ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def captions(script: dict, durs: list[float], path: Path, words_per_line: int = 9) -> Path:
    """SRT captions timed by spreading each scene's words across its audio."""
    lines, t, n = [], 0.0, 1
    for sc, d in zip(script["scenes"], durs):
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
