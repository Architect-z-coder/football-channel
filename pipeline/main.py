"""Orchestrator: Scout -> Writer -> Fact-checker -> Visuals -> Voice -> Editor -> Publisher -> Alert.

Usage:
  python -m pipeline.main               # full run (needs all secrets)
  python -m pipeline.main --dry-run     # sample match, no upload; AI used only if a key is set
  python -m pipeline.main --no-upload   # real match, everything except the upload
"""
import argparse
import sys
from datetime import date

from . import factcheck, notify, render, visuals, voice, writer
from .common import DATA_DIR, OUT_DIR, SAMPLES_DIR, StopPipeline, load_config, log, read_json, \
    secret, slugify, write_json

MAX_ATTEMPTS = 2


def get_script(cfg, pack, use_ai):
    if not use_ai:
        log.warning("No ANTHROPIC_API_KEY: using the sample script.")
        script = read_json(SAMPLES_DIR / "sample_script.json")
        return script, factcheck.check(cfg, script, pack, use_ai=False)
    feedback = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        script = writer.write_script(cfg, pack, feedback)
        report = factcheck.check(cfg, script, pack)
        if report["ok"]:
            return script, report
        feedback = "\n".join(report["problems"])
        log.warning("Attempt %d failed fact-check:\n%s", attempt, feedback)
    return script, report


def run(dry_run: bool, upload: bool) -> int:
    cfg = load_config()
    if dry_run:
        pack = read_json(SAMPLES_DIR / "sample_pack.json")  # fictional match, same shape as a real pack
    elif cfg.get("data_source", "football-data") == "football-data":
        from .fdorg import scout
        pack = scout(cfg)
    else:
        from .scout import scout
        pack = scout(cfg)

    workdir = OUT_DIR / f"{date.today():%Y%m%d}-{slugify(pack['home'] + '-' + pack['away'])}"
    workdir.mkdir(parents=True, exist_ok=True)
    write_json(workdir / "datapack.json", pack)

    script, report = get_script(cfg, pack, use_ai=bool(secret("ANTHROPIC_API_KEY")))
    write_json(workdir / "script.json", script)
    write_json(workdir / "factcheck.json", report)
    if not report["ok"]:
        raise StopPipeline("Script failed fact-checking after retries:\n- " +
                           "\n- ".join(report["problems"][:10]))

    images = []
    for sc in script["scenes"]:
        img = workdir / f"scene_{sc['id']:02d}.png"
        visuals.render_scene(sc, pack, cfg, img)
        images.append(img)
    audios = voice.narrate(cfg, script, workdir, placeholder=dry_run and not secret("ELEVENLABS_API_KEY"))
    video, durs = render.assemble(images, audios, workdir)
    srt = render.captions(script, durs, workdir / "captions.srt")
    thumbs = visuals.render_thumbnails(script, pack, cfg, workdir)
    minutes = sum(durs) / 60

    meta = {"titles": script["title_options"], "description": script["description"],
            "tags": script.get("tags", []), "minutes": round(minutes, 1),
            "fixture_id": pack["fixture_id"]}
    write_json(workdir / "metadata.json", meta)

    has_voice = bool(secret("ELEVENLABS_API_KEY") and secret("ELEVENLABS_VOICE_ID"))
    if upload and not dry_run and not has_voice:
        notify.send(f"Video made with silent audio (no voice keys yet), so it was NOT uploaded. "
                    f"Files: {workdir.name}")
        upload = False
    if upload and not dry_run:
        from .publish import upload as yt_upload
        vid = yt_upload(cfg, script, video, srt, thumbs)
        history = read_json(DATA_DIR / "history.json", {"fixtures": []})
        history["fixtures"].append(pack["fixture_id"])
        write_json(DATA_DIR / "history.json", history)
        notify.send(
            f"New video ready for review ({minutes:.1f} min): {pack['home']} vs {pack['away']}\n\n"
            f"Title: {script['title_options'][0]}\n"
            f"Other titles to A/B test: {' | '.join(script['title_options'][1:])}\n\n"
            f"Review, then set to Public or Scheduled:\nhttps://studio.youtube.com/video/{vid}/edit")
    else:
        notify.send(f"Test run finished ({minutes:.1f} min). Files: {workdir.name}")
    log.info("Done. Output in %s", workdir)
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-upload", action="store_true")
    args = p.parse_args()
    try:
        sys.exit(run(dry_run=args.dry_run, upload=not args.no_upload))
    except StopPipeline as e:
        log.error("Stopped: %s", e)
        notify.send(f"Pipeline stopped, nothing was published.\n\nReason: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
