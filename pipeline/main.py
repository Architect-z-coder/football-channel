"""Orchestrator: Scout -> Writer -> Fact-checker -> Visuals -> Voice -> Editor -> Publisher -> Alert.

Usage:
  python -m pipeline.main               # full run (needs all secrets)
  python -m pipeline.main --dry-run     # sample match, no upload; AI used only if a key is set
  python -m pipeline.main --no-upload   # real match, everything except the upload
  python -m pipeline.main --list        # show recent finished matches to choose from
  python -m pipeline.main --pick "Arsenal Chelsea"   # make a video about the match you choose

Without --pick, the next line of data/queue.txt is used (and removed after a successful run).
"""
import argparse
import sys
from datetime import date

from . import factcheck, notify, render, visuals, voice, writer
from .common import DATA_DIR, OUT_DIR, SAMPLES_DIR, StopPipeline, load_config, log, read_json, \
    secret, slugify, write_json

MAX_ATTEMPTS = 2
QUEUE = DATA_DIR / "queue.txt"


def next_in_queue() -> str | None:
    if not QUEUE.exists():
        return None
    for line in QUEUE.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.strip().startswith("#"):
            return line.strip()
    return None


def pop_queue(pick: str) -> None:
    lines = QUEUE.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip() == pick:
            del lines[i]
            break
    QUEUE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def show_list() -> int:
    from .fdorg import list_matches
    cfg = load_config()
    rows = list_matches(cfg)
    days = cfg["scout"]["look_back_days"]
    text = (f"Finished matches in the last {days} days (most interesting first).\n"
            "To choose one, copy its number (first column) or type the two team names.\n\n"
            + ("\n".join(rows) if rows else "None found. Try a longer look-back."))
    print(text)
    import os
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## Matches to choose from\n\n```\n" + text + "\n```\n")
    notify.send(text[:3800])
    return 0


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


def run(dry_run: bool, upload: bool, pick: str | None = None) -> int:
    cfg = load_config()
    from_queue = False
    if not dry_run and not pick:
        pick = next_in_queue()
        from_queue = bool(pick)
        if pick:
            log.info("Next match from the queue: %s", pick)
    if dry_run:
        pack = read_json(SAMPLES_DIR / "sample_pack.json")  # fictional match, same shape as a real pack
    elif cfg.get("data_source", "football-data") == "football-data":
        from .fdorg import scout
        pack = scout(cfg, pick)
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

    audios = voice.narrate(cfg, script, workdir, placeholder=dry_run and not secret("ELEVENLABS_API_KEY"))
    if cfg.get("render_engine", "motion") == "motion":
        from . import motion
        video, durs = motion.render(cfg, script, pack, audios, workdir)
    else:  # fallback: still images with a slow zoom
        images = []
        for sc in script["scenes"]:
            img = workdir / f"scene_{sc['id']:02d}.png"
            visuals.render_scene(sc, pack, cfg, img)
            images.append(img)
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
    if from_queue and upload and not dry_run:
        pop_queue(pick)  # only remove it once the video is really uploaded
    log.info("Done. Output in %s", workdir)
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-upload", action="store_true")
    p.add_argument("--list", action="store_true")
    p.add_argument("--pick", default="")
    args = p.parse_args()
    try:
        if args.list:
            sys.exit(show_list())
        sys.exit(run(dry_run=args.dry_run, upload=not args.no_upload, pick=args.pick or None))
    except StopPipeline as e:
        log.error("Stopped: %s", e)
        notify.send(f"Pipeline stopped, nothing was published.\n\nReason: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
