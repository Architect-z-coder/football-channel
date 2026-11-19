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
import os
import sys
from pathlib import Path
from datetime import date

from . import critic, factcheck, history, notify, render, shorts, thumbs, visuals, voice, writer
from datetime import datetime, timedelta, timezone

from .common import DATA_DIR, OUT_DIR, SAMPLES_DIR, StopPipeline, load_config, log, read_json, \
    secret, slugify, write_json

MAX_ATTEMPTS = 2
QUEUE = DATA_DIR / "queue.txt"
DASH = DATA_DIR / "dashboard"   # files the dashboard reads
CACHE = DATA_DIR / "cache"      # research + approved script per match (reused if a later step fails)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    rows, data = list_matches(cfg)
    days = cfg["scout"]["look_back_days"]
    write_json(DASH / "matches.json", {"updated": now(), "look_back_days": days, "matches": data})
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
    feedback, script = None, None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        script = writer.write_script(cfg, pack, feedback, previous=script if feedback else None)
        report = factcheck.check(cfg, script, pack)
        if report["ok"]:
            return improve(cfg, pack, script, report)
        feedback = "\n".join(report["problems"])
        log.warning("Attempt %d failed fact-check:\n%s", attempt, feedback)
    return script, report


def improve(cfg, pack, script, report):
    """Critic pass: one rewrite for a weak hook or pacing. A rewrite that fails fact-check is dropped."""
    if not cfg.get("critic", {}).get("enabled", True):
        return script, report
    try:
        review = critic.review(cfg, script, pack)
    except Exception as e:  # the critic is a bonus: never stop a good script because of it
        log.warning("Critic skipped: %s", e)
        return script, report
    report = {**report, "critic": review}
    if not critic.needs_rewrite(cfg, review):
        log.info("Critic: no rewrite needed (hook %d)", review["hook"])
        return script, report
    try:
        better = writer.write_script(cfg, pack, previous=script, editor_notes=critic.feedback(review))
        check2 = factcheck.check(cfg, better, pack)
    except Exception as e:
        log.warning("Critic rewrite failed (%s); keeping the first script.", e)
        return script, report
    if check2["ok"]:
        log.info("Critic rewrite passed fact-check; using it.")
        return better, {**check2, "critic": review, "rewritten": True}
    log.warning("Critic rewrite failed fact-check; keeping the first script.")
    return script, {**report, "rewrite_rejected": check2["problems"][:5]}


def show_data(pick: str | None) -> int:
    """Fetch the data pack for a match and print it. No script, voice or video."""
    from .fdorg import scout
    cfg = load_config()
    pack = scout(cfg, pick or next_in_queue())
    lines = [f"{f['id']}: {f['value']}" for f in pack["facts"]]
    shots = pack.get("shots", [])
    text = (f"{pack['home']} v {pack['away']} ({pack['competition']}), source: {pack.get('source')}\n"
            + "\n".join(lines) + f"\n\nShots: {len(shots)}")
    if shots:
        text += "\n" + "\n".join(f"{s['minute']}' {s['side']} {s['player']} xG {s['xg']} {s['result']}"
                                   for s in shots[:40])
    print(text)
    found = []
    if cfg.get("photos", {}).get("enabled", True):
        from . import photos
        found = photos.find(photos.people_in(pack), OUT_DIR / "photos")
        for ph in found:
            print(f"Photo: {ph['name']} ({ph['role']}) - {ph['licence']}, {ph['author']} - {ph['page']}")
    write_json(DASH / "match_data.json", {
        "photos": [{k: v for k, v in ph.items() if k != "path"} for ph in found],
        "updated": now(), "fixture_id": pack.get("fixture_id"), "home": pack["home"],
        "away": pack["away"], "competition": pack["competition"], "source": pack.get("source"),
        "facts": pack["facts"], "shots": shots})
    import os
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## Match data\n\n```\n" + text + "\n```\n")
    return 0


REVIEW = DATA_DIR / "review"


def _visual_note(v: dict) -> str:
    v = v or {}
    t = v.get("type", "")
    extra = v.get("photo") or v.get("speaker") or v.get("caption") or v.get("text") or ""
    return f"{t}{': ' + str(extra)[:60] if extra else ''}"


