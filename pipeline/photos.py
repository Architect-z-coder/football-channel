"""Real photos of the people in the story (coaches, key players, absentees) from Wikimedia Commons.

Only freely licensed images (public domain, CC0, CC BY, CC BY-SA) are used, found through each
person's Wikidata portrait (P18). Every photo is shown with its author and licence on screen, and
listed in the video description. Match/press-agency photos (Getty, Reuters, AP...) are never used.
Never raises: no photo means the scene simply uses graphics.
"""
from pathlib import Path

import requests

from .common import log

HEAD = {"User-Agent": "TheOtherTouchline/1.0 (football analysis channel; contact via GitHub)"}
OK_LICENCES = ("public domain", "pd", "cc0", "cc by", "cc-by")


def _wikidata_image(name: str) -> str | None:
    r = requests.get("https://www.wikidata.org/w/api.php", headers=HEAD, timeout=20, params={
        "action": "wbsearchentities", "search": name, "language": "en", "type": "item",
        "limit": 5, "format": "json"})
    for hit in r.json().get("search", []):
        desc = (hit.get("description") or "").lower()
        if not any(w in desc for w in ("football", "soccer", "coach", "manager")):
            continue
        e = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{hit['id']}.json",
                         headers=HEAD, timeout=20).json()
        claims = e["entities"][hit["id"]].get("claims", {}).get("P18") or []
        if claims:
            return claims[0]["mainsnak"]["datavalue"]["value"]
    return None


def _commons_info(filename: str) -> dict | None:
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=HEAD, timeout=20, params={
        "action": "query", "titles": f"File:{filename}", "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": 900, "format": "json"})
    page = next(iter(r.json()["query"]["pages"].values()))
    info = (page.get("imageinfo") or [None])[0]
    if not info:
        return None
    meta = info.get("extmetadata", {})
    lic = (meta.get("LicenseShortName", {}).get("value") or "").strip()
    if not lic.lower().startswith(OK_LICENCES):
        return None
    import re
    artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value") or "unknown").strip()
    return {"url": info.get("thumburl") or info["url"], "page": info.get("descriptionurl"),
            "licence": lic, "author": artist[:60]}


def find(people: list[dict], outdir: Path, limit: int = 6) -> list[dict]:
    """people: [{"name", "role", "team"}]. Returns photos saved in outdir with credits."""
    out, seen = [], set()
    outdir.mkdir(parents=True, exist_ok=True)
    for p in people:
        if len(out) >= limit or not p.get("name") or p["name"] in seen:
            continue
        seen.add(p["name"])
        try:
            fn = _wikidata_image(p["name"])
            info = _commons_info(fn) if fn else None
            if not info:
                continue
            ext = Path(info["url"]).suffix.lower() or ".jpg"
            dest = outdir / f"photo_{len(out) + 1}{ext if ext in ('.jpg', '.jpeg', '.png', '.webp') else '.jpg'}"
            dest.write_bytes(requests.get(info["url"], headers=HEAD, timeout=30).content)
            out.append({**p, "file": dest.name, "path": str(dest), **info})
        except Exception as e:
            log.info("No photo for %s (%s)", p["name"], e)
    log.info("Photos: %d free-licence photos found (Wikimedia Commons)", len(out))
    return out


def people_in(pack: dict) -> list[dict]:
    """Who the story is about: coaches, top and bottom rated starters, key absentees."""
    f = {x["id"]: x["value"] for x in pack["facts"]}
    ppl = []
    for side in ("home", "away"):
        team = pack[side]
        if f.get(f"{side}_coach"):
            ppl.append({"name": f[f"{side}_coach"], "role": "Head coach", "team": team})
    for k in ("best_player_1", "best_player_2", "worst_player_1"):
        if isinstance(f.get(k), dict):
            ppl.append({"name": f[k]["player"], "role": "Player", "team": f[k].get("team")})
    for side in ("home", "away"):
        a = f.get(f"{side}_absent_1")
        if isinstance(a, dict):
            ppl.append({"name": a["player"], "role": f"Missing ({a.get('reason')})", "team": pack[side]})
    return ppl
