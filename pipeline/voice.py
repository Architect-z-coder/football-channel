"""Voice: one audio file per scene. ElevenLabs (your cloned voice) or silent placeholder."""
import base64
import json
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


def words_file(audio: Path) -> Path:
    return audio.with_suffix(".words.json")


def _word_times(text: str, alignment: dict | None) -> list[dict] | None:
    """Turn ElevenLabs character timings into one start/end per word of the narration."""
    if not alignment:
        return None
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    out, cur = [], None
    for ch, st, en in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                out.append(cur)
                cur = None
            continue
        if cur is None:
            cur = {"w": "", "start": st, "end": en}
        cur["w"] += ch
        cur["end"] = en
    if cur:
        out.append(cur)
    if [w["w"] for w in out] != text.split():   # timings must match the words we show
        log.warning("Word timings did not line up with the text; captions will use estimates.")
        return None
    return [{"w": w["w"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in out]


def _elevenlabs(text: str, path: Path, model_id: str, key: str, voice_id: str) -> None:
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json={"text": text, "model_id": model_id,
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}},
        timeout=120,
    )
    if r.status_code != 200:
        raise StopPipeline(f"ElevenLabs error {r.status_code}: {r.text[:300]}")
    data = r.json()
    path.write_bytes(base64.b64decode(data["audio_base64"]))
    words = _word_times(text, data.get("alignment"))
    if words:
        words_file(path).write_text(json.dumps(words), encoding="utf-8")


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
