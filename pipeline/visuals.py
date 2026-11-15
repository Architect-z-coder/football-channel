"""Visual engine: renders each scene and the thumbnails as images (no footage, no badges, no faces)."""
import re
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mplsoccer import Pitch  # noqa: E402

BG = "#0E1A14"
PANEL = "#16271E"
TEXT = "#F4F6F5"
MUTED = "#9DB0A5"
ACCENT = "#F2C14E"
HOME = "#E8EDF2"
AWAY = "#4FB3BF"

W, H, DPI = 16, 9, 120  # 1920 x 1080


def _fig(w=W, h=H):
    fig = plt.figure(figsize=(w, h), dpi=DPI, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.set_facecolor(BG)
    return fig, ax


def _footer(ax, cfg, pack):
    ax.text(3, 4, cfg["channel"]["name"].upper(), color=MUTED, fontsize=13, fontweight="bold")
    ax.text(97, 4, f"Data: {pack.get('source', 'API-Football')}", color=MUTED, fontsize=12, ha="right")


def _save(fig, path: Path):
    fig.savefig(path, dpi=DPI, facecolor=fig.get_facecolor())
    plt.close(fig)


def _facts(pack):
    return {f["id"]: f["value"] for f in pack["facts"]}


def _num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"\d+(?:\.\d+)?", str(v))
    return float(m.group()) if m else None


def _wrap(text, width):
    return "\n".join(textwrap.wrap(text, width, break_long_words=False))


def title_card(ax, vis, pack, cfg):
    ax.text(50, 62, _wrap(vis.get("title", ""), 32), color=TEXT, fontsize=54,
            fontweight="bold", ha="center", va="center", linespacing=1.15)
    ax.text(50, 36, _wrap(vis.get("subtitle", ""), 60), color=ACCENT, fontsize=26,
            ha="center", va="center")


def scoreline(ax, vis, pack, cfg):
    f = _facts(pack)
    ax.text(50, 80, pack["competition"].upper(), color=MUTED, fontsize=22, ha="center")
    ax.text(20, 55, _wrap(pack["home"], 12), color=HOME, fontsize=42, fontweight="bold",
            ha="center", va="center")
    ax.text(80, 55, _wrap(pack["away"], 12), color=AWAY, fontsize=42, fontweight="bold",
            ha="center", va="center")
    ax.text(50, 55, f"{f.get('score_home')} – {f.get('score_away')}", color=TEXT,
            fontsize=90, fontweight="bold", ha="center", va="center")
    sub = " · ".join(str(x) for x in [f.get("round"), f.get("date")] if x)
    ax.text(50, 30, sub, color=MUTED, fontsize=20, ha="center")


def stat_bars(ax, vis, pack, cfg):
    f = _facts(pack)
    stats = [s for s in vis.get("stats", []) if f"home_{s}" in f and f"away_{s}" in f][:5]
    ax.text(28, 88, pack["home"], color=HOME, fontsize=28, fontweight="bold", ha="center")
    ax.text(72, 88, pack["away"], color=AWAY, fontsize=28, fontweight="bold", ha="center")
    top, step = 75, 13
    for i, key in enumerate(stats):
        y = top - i * step
        hv, av = f[f"home_{key}"], f[f"away_{key}"]
        hn, an = _num(hv) or 0, _num(av) or 0
        total = hn + an or 1
        ax.text(50, y + 4.5, key.replace("_", " ").replace("pct", "%").title(), color=MUTED,
                fontsize=18, ha="center")
        left = 70 * hn / total
        ax.barh(y, left, left=15, height=4, color=HOME)
        ax.barh(y, 70 - left, left=15 + left, height=4, color=AWAY)
        ax.text(13, y, str(hv), color=HOME, fontsize=22, fontweight="bold", ha="right", va="center")
        ax.text(87, y, str(av), color=AWAY, fontsize=22, fontweight="bold", ha="left", va="center")


def key_number(ax, vis, pack, cfg):
    ax.text(50, 58, str(vis.get("value", "")), color=ACCENT, fontsize=150, fontweight="bold",
            ha="center", va="center")
    ax.text(50, 28, _wrap(vis.get("label", ""), 50), color=TEXT, fontsize=30, ha="center",
            va="center")


