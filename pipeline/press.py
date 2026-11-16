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
