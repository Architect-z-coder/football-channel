"""Name tags: when a player or coach is first named in the narration, a small round photo with his
name and team appears on screen, timed to the spoken word. Photos are free-licence only (Wikimedia
Commons / Openverse via photos.py) and credited; with no free photo the tag shows the name alone."""
import re
import unicodedata

FPS = 30
TAG_FRAMES = 90           # 3 s on screen
REPEAT_AFTER_S = 60       # name the same person again only after a minute


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", re.sub(r"'s$|’s$", "", s))


def roster(pack: dict) -> list[dict]:
    """Everyone who can be named: players who played, missing players, the two coaches."""
    f = {x["id"]: x["value"] for x in pack.get("facts", [])}
    people, seen = [], set()

    def add(name, team, role, rating=None):
        if name and name not in seen:
            seen.add(name)
            people.append({"name": name, "team": team or "", "role": role, "rating": rating})

    for side in ("home", "away"):
        add(f.get(f"{side}_coach"), pack.get(side), "Head coach")
    for r in pack.get("ratings") or []:
        add(r.get("player"), r.get("team"), "Player", r.get("rating"))
    for side, lu in (pack.get("lineups") or {}).items():
        for m in lu.get("missing", []):
            add(m.get("player"), lu.get("team"), "Missing")
    for k, v in f.items():
        if k.startswith("goal_") and isinstance(v, dict):
            add(v.get("player"), v.get("team"), "Player")
    # keys to look for in the words: the full surname (last word) and, if unique, the first name
    lasts = {}
    for p in people:
        lasts.setdefault(_norm(p["name"].split()[-1]), []).append(p)
    for p in people:
        last = _norm(p["name"].split()[-1])
        p["keys"] = [last] if len(last) >= 4 and len(lasts[last]) == 1 else []
        first = _norm(p["name"].split()[0])
        if p["role"] == "Head coach" and len(first) >= 4 and len(p["name"].split()) > 1:
            p["keys"].append(first)                 # coaches are often called by first name (Xavi)
        if len(p["name"].split()) == 1:
            p["keys"] = [_norm(p["name"])]
    return [p for p in people if p["keys"]]


def mentioned(texts: list[str], people: list[dict]) -> list[dict]:
    words = {_norm(w) for t in texts for w in t.split()}
    return [p for p in people if any(k in words for k in p["keys"])]


def photo_of(pack: dict, name: str) -> dict | None:
    return next((ph for ph in pack.get("photos") or [] if ph.get("name") == name), None)


def tags_for(pack: dict, scenes: list[dict], shown: dict | None = None) -> list[list[dict]]:
    """scenes: [{"narration", "word_starts" (seconds or None), "frames", "offset_s"}].
    Returns one list of tags per scene: {from, name, team, role, file, credit}."""
    people = roster(pack)
    shown = {} if shown is None else shown          # name -> last time shown (s, whole video)
    out = []
    for sc in scenes:
        tokens = sc["narration"].split()
        starts = sc.get("word_starts")
        if not starts or len(starts) != len(tokens):
            n = max(1, len(tokens))
            starts = [i / n * (sc["frames"] / FPS) for i in range(n)]
        tags, busy_until = [], -1
        for i, w in enumerate(tokens):
            key = _norm(w)
            p = next((p for p in people if key in p["keys"]), None)
            if not p:
                continue
            t = starts[i]
            whole = sc.get("offset_s", 0) + t
            if p["name"] in shown and whole - shown[p["name"]] < REPEAT_AFTER_S:
                continue
            frm = int(t * FPS)
            if frm < busy_until or frm + 40 > sc["frames"]:
                continue
            ph = photo_of(pack, p["name"])
            tags.append({"from": frm, "name": p["name"], "team": p["team"], "role": p["role"],
                         "file": ph["file"] if ph else None,
                         "face": ph.get("face") if ph else None,
                         "credit": f"{ph.get('author') or 'Unknown'}, {ph.get('licence')}" if ph else ""})
            shown[p["name"]] = whole
            busy_until = frm + TAG_FRAMES
        out.append(tags)
    return out
