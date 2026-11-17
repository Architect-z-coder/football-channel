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
    return {"url": info.get("thumburl") or info["url"], "page": info.get("descriptionurl"),
            "licence": lic, "author": _clean_artist(meta.get("Artist", {}).get("value"))}


def _clean_artist(html: str) -> str:
    import re
    txt = re.sub(r"<[^>]+>", "", html or "").replace("Original:", "").replace("Derivative work:", "/")
    return " ".join(txt.split()).strip(" ;/")[:60] or "unknown"


def _commons_search(query: str, limit: int = 8) -> list[dict]:
    """Search Wikimedia Commons files; keep only freely licensed photos."""
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=HEAD, timeout=20, params={
        "action": "query", "generator": "search", "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": 6, "gsrlimit": limit, "prop": "imageinfo", "iiprop": "url|extmetadata|size",
        "iiextmetadatafilter": "LicenseShortName|Artist", "iiurlwidth": 900, "format": "json"})
    pages = sorted((r.json().get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    out = []
    for p in pages:
        info = (p.get("imageinfo") or [None])[0]
        if not info or info.get("width", 0) < 280:
            continue
        meta = info.get("extmetadata", {})
        lic = (meta.get("LicenseShortName", {}).get("value") or "").strip()
        if not lic.lower().startswith(OK_LICENCES):
            continue
        out.append({"url": info.get("thumburl") or info["url"], "page": info.get("descriptionurl"),
                    "licence": lic, "author": _clean_artist(meta.get("Artist", {}).get("value")),
                    "title": p.get("title", ""), "width": info.get("width", 0)})
    return out


def _best_photo(person: dict) -> dict | None:
    """Search Commons with context first (press conference for coaches, playing for players),
    then the person's Wikidata portrait."""
    name = person["name"]
    last = name.split()[-1].lower()
    queries = ([f'"{name}" press conference', f'"{name}" coach', f'"{name}"']
               if "coach" in (person.get("role") or "").lower()
               else [f'"{name}" football', f'"{name}"'])
    for q in queries:
        try:
            hits = sorted((h for h in _commons_search(q) if last in h["title"].lower()),
                          key=lambda h: -h["width"])   # sharpest photo of the right person first
        except Exception as e:
            log.info("Commons search failed for %s: %s", q, e)
            hits = []
        if hits:
            return {**hits[0], "query": q}
    fn = _wikidata_image(name)
    return _commons_info(fn) if fn else None


def find(people: list[dict], outdir: Path, limit: int = 8) -> list[dict]:
    """people: [{"name", "role", "team"}]. Returns photos saved in outdir with credits."""
    out, seen = [], set()
    outdir.mkdir(parents=True, exist_ok=True)
    for p in people:
        if len(out) >= limit or not p.get("name") or p["name"] in seen:
            continue
        seen.add(p["name"])
        try:
            info = _best_photo(p)
            if not info:
                continue
            dest = outdir / f"photo_{len(out) + 1}.jpg"
            import io
            import time

            from PIL import Image
            time.sleep(1)                                   # be gentle with Wikimedia
            r = requests.get(info["url"], headers=HEAD, timeout=30)
            r.raise_for_status()
            try:                                            # must be a real image: re-save as a clean JPEG
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
            except Exception:
                raise ValueError("download was not an image")
            img.thumbnail((1200, 1200))
            img.save(dest, "JPEG", quality=88)
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