def events_timeline(ax, vis, pack, cfg):
    events = [f for f in pack["facts"] if f["id"].startswith("event_")]
    shown = [e for e in events if "Goal" in e["label"] or "Red Card" in e["label"]]
    end = max([90] + [e["value"]["minute"] or 0 for e in shown])
    ax.text(50, 88, "How the match unfolded", color=TEXT, fontsize=32, fontweight="bold", ha="center")
    ax.plot([8, 92], [50, 50], color=MUTED, lw=3)
    for m in (0, 45, 90):
        x = 8 + 84 * m / end
        ax.plot([x, x], [48, 52], color=MUTED, lw=2)
        ax.text(x, 43, f"{m}'", color=MUTED, fontsize=16, ha="center")
    for i, e in enumerate(shown):
        v = e["value"]
        minute = v["minute"] or 0
        x = 8 + 84 * minute / end
        is_home = e["label"].startswith(pack["home"])
        color = HOME if is_home else AWAY
        up = 1 if is_home else -1
        marker = "o" if "Goal" in e["label"] else "s"
        ax.scatter([x], [50], s=420, color=color if marker == "o" else "#D64545", zorder=3,
                   marker=marker, edgecolors=BG, linewidths=2)
        label = f"{minute}'{'+' + str(v['extra']) if v.get('extra') else ''} {v.get('player') or ''}"
        ax.text(x, 50 + up * (12 + 7 * (i % 2)), label.strip(), color=color, fontsize=17,
                ha="center", va="center")
    ax.text(30, 18, f"● {pack['home']}", color=HOME, fontsize=18, ha="center")
    ax.text(70, 18, f"● {pack['away']}", color=AWAY, fontsize=18, ha="center")


def _formation_points(formation: str, attacking_right: bool):
    rows = [int(x) for x in re.findall(r"\d", formation or "")] or [4, 4, 2]
    pts = [(4, 50)]  # goalkeeper
    for r, count in enumerate(rows):
        x = 12 + r * (30 / (len(rows) - 1)) if len(rows) > 1 else 28
        for j in range(count):
            y = 100 * (j + 1) / (count + 1)
            pts.append((x, y))
    if attacking_right:
        return pts
    return [(100 - x, y) for x, y in pts]


def formations(ax_unused, vis, pack, cfg, fig=None):
    f = _facts(pack)
    ax = fig.add_axes([0.1, 0.17, 0.8, 0.67])
    pitch = Pitch(pitch_type="opta", pitch_color=PANEL, line_color=MUTED, linewidth=1.5)
    pitch.draw(ax=ax)
    for side, color, right in (("home", HOME, True), ("away", AWAY, False)):
        pts = _formation_points(f.get(f"{side}_formation"), right)
        pitch.scatter([p[0] for p in pts], [p[1] for p in pts], ax=ax, s=500, color=color,
                      edgecolors=BG, zorder=3)
    ax_unused.text(25, 92, f"{pack['home']}  {f.get('home_formation') or ''}", color=HOME,
                   fontsize=26, fontweight="bold", ha="center")
    ax_unused.text(75, 92, f"{f.get('away_formation') or ''}  {pack['away']}", color=AWAY,
                   fontsize=26, fontweight="bold", ha="center")


def text_card(ax, vis, pack, cfg):
    ax.text(8, 78, _wrap(vis.get("heading", ""), 40), color=ACCENT, fontsize=44, fontweight="bold",
            va="center")
    for i, line in enumerate(vis.get("lines", [])[:3]):
        ax.text(8, 55 - i * 14, _wrap(line, 60), color=TEXT, fontsize=30, va="center")


def lesson_list(ax, vis, pack, cfg):
    ax.text(8, 84, "The lesson", color=ACCENT, fontsize=44, fontweight="bold", va="center")
    for i, item in enumerate(vis.get("items", [])[:3]):
        y = 62 - i * 18
        ax.text(9, y, str(i + 1), color=BG, fontsize=30, fontweight="bold", ha="center", va="center",
                bbox=dict(boxstyle="circle,pad=0.4", fc=ACCENT, ec="none"))
        ax.text(15, y, _wrap(item, 55), color=TEXT, fontsize=30, va="center")


def halftime_fulltime(ax, vis, pack, cfg):
    f = _facts(pack)
    ax.text(28, 88, pack["home"], color=HOME, fontsize=30, fontweight="bold", ha="center")
    ax.text(72, 88, pack["away"], color=AWAY, fontsize=30, fontweight="bold", ha="center")
    for y, label, h, a in ((62, "HALF TIME", f.get("ht_home"), f.get("ht_away")),
                           (32, "FULL TIME", f.get("score_home"), f.get("score_away"))):
        ax.text(50, y + 13, label, color=MUTED, fontsize=20, ha="center")
        ax.text(50, y, f"{h} – {a}", color=ACCENT if label == "FULL TIME" else TEXT,
                fontsize=72, fontweight="bold", ha="center", va="center")


