"""Voice: one audio file per scene. ElevenLabs (your cloned voice) or silent placeholder."""
import subprocess
from pathlib import Path

import requests

from .common import StopPipeline, log, secret


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _silent(path: Path, seconds: float) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=stereo", "-t", f"{seconds:.2f}", "-c:a", "libmp3lame",
                    "-b:a", "128k", str(path)], check=True)


def _elevenlabs(text: str, path: Path, model_id: str, key: str, voice_id: str) -> None:
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json={"text": text, "model_id": model_id,
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}},
        timeout=120,
    )
    if r.status_code != 200:
        raise StopPipeline(f"ElevenLabs error {r.status_code}: {r.text[:300]}")
    path.write_bytes(r.content)


def narrate(cfg: dict, script: dict, workdir: Path, placeholder: bool = False) -> list[Path]:
    key, voice_id = secret("ELEVENLABS_API_KEY"), secret("ELEVENLABS_VOICE_ID")
    use_real = not placeholder and key and voice_id
    if not use_real:
        log.warning("No ElevenLabs keys (or dry run): using silent placeholder audio.")
    wpm = cfg["writer"]["words_per_minute"]
    files = []
    for sc in script["scenes"]:
        path = workdir / f"voice_{sc['id']:02d}.mp3"
        if use_real:
            _elevenlabs(sc["narration"], path, cfg["voice"]["model_id"], key, voice_id)
        else:
            words = len(sc["narration"].split())
            _silent(path, max(3.0, words / wpm * 60))
        files.append(path)
    return files
