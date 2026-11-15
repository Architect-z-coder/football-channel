"""Writer: turns a data pack into a scene-by-scene script (the Match Lens structure)."""
import json

from .llm import ask_json

VISUAL_TYPES = """
Allowed visual types (use only these; the renderer supports nothing else):
- {"type": "title_card", "title": str, "subtitle": str}
- {"type": "scoreline"}                         -> final score from the data pack
- {"type": "stat_bars", "stats": [str, ...]}    -> 2-5 stat keys WITHOUT the home_/away_ prefix,
                                                   e.g. "ball_possession", "total_shots", "shots_on_goal",
                                                   "expected_goals", "passes_pct", "corner_kicks".
                                                   Only keys that exist for both teams in the pack.
- {"type": "key_number", "value": str, "label": str}  -> one big number taken from the pack
- {"type": "halftime_fulltime"}                 -> half-time score, then full-time score
- {"type": "table_snapshot"}                    -> both teams' league position, points, W-D-L, goals
                                                   (only if the pack has home_position / away_position)
- {"type": "form_compare"}                      -> both teams' record in their previous 5 matches
                                                   (only if the pack has *_last5_* facts)
- {"type": "events_timeline"}                   -> goals and red cards on a 90-minute line
                                                   (only if the pack has event_ facts)
- {"type": "formations"}                        -> both formations on a pitch
                                                   (only if the pack has *_formation facts)
- {"type": "text_card", "heading": str, "lines": [str, ...]}  -> max 3 short lines
- {"type": "lesson_list", "items": [str, str, str]}
"""

SYSTEM = f"""You write scripts for a faceless YouTube channel that explains modern football clearly.
Voice: plain, confident English, short sentences, no hype, no clickbait. A teacher who loves the game.

HARD RULES
1. Closed book: every number, name, minute and result you state must come from the data pack.
   Never use outside knowledge for facts. If the pack does not support a point, leave it out.
2. Analysis is allowed, but phrase it as reading of the numbers ("the numbers suggest", "that points to"),
   never as a claim about what happened on the pitch that the data cannot show.
3. Never mention: politics, transfer rumours, betting or odds, injury speculation, private lives.
4. Spell numbers as digits in narration (e.g. "62 percent", "14 shots") so they can be checked.
5. Structure (Match Lens): hook (one striking fact + a question), promise (3 keys named), the picture
   (scoreline and shapes), key 1, key 2, key 3 (each: claim, number, why it matters, one-line recap),
   the lesson (what a player or coach can learn), close (answer the question, then invite viewers to
   the next breakdown). Put a short subscribe line at the end of key 1.
6. Each scene: 20-60 words of narration. Change the visual every scene.
7. For each scene list the fact ids you used in "fact_ids".
{VISUAL_TYPES}
Return ONLY JSON with this shape:
{{
  "title_options": [str, str, str],          // under 70 characters, accurate, curiosity without lying
  "thumbnail_texts": [str, str, str],        // 2-4 words each
  "description": str,                        // 2 short paragraphs + a "Data: <source>." line
  "tags": [str, ...],
  "scenes": [{{"id": int, "beat": str, "visual": {{...}}, "on_screen": str, "narration": str,
              "fact_ids": [str, ...]}}]
}}"""


def write_script(cfg: dict, pack: dict, feedback: str | None = None) -> dict:
    target_words = cfg["writer"]["target_minutes"] * cfg["writer"]["words_per_minute"]
    user = (
        f"Channel: {cfg['channel']['name']} - {cfg['channel']['tagline']}\n"
        f"Target length: about {target_words} words of narration in total.\n\n"
        f"DATA PACK:\n{json.dumps(pack, ensure_ascii=False)}\n"
    )
    if feedback:
        user += f"\nYour previous draft failed fact-checking. Fix these problems:\n{feedback}\n"
    return ask_json(cfg["writer"]["model"], SYSTEM, user)
