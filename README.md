# Football channel pipeline (v1)

Twice a week, in the cloud, this project:

1. **Scout** – finds the most interesting finished match (Algeria's matches get a bonus).
2. **Writer** – Claude writes a 9-scene script (Match Lens structure) using only numbers from the match data.
3. **Fact-checker** – code checks every number against the data; a second AI pass checks every claim.
   Any problem = the run stops and you get an alert. Nothing is published.
4. **Visuals** – renders score, stat bars, timeline, formations, key numbers, lesson cards.
5. **Voice** – narrates each scene with your cloned voice (ElevenLabs).
6. **Editor** – builds a 1080p MP4 with a slow camera push, optional music and captions.
7. **Publisher** – uploads it to YouTube as **private**, with captions and thumbnail.
8. **Alert** – sends you a Telegram message with the review link and 3 title options.

You then open the link, watch, and set the video to Public or Scheduled. That tap is required:
YouTube keeps API uploads private until the project passes Google's audit, and it keeps a human in
charge, which protects monetisation.

## One-time setup (about 1 hour)

### 1. GitHub
1. Create a free account at github.com.
2. Create a **private** repository and upload all files from this folder.
3. Settings → Secrets and variables → Actions → add the secrets below.

### 2. Secrets to add

| Secret | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API keys |
| `ELEVENLABS_API_KEY` | elevenlabs.io → Profile → API key (Creator plan for ~100 min/month) |
| `ELEVENLABS_VOICE_ID` | Record 2–3 minutes of your voice → Voices → Instant clone → copy the voice ID |
| `FOOTBALL_DATA_KEY` | football-data.org/client/register (free; the key arrives by email) |
| `API_FOOTBALL_KEY` | Optional. dashboard.api-football.com: only useful on the paid Pro plan, which covers the current season |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | Run `scripts/get_youtube_token.py` once on your computer (instructions inside the file) |
| `TELEGRAM_BOT_TOKEN` | In Telegram, message @BotFather → /newbot |
| `TELEGRAM_CHAT_ID` | Message your new bot once, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id` |

### 3. YouTube channel
- Verify the channel by phone (needed for custom thumbnails).
- Turn on "advanced features" in YouTube Studio (needed for A/B testing titles and thumbnails).

### 4. Music (optional)
Download 3–5 "no attribution required" tracks from the YouTube Audio Library into `assets/music/`.

## Test it, step by step
In GitHub → Actions → **Produce video** → Run workflow:

1. `dry-run` – fictional sample match, silent audio. Checks that the cloud setup works.
2. `no-upload` – a real match, real script and voice, no upload. Download the video from the run's
   "video-files" and watch it.
3. `full` – the real thing. Arrives in YouTube Studio as private.

After that, it runs by itself every Monday and Thursday at 07:17 Algeria time.

## Settings
Everything you'd want to change is in `config.yaml`: channel name, competitions, Algeria bonus,
video length, banned topics.

## Known limits of v1
- Videos are **data-led** (about 5–6 minutes): score, stats, timeline, formations. No player-movement
  animations yet: the free data has no tracking.
- English only. Arabic/French: turn on YouTube auto-dubbing in Studio for now; own-voice tracks come in v2.
- No Shorts yet (v2).
- API-Football's free plan may not allow the current season for every competition. If the alert says
  "season not allowed", either upgrade to Pro ($19/month) or remove that competition from `config.yaml`.
- A private repository gets a limited number of free GitHub Actions minutes per month; one run takes
  about 5–10 minutes, so two runs a week fit easily.

## Files
- `pipeline/` – the code (one file per step)
- `samples/` – the fictional test match
- `data/history.json` – matches already covered (updated automatically)
- `out/` – created during a run (video, script, fact-check report, thumbnails)

## History lens (StatsBomb open data)

`data/history_lens.json` holds per-match numbers for famous teams (Leverkusen 2023/24, Leicester 2015/16,
Arsenal 2003/04, Barcelona 2010/11, Argentina and Morocco at the 2022 World Cup, Spain at Euro 2024,
Côte d'Ivoire at AFCON 2023), built from StatsBomb's free open data with mplsoccer.
The writer may use one of them in one scene for a brief comparison, and the fact-checker allows only
those numbers. To add a team, edit `LENSES` in `scripts/build_history_lens.py` and run it again.

## Thumbnails

`pipeline/thumbs.py` makes three styles for YouTube Test & Compare: the real shot map (when Understat
has the match), a big-number card, and a team split. Font: Anton (SIL Open Font License).
