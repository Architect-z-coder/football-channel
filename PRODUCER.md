# Producer task (runs as a scheduled Claude task, Monday and Thursday)

The producer is Claude, running on a schedule with the owner's connected tools (Everygen voice).
GitHub does the heavy work (data, research, script, render); the producer adds the paid tools.

## Steps (one match per run)
1. Clone or pull `Architect-z-coder/football-channel` (git identity: Architect-z-coder,
   177468583+Architect-z-coder@users.noreply.github.com).
2. Match: the first non-comment line of `data/queue.txt`. Empty queue -> notify the owner and stop.
3. **Prepare on GitHub:** write `data/dashboard/request.json`
   `{"id": "<unique>", "mode": "prepare", "match": "<line>", "look_back_days": ""}`, commit, push.
   Poll `data/dashboard/status.json` (git pull every 20 s, max 15 min) until `request_id` matches and
   `state` is `done` or `failed`. Failed -> report the reason and stop.
4. **Draft for the owner (stop here):** the prepare run wrote `data/review/<slug>.md`. Publish it as a
   Claude Doc (Claude_Docs connector; title "Draft: <home> vs <away>") so the owner can read it on his
   phone; if that fails, send the markdown as a message. Then end your turn with one line:
   "Draft ready: reply approve, or tell me what to change." Do not voice or render anything yet.
5. **When the owner replies:**
   - **Changes:** edit the script in `data/cache/<slug>.json` (`script.scenes[].shots[].text`; for a
     Short, `shorts[].shots[].text`). Change only what he asked, keep every fact and number exactly as in
     the data pack (never invent one), and set `"edited": true` at the top level. Commit, then run
     prepare again as in step 3 (it re-runs the fact-check on the edited words and rewrites the draft).
     If the fact-check fails, tell him why and suggest a fix. Show the new draft and wait again.
   - **Approve:** continue with step 6.
6. **Voice with Everygen:** read `data/dashboard/voice_needed.json`. Check the Everygen balance; it must be
   at least the number of items + 5, otherwise stop and tell the owner. For each item, call
   `generate_voiceover_batch` (up to 12 lines per call, one locked voice) with each item's exact `text`
   and `voiceId` = the file's `voice`.
   Save `data/voice/<slug>.json`:
   `{"fixture_id": ..., "provider": "everygen", "items": [{"key", "text", "url": audioUrl, "voice": "<voice>",
   "duration": durationSeconds, "starts": [start of each word, in order]}]}`.
   The number of starts must equal the number of words in `text` (split on spaces); check before committing.
   Never change the text. One call per item, no retries of a call that succeeded.
6b. **Match music:** make one original instrumental for this match with Everygen `generate_audio`
   (model lyria-3.5): instrumental only, completely original melody (never quote or imitate a real song,
   club anthem or chant), restrained and steady under a narrator, ~95 BPM, coloured by the two clubs'
   or countries' musical character (e.g. Bavarian brass + stadium-chant rhythm; Cologne carnival).
   Add it to config.yaml music.tracks as `{name: <slug>, kind: main, fixture: "<fixture_id>", url: <audioUrl>}`.
7. **Render on GitHub:** if `youtube.upload_ready` in config.yaml is true, use `"mode": "full"` (uploads as
   PRIVATE); otherwise `"mode": "no-upload"` (files only, kept 14 days on the run page). Same match; commit
   the manifest and request.json, push; poll status (max 25 min). After a successful no-upload run, remove
   that match line from data/queue.txt yourself and push (a full run removes it on its own).
8. Report: titles, length, YouTube Studio links and the suggested publish days of the two Shorts
   (from `data/dashboard/last_video.json`), or the failure reason.

## Rules
- Never publish anything publicly; uploads are private for the owner to approve.
- One prepare per round (again only after the owner asks for changes), and one render, only after he approves.
- If any step fails, stop and report; never loop or start a second attempt on your own.
