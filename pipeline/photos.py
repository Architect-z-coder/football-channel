"""Real photos of the people in the story (coaches, key players, absentees) from Wikimedia Commons.

Only freely licensed images (public domain, CC0, CC BY, CC BY-SA) are used, found through each
person's Wikidata portrait (P18). Every photo is shown with its author and licence on screen, and
listed in the video description. Match/press-agency photos (Getty, Reuters, AP...) are never used.
Never raises: no photo means the scene simply uses graphics.
"""
from pathlib import Path

import requests

from .common import log

HEAD = {"User-Agent": "TheOtherTouchline/1.0 (https://github.com/Architect-z-coder/football-channel) python-requests"}
OK_LICENCES = ("public domain", "pd", "cc0", "cc by", "cc-by")


def _get(url: str, **kw):
    """GET with one polite retry when Wikimedia says 'too many requests'."""
    import time
    kw.pop("headers", None)
    kw.pop("timeout", None)
    for attempt in range(3):
        r = requests.get(url, headers=HEAD, timeout=30, **kw)
        if r.status_code != 429:
            return r
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()
    return r


def _wikidata_image(name: str) -> str | None:
    r = _get("https://www.wikidata.org/w/api.php", headers=HEAD, timeout=20, params={
        "action": "wbsearchentities", "search": name, "language": "en", "type": "item",
        "limit": 5, "format": "json"})
    for hit in r.json().get("search", []):
        desc = (hit.get("description") or "").lower()
        if not any(w in desc for w in ("football", "soccer", "coach", "manager")):
            continue
        e = _get(f"https://www.wikidata.org/wiki/Special:EntityData/{hit['id']}.json").json()
        claims = e["entities"][hit["id"]].get("claims", {}).get("P18") or []
        if claims:
            return claims[0]["mainsnak"]["datavalue"]["value"]
    return None


def _commons_info(filename: str) -> dict | None:
    r = _get("https://commons.wikimedia.org/w/api.php", params={
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
    r = _get("https://commons.wikimedia.org/w/api.php", params={
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


OPENVERSE_OK = {"by", "by-sa", "cc0", "pdm"}


def _openverse(query: str, last: str) -> dict | None:
    """Openverse (Flickr and other open collections): commercial-use licences only."""
    r = _get("https://api.openverse.org/v1/images/", params={
        "q": query, "license_type": "commercial", "page_size": 20})
    best = None
    for h in r.json().get("results", []):
        lic = (h.get("license") or "").lower()
        if lic not in OPENVERSE_OK or (h.get("width") or 0) < 400:
            continue
        if last and last not in ((h.get("title") or "") + " " + " ".join(t.get("name", "") for t in h.get("tags") or [])).lower():
            continue
        if not best or (h.get("width") or 0) > (best.get("width") or 0):
            best = h
    if not best:
        return None
    lic = best["license"]
    lic_name = {"cc0": "CC0", "pdm": "Public domain"}.get(lic, f"CC {lic.upper()} {best.get('license_version') or ''}".strip())
    return {"url": best["url"], "page": best.get("foreign_landing_url") or best.get("url"),
            "licence": lic_name, "author": (best.get("creator") or "unknown")[:60],
            "via": "Openverse"}


def _best_photo(person: dict) -> dict | None:
    """Search Commons with context first (press conference for coaches, playing for players),
    then the person's Wikidata portrait."""
    name = person["name"]
    if person.get("role") == "Stadium inside":               # stands, pitch, interior views
        base = person["stadium"].split(",")[0]
        key = next((w.lower() for w in base.split() if len(w) > 3), base.lower())
        seen, hits = set(), []
        for q in (f'"{base}" interior', f'"{base}" inside', f'"{base}" stands', f'"{base}" pitch',
                  f'"{base}" match', f'"{base}" tribune'):
            try:
                for h in _commons_search(q):
                    t = h["title"].lower()
                    if key in t and h["url"] not in seen and not any(x in t for x in ("aerial", "exterior",
                                                                                     "outside", "map", "logo", "plan")):
                        seen.add(h["url"]); hits.append(h)
            except Exception as e:
                log.info("Commons search failed for %s: %s", q, e)
            if len(hits) > person.get("pick", 0) + 2:
                break
        return hits[person.get("pick", 0)] if len(hits) > person.get("pick", 0) else None
    if person.get("role") == "Stadium":                       # places: plain search, no name filter
        hits = _commons_search(f'"{name.split(",")[0]}"')
        if hits:
            return hits[0]
        return _openverse(name.split(",")[0], "")
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
    info = _commons_info(fn) if fn else None
    if info:
        return info
    try:
        return _openverse(name, last)
    except Exception as e:
        log.info("Openverse failed for %s: %s", name, e)
        return None


def find(people: list[dict], outdir: Path, limit: int = 15, start: int = 0) -> list[dict]:
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
            if any(o.get("url") == info.get("url") for o in out):
                continue
            dest = outdir / f"photo_{start + len(out) + 1}.jpg"
            import io
            import time

            from PIL import Image
            time.sleep(1)                                   # be gentle with Wikimedia
            r = _get(info["url"])
            r.raise_for_status()
            try:                                            # must be a real image: re-save as a clean JPEG
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
            except Exception:
                raise ValueError("download was not an image")
            img.thumbnail((1200, 1200))
            img.save(dest, "JPEG", quality=88)
            out.append({**p, "file": dest.name, "path": str(dest), "via": info.get("via", "Wikimedia Commons"), **info})
        except Exception as e:
            log.info("No photo for %s (%s)", p["name"], e)
    log.info("Photos: %d free-licence photos found (Wikimedia Commons)", len(out))
    return out


def people_in(pack: dict) -> list[dict]:
    """Who and where the story is about: stadium, coaches, scorers, top/bottom rated, absentees,
    and coaches named in the coach story (e.g. the predecessor)."""
    f = {x["id"]: x["value"] for x in pack["facts"]}
    ppl = []
    if f.get("stadium"):
        ppl.append({"name": f["stadium"], "role": "Stadium", "team": ""})
        for k in range(3):        # up to three views from inside the ground
            ppl.append({"name": f"{f['stadium']} (inside, view {k + 1})", "role": "Stadium inside",
                        "stadium": f["stadium"], "pick": k, "team": ""})
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
    for k in sorted(k for k in f if k.startswith("goal_")):
        if isinstance(f[k], dict) and f[k].get("player"):
            ppl.append({"name": f[k]["player"], "role": "Scorer", "team": f[k].get("team")})
    for t in (pack.get("context") or {}).get("teams", []):
        if t.get("replaced"):
            ppl.append({"name": t["replaced"].split("(")[0].strip(), "role": "Former coach", "team": t.get("team")})
    return ppl