def write_draft(pack: dict, script: dict, shorts_list: list, cfg: dict) -> Path:
    """A readable draft for the owner: titles, every scene's words and what is on screen, the Shorts."""
    REVIEW.mkdir(parents=True, exist_ok=True)
    slug = slugify(str(pack["fixture_id"]))
    words = sum(len(sc["narration"].split()) for sc in script["scenes"])
    L = [f"# Draft: {pack['home']} vs {pack['away']}", "",
         f"{pack['competition']} | about {words / cfg['writer']['words_per_minute']:.1f} min | "
         f"voice: {cfg['voice'].get('everygen_voice', '')}", "",
         "Reply **approve**, or say what to change (scene number + what). Nothing is voiced or rendered "
         "until you approve.", "", "## Title options"]
    L += [f"{i}. {t}" for i, t in enumerate(script.get("title_options", []), 1)]
    for sc in script["scenes"]:
        L += ["", f"## Scene {sc['id']}" + (f" | {sc['on_screen']}" if sc.get("on_screen") else "")]
        for sh in sc.get("shots") or [{"text": sc["narration"], "visual": sc.get("visual")}]:
            L += [f"- {sh.get('text', '').strip()}", f"  *On screen: {_visual_note(sh.get('visual'))}*"]
    for x in shorts_list or []:
        L += ["", f"## Short {x['id']} ({x.get('format', '')}): {x.get('title', '')}", "", x["narration"]]
    path = REVIEW / f"{slug}.md"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def run(dry_run: bool, upload: bool, pick: str | None = None, prepare: bool = False) -> int:
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
        from . import diagnosis
        pack = diagnosis.add(pack)
    else:
        from .scout import scout
        pack = scout(cfg)

    pack["history"] = history.menu()
    if not dry_run:
        from . import press
        cached = read_json(CACHE / f"{slugify(str(pack['fixture_id']))}.json", {})
        if cached.get("press") is not None:
            log.info("Using saved press/context research for this match (no new web search).")
            pack["press"], pack["context"] = cached["press"], cached.get("context", {})
        else:
            pack["press"] = press.gather(cfg, pack)
            from . import context
            pack["context"] = context.gather(cfg, pack)
            write_json(CACHE / f"{slugify(str(pack['fixture_id']))}.json",
                       {**cached, "saved": now(), "press": pack["press"], "context": pack["context"]})
        # what the papers said: search once, screenshot once (free pages), keep for prepare and render
        cache_path = CACHE / f"{slugify(str(pack['fixture_id']))}.json"
        cached = read_json(cache_path, {})
        if "reviews" in cached:
            pack["reviews"] = cached["reviews"]
            if any(r.get("kind") == "pending" for r in pack["reviews"]):     # retake marked screenshots only
                from . import clippings
                pend = [r for r in pack["reviews"] if r.get("kind") == "pending"]
                shot = clippings.capture(pend, CACHE / "press" / slugify(str(pack["fixture_id"])),
                                         first=1 + pack["reviews"].index(pend[0]))
                done = {r["url"]: r for r in shot}
                pack["reviews"] = [done.get(r["url"], r) if r.get("kind") == "pending" else r
                                   for r in pack["reviews"] if r.get("kind") != "pending" or r["url"] in done]
                write_json(cache_path, {**read_json(cache_path, {}), "reviews": pack["reviews"]})
        else:
            from . import clippings
            found = press.reviews(cfg, pack)
            pack["reviews"] = clippings.capture(found, CACHE / "press" / slugify(str(pack["fixture_id"])))
            write_json(cache_path, {**read_json(cache_path, {}), "reviews": pack["reviews"]})
    workdir = OUT_DIR / f"{date.today():%Y%m%d}-{slugify(pack['home'] + '-' + pack['away'])}"
    workdir.mkdir(parents=True, exist_ok=True)
    if not dry_run and cfg.get("photos", {}).get("enabled", True):
        from . import photos
        found = photos.find(photos.people_in(pack), workdir / "photos")
        pack["photos"] = [{k: v for k, v in ph.items() if k != "path"} for ph in found]
    write_json(workdir / "datapack.json", pack)

    cache_file = CACHE / f"{slugify(str(pack['fixture_id']))}.json"
    cached = read_json(cache_file, {}) if not dry_run else {}
    if cached.get("script") and not os.environ.get("NEW_SCRIPT"):
        log.info("Using the saved, fact-checked script for this match (set NEW_SCRIPT=1 to write a new one).")
        script, report = cached["script"], cached["report"]
        if cached.get("edited"):       # the owner changed the draft: check the new words again
            for sc in script["scenes"]:     # narration is always the shot texts, in order
                if sc.get("shots"):
                    sc["narration"] = " ".join((sh.get("text") or "").strip() for sh in sc["shots"]).strip()
            report = factcheck.check(cfg, script, pack, use_ai=bool(secret("ANTHROPIC_API_KEY")))
            sh_list = cached.get("shorts") or []
            if report["ok"] and sh_list:
                for x in sh_list:
                    if x.get("shots"):
                        x["narration"] = " ".join((h.get("text") or "").strip() for h in x["shots"]).strip()
                sr = factcheck.check(cfg, shorts._as_script(sh_list), pack, use_ai=bool(secret("ANTHROPIC_API_KEY")))
                if not sr["ok"]:
                    report = {"ok": False, "problems": ["Short: " + p for p in sr["problems"]]}
            if report["ok"]:
                cached = {**cached, "script": script, "report": report, "shorts": sh_list, "edited": False}
                write_json(cache_file, cached)
                log.info("Edited draft passed the fact-check again.")
            else:
                raise StopPipeline("Your edits failed the fact-check:\n- " + "\n- ".join(report["problems"][:10]))
    else:
        script, report = get_script(cfg, pack, use_ai=bool(secret("ANTHROPIC_API_KEY")))
        if not dry_run and report.get("ok"):
            write_json(cache_file, {**cached, "script": script, "report": report, "saved_script": now()})
    write_json(workdir / "script.json", script)
    write_json(workdir / "factcheck.json", report)
    if not report["ok"]:
        raise StopPipeline("Script failed fact-checking after retries:\n- " +
                           "\n- ".join(report["problems"][:10]))

    if not prepare and not dry_run and cfg.get("photos", {}).get("enabled", True):
        # name tags: a photo for every player or coach the story names (free licence only)
        from . import nametags, photos
        texts = [sc["narration"] for sc in script["scenes"]] + [x["narration"] for x in cached.get("shorts") or []]
        have = {ph["name"] for ph in pack.get("photos") or []}
        need = [{k: p[k] for k in ("name", "role", "team")} for p in nametags.mentioned(texts, nametags.roster(pack))
                if p["name"] not in have]
        if need:
            more = photos.find(need, workdir / "photos", limit=16, start=len(pack.get("photos") or []))
            pack["photos"] = (pack.get("photos") or []) + [{k: v for k, v in ph.items() if k != "path"} for ph in more]
            write_json(workdir / "datapack.json", pack)
            log.info("Name tags: %d of %d named people have a free photo.", len(more), len(need))

    if prepare:   # stop before the voice: the producer task makes it (Everygen) and starts the render
        prepared = cached.get("shorts") or shorts.prepare(cfg, pack, script)
        if prepared:
            write_json(cache_file, {**read_json(cache_file, {}), "shorts": prepared})
        items = ([{"key": f"scene_{sc['id']:02d}", "text": sc["narration"]} for sc in script["scenes"]]
                 + [{"key": f"short_{x['id']}", "text": x["narration"]} for x in prepared])
        write_json(DASH / "voice_needed.json", {
            "updated": now(), "fixture_id": pack["fixture_id"], "match": pick,
            "slug": slugify(str(pack["fixture_id"])), "home": pack["home"], "away": pack["away"],
            "voice": cfg["voice"].get("everygen_voice", "alex"), "items": items,
            "characters": sum(len(i["text"]) for i in items)})
        write_draft(pack, script, prepared, cfg)
        notify.send(f"Draft script ready for {pack['home']} vs {pack['away']}: please read and approve.")
        log.info("Prepared: %d voice parts written to data/dashboard/voice_needed.json", len(items))
        return 0

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
    srt = render.captions(script, durs, workdir / "captions.srt", workdir=workdir)
    thumb_paths = thumbs.render(script, pack, workdir)
    credits = []
    used = {(v or {}).get("photo") for sc in script["scenes"] for v in
            [sh.get("visual") for sh in sc.get("shots") or []] + [sc.get("visual")]}
    if pack.get("reviews"):
        script["description"] = script["description"].rstrip() + "\n\nWhat the papers said:\n" + "\n".join(
            f"- {r['outlet']}{', ' + r['author'] if r.get('author') else ''}: {r['url']}" for r in pack["reviews"])
    from . import nametags
    named = {p["name"] for p in nametags.mentioned([sc["narration"] for sc in script["scenes"]], nametags.roster(pack))}
    for ph in pack.get("photos") or []:
        if ph["name"] in used or ph["name"] in named or ph.get("role", "").startswith("Stadium"):
            credits.append(f"Photo of {ph['name']}: {ph['author']}, {ph['licence']}, via {ph.get('via', 'Wikimedia Commons')} ({ph['page']})")
    for q in pack.get("press") or []:
        credits.append(f"{q['speaker']} quote: {q.get('source') or ''} {q['url']}".strip())
    if credits:
        script["description"] = script["description"].rstrip() + "\n\nSources and credits:\n" + "\n".join(credits)
    made_shorts = (shorts.make(cfg, pack, script, workdir, placeholder=dry_run and not secret("ELEVENLABS_API_KEY"),
                               preset=None if os.environ.get("NEW_SCRIPT") else cached.get("shorts"))
                   if secret("ANTHROPIC_API_KEY") else [])
    if made_shorts and not dry_run:
        write_json(cache_file, {**read_json(cache_file, {}), "shorts": [m["short"] for m in made_shorts]})
    minutes = sum(durs) / 60

    meta = {"titles": script["title_options"], "description": script["description"],
            "tags": script.get("tags", []), "minutes": round(minutes, 1),
            "fixture_id": pack["fixture_id"]}
    write_json(workdir / "metadata.json", meta)

    result = {"updated": now(), "home": pack["home"], "away": pack["away"],
              "competition": pack["competition"], "fixture_id": pack["fixture_id"],
              "titles": script["title_options"], "minutes": round(minutes, 1),
              "files": workdir.name, "uploaded": False, "youtube": None,
              "critic": report.get("critic"), "rewritten": bool(report.get("rewritten")),
              "shorts": [{"title": m["short"]["title"], "hook": m["short"]["hook"],
                          "format": m["short"].get("format"), "youtube": None,
                          "suggested_publish": str(date.today() + timedelta(days=i + 1))}
                         for i, m in enumerate(made_shorts)]}
    result["voice"] = voice.provider_used(workdir)
    has_voice = result["voice"] != "silent"
    if upload and not dry_run and not has_voice:
        notify.send(f"Video made with silent audio (no voice keys yet), so it was NOT uploaded. "
                    f"Files: {workdir.name}")
        upload = False
    if upload and not dry_run:
        from .publish import upload as yt_upload
        vid = yt_upload(cfg, script, video, srt, thumb_paths)
        covered = read_json(DATA_DIR / "history.json", {"fixtures": []})
        covered["fixtures"].append(pack["fixture_id"])
        write_json(DATA_DIR / "history.json", covered)
        result.update(uploaded=True, youtube=f"https://studio.youtube.com/video/{vid}/edit")
        from .publish import upload_short
        for m, row in zip(made_shorts, result["shorts"]):
            try:
                sid = upload_short(cfg, m["short"], m["video"], vid)
                row["youtube"] = f"https://studio.youtube.com/video/{sid}/edit"
            except Exception as e:  # a failed short never undoes the main upload
                log.warning("Short upload failed: %s", e)
        notify.send(
            f"New video ready for review ({minutes:.1f} min): {pack['home']} vs {pack['away']}\n\n"
            f"Title: {script['title_options'][0]}\n"
            f"Other titles to A/B test: {' | '.join(script['title_options'][1:])}\n\n"
            f"Review, then set to Public or Scheduled:\nhttps://studio.youtube.com/video/{vid}/edit"
            + "".join(f"\nShort ({r['format']}), publish {r['suggested_publish']}: {r['youtube']}"
                      for r in result["shorts"] if r["youtube"]))
    else:
        notify.send(f"Test run finished ({minutes:.1f} min). Files: {workdir.name}")
    if not dry_run:
        write_json(DASH / "last_video.json", result)
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
    p.add_argument("--data-only", action="store_true")
    p.add_argument("--prepare", action="store_true", help="data + research + scripts, stop before the voice")
    args = p.parse_args()
    try:
        if args.list:
            sys.exit(show_list())
        if args.data_only:
            sys.exit(show_data(args.pick or None))
        sys.exit(run(dry_run=args.dry_run, upload=not args.no_upload, pick=args.pick or None,
                     prepare=args.prepare))
    except StopPipeline as e:
        log.error("Stopped: %s", e)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "stop_reason.txt").write_text(str(e), encoding="utf-8")
        notify.send(f"Pipeline stopped, nothing was published.\n\nReason: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
