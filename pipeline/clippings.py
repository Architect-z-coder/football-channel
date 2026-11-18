"""Newspaper cuts: a real screenshot of each review article (headline + the quoted paragraph), when the
page is free to read. Also measures where each word of the quote sits in the paragraph image, so the
video can highlight the words as the narrator reads them.

Checks, per article:
- the page must load without a paywall, and the quote must be found on the page word for word;
- cookie banners: we click "reject"/"necessary only" where offered, else hide the overlay;
- page loaded but the quote is NOT on it -> the review is dropped (the quote may be wrong);
- paywall / blocked / timeout -> kept, and shown as our rebuilt clipping instead (kind = "rebuilt").
Runs on the GitHub runner (Playwright + Chromium). Never raises.
"""
import json
import re
from pathlib import Path

from .common import log

REJECT = ["Reject all", "Reject All", "Reject", "Decline", "Decline all", "Only necessary", "Necessary only",
          "Use necessary cookies only", "Continue without accepting", "Tout refuser", "Refuser",
          "Continuer sans accepter", "Alle ablehnen", "Ablehnen", "Nur notwendige", "Rechazar todo", "Rechazar",
          "Rifiuta tutto", "Rifiuta", "Weigeren", "Alles weigeren", "Rejeitar"]
PAYWALL = re.compile(r"subscribe to (continue|read)|to continue reading|already a subscriber|sign in to read|"
                     r"subscribers only|abonnez-vous|réservé aux abonnés|jetzt abonnieren|weiterlesen mit|"
                     r"suscríbete|solo para suscriptores|abbonati|alleen voor abonnees", re.I)

JS_FIND = r"""
(quote) => {
  const simp = s => s.toLowerCase().replace(/[‘’‚‛'`´]/g, "'")
     .replace(/[“”„«»"]/g, '"').replace(/[–—]/g, '-').replace(/\s+/g, ' ');
  const words = simp(quote).replace(/^["' ]+|["' .,]+$/g, '').split(' ').filter(Boolean);
  const target = words.join(' ');
  // hide fixed overlays (cookie walls, sticky bars) that would cover the shot
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if ((cs.position === 'fixed' || cs.position === 'sticky') && el.offsetHeight > 0) el.style.setProperty('display', 'none', 'important');
  }
  document.documentElement.style.overflow = 'visible'; document.body.style.overflow = 'visible';
  const blocks = [...document.querySelectorAll('p, blockquote, li, div')].filter(e => {
    if (!e.offsetParent) return false;
    const t = simp(e.textContent || '');
    return t.length < 2500 && t.includes(target);
  });
  if (!blocks.length) return {found: false};
  blocks.sort((a, b) => (a.textContent.length - b.textContent.length));
  const el = blocks[0];
  // map simplified text back to text nodes to measure each word
  const nodes = []; const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  let n, flat = '', map = [];
  while ((n = walk.nextNode())) {
    for (let i = 0; i < n.data.length; i++) {
      let c = simp(n.data[i]);
      if (c === ' ' && flat.endsWith(' ')) continue;
      flat += c; map.push([n, i]);
    }
  }
  const start = flat.indexOf(target);
  el.scrollIntoView({block: 'center'});
  const er = el.getBoundingClientRect();
  const rects = []; let pos = start;
  for (const w of words) {
    const s = flat.indexOf(w, pos); if (s < 0) break; const e = s + w.length - 1; pos = e + 1;
    const r = document.createRange(); r.setStart(map[s][0], map[s][1]); r.setEnd(map[e][0], map[e][1] + 1);
    const b = r.getBoundingClientRect();
    rects.push({x: b.left - er.left, y: b.top - er.top, w: b.width, h: b.height});
  }
  const h1 = document.querySelector('h1');
  const hr = h1 && h1.offsetParent ? h1.getBoundingClientRect() : null;
  el.setAttribute('data-tot-quote', '1'); if (h1) h1.setAttribute('data-tot-head', '1');
  return {found: true, rects, w: er.width, h: er.height, head: !!hr};
}
"""


def _reject_cookies(page) -> None:
    for frame in [page] + list(page.frames):
        for label in REJECT:
            try:
                b = frame.get_by_role("button", name=label, exact=True)
                if b.count():
                    b.first.click(timeout=1500)
                    page.wait_for_timeout(600)
                    return
            except Exception:
                continue


def capture(items: list[dict], outdir: Path) -> list[dict]:
    """Adds kind ("screenshot" | "rebuilt"), files and word boxes to each review; drops wrong quotes."""
    if not items:
        return []
    outdir.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("Playwright not installed: all press cuts will be rebuilt clippings.")
        return [{**r, "kind": "rebuilt"} for r in items]
    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1100, "height": 1400}, device_scale_factor=2,
                                  locale="en-GB", user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"))
        for i, r in enumerate(items, 1):
            r = {**r, "kind": "rebuilt"}
            page = ctx.new_page()
            try:
                resp = page.goto(r["url"], wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)
                if not resp or resp.status >= 400:
                    raise RuntimeError(f"HTTP {resp.status if resp else 'none'}")
                _reject_cookies(page)
                res = page.evaluate(JS_FIND, r["quote"])
                body = page.inner_text("body")[:200000]
                if not res.get("found"):
                    if PAYWALL.search(body) or len(body) < 1500:
                        log.info("Press cut %d (%s): paywall or short page, rebuilt clipping.", i, r["outlet"])
                        out.append(r)
                    else:
                        log.warning("Press cut %d (%s): quote not on the page; review dropped.", i, r["outlet"])
                    continue
                para = outdir / f"press_{i}_para.png"
                page.locator("[data-tot-quote]").first.screenshot(path=str(para))
                files = {"para": para.name}
                if res.get("head"):
                    head = outdir / f"press_{i}_head.png"
                    page.locator("[data-tot-head]").first.screenshot(path=str(head))
                    files["head"] = head.name
                r.update(kind="screenshot", files=files, rects=res["rects"], box={"w": res["w"], "h": res["h"]},
                         verified=True)
                log.info("Press cut %d (%s): screenshot taken.", i, r["outlet"])
                out.append(r)
            except Exception as e:
                log.info("Press cut %d (%s): %s; rebuilt clipping.", i, r.get("outlet"), str(e)[:120])
                out.append(r)
            finally:
                page.close()
        browser.close()
    (outdir / "reviews.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
