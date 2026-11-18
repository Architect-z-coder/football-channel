"""Press context: what the coaches and players said after the match (tactics, plans, explanations).

Claude searches the web for post-match press-conference and interview reports, and returns short
quotes with their source links. Rules: only things actually reported after this match, each with a
source URL; quotes under 25 words; no rumours, transfers, injuries speculation, politics or private
life. Never raises: if nothing reliable is found, the video is made from the data alone.
"""
import json

from .common import log, secret
from .llm import parse_json

SYSTEM = """You research what was said after a football match, for a fact-checked analysis video.
Search the web for reports of the post-match press conferences and interviews of this exact match.
Collect, for this exact match:
- BEFORE the match (pre-match press conference, team news): what each head coach said about the plan,
  selection choices and confirmed absences (injured or suspended players);
- AFTER the match: what each head coach said about tactics, the game plan, changes, why the result
  happened; notable things players said about the match itself.
Rules: only statements about THIS match, by reliable outlets (club/federation sites,
major news, wire agencies). Each item needs the source URL and the speaker's name and role. Quotes
must be under 25 words, word for word as reported; otherwise give a short paraphrase marked as such.
Skip rumours, transfers, injury speculation, politics, betting and private life.
If you find nothing reliable, return an empty list.
Return ONLY JSON: {"items": [{"speaker": str, "role": str, "team": str, "quote": str,
"is_paraphrase": bool, "when": "before|after", "topic": "tactics|selection|absence|result|player|other", "source": str, "url": str}]}"""


def gather(cfg: dict, pack: dict) -> list[dict]:
    if not cfg.get("press", {}).get("enabled", True) or not secret("ANTHROPIC_API_KEY"):
        return []
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=secret("ANTHROPIC_API_KEY", required=True))
        date = next((f["value"] for f in pack["facts"] if f["id"] == "date"), "")
        user = (f"Match: {pack['home']} vs {pack['away']}, {pack['competition']}, played {date}. "
                f"Final score {pack['home']} "
                f"{next(f['value'] for f in pack['facts'] if f['id'] == 'score_home')}-"
                f"{next(f['value'] for f in pack['facts'] if f['id'] == 'score_away')} {pack['away']}.")
        msg = client.messages.create(
            model=cfg["writer"]["model"], max_tokens=4000, system=SYSTEM,
            messages=[{"role": "user", "content": user}],
            tools=[{"type": cfg.get("press", {}).get("tool", "web_search_20250305"),
                    "name": "web_search", "max_uses": 8}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        try:
            data = parse_json(text)
        except Exception:   # web-search replies sometimes break JSON (stray quotes): ask for a clean copy
            from .llm import ask_json
            data = ask_json(cfg["writer"]["model"], "Return the same data as valid JSON only, same keys. "
                            "Escape quotes inside strings.", text, max_tokens=4000)
        items = [i for i in data.get("items", []) if i.get("url") and i.get("quote")]
        for i in items:
            if not i.get("is_paraphrase") and len(i["quote"].split()) > 25:
                i["quote"] = " ".join(i["quote"].split()[:25]) + "..."
        log.info("Press: %d statements found", len(items))
        return items[:10]
    except Exception as e:
        log.warning("Press context skipped: %s", e)
        return []


def web_research(cfg: dict, system: str, user: str, max_uses: int = 8) -> dict:
    """One Claude call with web search; returns parsed JSON (repairing it once if needed)."""
    import anthropic
    client = anthropic.Anthropic(api_key=secret("ANTHROPIC_API_KEY", required=True))
    msg = client.messages.create(
        model=cfg["writer"]["model"], max_tokens=5000, system=system,
        messages=[{"role": "user", "content": user}],
        tools=[{"type": cfg.get("press", {}).get("tool", "web_search_20250305"),
                "name": "web_search", "max_uses": max_uses}])
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    try:
        return parse_json(text)
    except Exception:
        from .llm import ask_json
        return ask_json(cfg["writer"]["model"], "Return the same data as valid JSON only, same keys. "
                        "Escape quotes inside strings.", text, max_tokens=5000)


# ---------------- what the papers said ----------------
OUTLETS = ["The Guardian", "The Athletic", "BBC Sport", "ESPN", "The Times", "The Independent",
           "The Telegraph", "Reuters", "AP", "Kicker", "Süddeutsche Zeitung", "FAZ", "Der Spiegel",
           "NOS", "De Telegraaf", "Algemeen Dagblad", "Voetbal International", "L'Équipe", "Le Monde",
           "Marca", "AS", "El País", "Mundo Deportivo", "La Gazzetta dello Sport", "Corriere dello Sport",
           "A Bola", "Record", "Olé", "New York Times"]

REVIEW_SYSTEM = """You find what respected newspapers and named football journalists wrote about ONE match,
for a fact-checked analysis video that will show a cut of each article on screen.
Search the web for match reports, analysis pieces and columns about this exact match, published after it,
by these outlets (others of the same standing are fine): {outlets}.
For each article (at most 5, different outlets, prefer ones with a named writer and a clear opinion):
- outlet, author (the byline, "" if none), date (YYYY-MM-DD), url (the article page itself), headline (as published),
- quote: ONE sentence copied WORD FOR WORD from the article body that carries the writer's judgement of the match
  (tactics, a player, a coach's decision, the meaning of the result). 8 to 30 words. Keep the original language;
- quote_en: an English translation if the quote is not in English, else "";
- point: the writer's main view in one plain English sentence, in your own words;
- free: true if the article looked readable without a subscription, false if it is paywalled, null if unsure.
Rules: only articles about THIS match; no rumours, transfers, betting, politics, private lives, injury speculation.
If you are not sure a sentence is word for word, leave that article out. If you find nothing reliable, return [].
Return ONLY JSON: {{"reviews": [{{"outlet", "author", "date", "url", "headline", "quote", "quote_en", "point", "free"}}]}}"""


def reviews(cfg: dict, pack: dict) -> list[dict]:
    if not cfg.get("press", {}).get("reviews", True) or not secret("ANTHROPIC_API_KEY"):
        return []
    try:
        f = {x["id"]: x["value"] for x in pack["facts"]}
        user = (f"Match: {pack['home']} {f.get('score_home')}-{f.get('score_away')} {pack['away']}, "
                f"{pack['competition']}, played {f.get('date', '')}.")
        data = web_research(cfg, REVIEW_SYSTEM.format(outlets=", ".join(OUTLETS)), user, max_uses=10)
        out = []
        for r in data.get("reviews", []):
            if r.get("url", "").startswith("http") and r.get("quote") and r.get("outlet"):
                if len(r["quote"].split()) > 40:
                    continue
                out.append(r)
        log.info("Press reviews: %d articles found", len(out))
        return out[:5]
    except Exception as e:
        log.warning("Press reviews skipped: %s", e)
        return []
