"""Coach story and the institution's bet: the bigger story around a match.

For each team: who the coach is, when and why he was appointed (what the club or federation said it
wanted), who he replaced, what he promised, his key choices since (selections, style), each with a
source link. One web-search call per video. Never raises: no context means a match-only story.
"""
from .common import log, secret
from .press import web_research

SYSTEM = """You research the bigger story around a football match for a fact-checked documentary video.
For EACH of the two teams, find from reliable sources (federation/club sites, major outlets, wire agencies):
- the head coach, the date he was appointed, and who he replaced (and why that coach left);
- what the club or federation said it wanted when it appointed him (style, identity, rebuilding...):
  short word-for-word quote under 25 words, with speaker and source;
- what the coach promised at his presentation (short quote, source);
- his key decisions since (squad selection, young players, dropped players, captaincy, style), each
  as one factual sentence with a source;
- any striking link worth a story (e.g. he replaced the same coach before at another club), only if
  reported by a source.
Rules: facts only, each with a URL. No rumours, transfers, betting, politics, private life.
If something is not found, leave it out rather than guessing.
Return ONLY JSON: {"teams": [{"team": str, "coach": str, "appointed": str, "replaced": str,
"replaced_reason": str, "institution_quote": {"quote": str, "speaker": str, "source": str, "url": str},
"coach_promise": {"quote": str, "source": str, "url": str},
"key_choices": [{"text": str, "source": str, "url": str}],
"links": [{"text": str, "source": str, "url": str}]}]}"""


def gather(cfg: dict, pack: dict) -> dict:
    if not cfg.get("context", {}).get("enabled", True) or not secret("ANTHROPIC_API_KEY"):
        return {}
    f = {x["id"]: x["value"] for x in pack["facts"]}
    user = (f"Match: {pack['home']} vs {pack['away']}, {pack['competition']}, played {f.get('date', '')}. "
            f"Coaches named in the line-ups: {f.get('home_coach', 'unknown')} ({pack['home']}), "
            f"{f.get('away_coach', 'unknown')} ({pack['away']}).")
    try:
        data = web_research(cfg, SYSTEM, user, max_uses=10)
        teams = [t for t in data.get("teams", []) if t.get("coach")]
        log.info("Context: coach stories for %d teams", len(teams))
        return {"teams": teams} if teams else {}
    except Exception as e:
        log.warning("Coach context skipped: %s", e)
        return {}
