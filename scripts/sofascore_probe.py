"""Probe: can we read Sofascore average positions and heat maps for a match? Writes data/probe/*.json."""
import json, sys, time
from pathlib import Path
import requests

OUT = Path("data/probe"); OUT.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
     "Accept": "application/json", "Referer": "https://www.sofascore.com/", "Origin": "https://www.sofascore.com"}
BASES = ["https://api.sofascore.com/api/v1", "https://www.sofascore.com/api/v1"]
log = {}


def get(path):
    for b in BASES:
        try:
            r = requests.get(b + path, headers=H, timeout=25)
            log[b + path] = r.status_code
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            log[b + path] = str(e)[:100]
        time.sleep(1)
    return None


date, home, away = sys.argv[1], sys.argv[2].lower(), sys.argv[3].lower()
ev = get(f"/sport/football/scheduled-events/{date}")
match = None
for e in (ev or {}).get("events", []):
    h, a = e["homeTeam"]["name"].lower(), e["awayTeam"]["name"].lower()
    if home in h and (away in a or a.startswith(away[:4])):
        match = e; break
res = {"status": log, "event": match and {"id": match["id"], "home": match["homeTeam"]["name"],
                                          "away": match["awayTeam"]["name"]}}
if match:
    eid = match["id"]
    ap = get(f"/event/{eid}/average-positions")
    res["average_positions"] = ap
    lu = get(f"/event/{eid}/lineups")
    if lu:
        pid = lu["home"]["players"][0]["player"]["id"]
        res["heatmap_sample_player"] = lu["home"]["players"][0]["player"]["name"]
        res["heatmap"] = get(f"/event/{eid}/player/{pid}/heatmap")
res["status"] = log
(OUT / "sofascore_probe.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps(log, indent=1))