def _table_grid(ax, title, cols, rows, pack):
    ax.text(50, 86, title, color=TEXT, fontsize=32, fontweight="bold", ha="center")
    xs = [12] + [38 + i * (54 / max(1, len(cols) - 1)) for i in range(len(cols))]
    for x, c in zip(xs[1:], cols):
        ax.text(x, 70, c, color=MUTED, fontsize=20, ha="center")
    for r, (name, color, values) in enumerate(rows):
        y = 55 - r * 18
        ax.add_patch(plt.Rectangle((6, y - 6), 88, 12, color=PANEL, zorder=0))
        ax.text(xs[0] - 4, y, name, color=color, fontsize=26, fontweight="bold", va="center")
        for x, v in zip(xs[1:], values):
            ax.text(x, y, "–" if v is None else str(v), color=TEXT, fontsize=28,
                    fontweight="bold", ha="center", va="center")


def table_snapshot(ax, vis, pack, cfg):
    f = _facts(pack)
    keys = [("Pos", "position"), ("Pts", "points"), ("P", "played_games"), ("W", "won"),
            ("D", "draw"), ("L", "lost"), ("GF", "goals_for"), ("GA", "goals_against")]
    rows = [(pack[s], c, [f.get(f"{s}_{k}") for _, k in keys])
            for s, c in (("home", HOME), ("away", AWAY))]
    _table_grid(ax, "The league table", [k for k, _ in keys], rows, pack)


def form_compare(ax, vis, pack, cfg):
    f = _facts(pack)
    keys = [("W", "wins"), ("D", "draws"), ("L", "losses"), ("Scored", "goals_for"),
            ("Conceded", "goals_against")]
    rows = [(pack[s], c, [f.get(f"{s}_last5_{k}") for _, k in keys])
            for s, c in (("home", HOME), ("away", AWAY))]
    _table_grid(ax, "Form: the 5 matches before this one", [k for k, _ in keys], rows, pack)


RENDERERS = {
    "halftime_fulltime": halftime_fulltime, "table_snapshot": table_snapshot,
    "form_compare": form_compare,
    "title_card": title_card, "scoreline": scoreline, "stat_bars": stat_bars,
    "key_number": key_number, "events_timeline": events_timeline, "formations": formations,
    "text_card": text_card, "lesson_list": lesson_list,
}


def render_scene(scene: dict, pack: dict, cfg: dict, path: Path) -> None:
    vis = scene.get("visual") or {"type": "text_card", "heading": scene.get("on_screen", "")}
    kind = vis.get("type", "text_card")
    fig, ax = _fig()
    fn = RENDERERS.get(kind, text_card)
    if kind == "formations":
        fn(ax, vis, pack, cfg, fig=fig)
    else:
        fn(ax, vis, pack, cfg)
    if scene.get("on_screen") and kind not in ("title_card", "text_card", "key_number"):
        ax.text(50, 10, _wrap(scene["on_screen"], 90), color=TEXT, fontsize=20, ha="center",
                bbox=dict(boxstyle="round,pad=0.5", fc=PANEL, ec="none"))
    _footer(ax, cfg, pack)
    _save(fig, path)


def render_thumbnails(script: dict, pack: dict, cfg: dict, workdir: Path) -> list[Path]:
    """Three different thumbnail styles at 1280x720 for YouTube A/B testing."""
    f = _facts(pack)
    texts = (script.get("thumbnail_texts") or ["Explained"] * 3)[:3]
    paths = []
    for i, text in enumerate(texts):
        fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=BG)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 100), ax.set_ylim(0, 100), ax.axis("off")
        if i == 0:   # score + big text
            ax.text(50, 70, f"{f.get('score_home')}–{f.get('score_away')}", color=TEXT,
                    fontsize=120, fontweight="bold", ha="center", va="center")
            ax.text(50, 25, text.upper(), color=ACCENT, fontsize=64, fontweight="bold", ha="center")
        elif i == 1:  # pitch background + text
            pax = fig.add_axes([0, 0, 1, 1])
            Pitch(pitch_type="opta", pitch_color=PANEL, line_color=MUTED).draw(ax=pax)
            ax2 = fig.add_axes([0, 0, 1, 1]); ax2.axis("off"); ax2.set_xlim(0, 100); ax2.set_ylim(0, 100)
            ax2.text(50, 50, _wrap(text.upper(), 14), color=ACCENT, fontsize=84, fontweight="bold",
                     ha="center", va="center", bbox=dict(boxstyle="round,pad=0.3", fc=BG, ec="none"))
        else:        # two team colours split
            ax.add_patch(plt.Rectangle((0, 0), 50, 100, color=PANEL))
            ax.text(25, 62, _wrap(pack["home"], 10), color=HOME, fontsize=54, fontweight="bold",
                    ha="center", va="center")
            ax.text(75, 62, _wrap(pack["away"], 10), color=AWAY, fontsize=54, fontweight="bold",
                    ha="center", va="center")
            ax.text(50, 18, text.upper(), color=ACCENT, fontsize=58, fontweight="bold", ha="center")
        path = workdir / f"thumbnail_{i + 1}.png"
        fig.savefig(path, dpi=100, facecolor=BG)
        plt.close(fig)
        paths.append(path)
    return paths
