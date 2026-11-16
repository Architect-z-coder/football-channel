"""YouTube thumbnails (1280x720), three styles for Test & Compare.

1. Shot map   - the real match shots on a pitch (Understat), sized by xG, goals in gold.
2. Big number - the score with the number that tells the story (xG or half-time score).
3. Team split - both team names in their colours with the score between them.

No badges, no player photos, no broadcast stills: only drawn data and type.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import patheffects  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from mplsoccer import Pitch  # noqa: E402

from .common import ASSETS_DIR  # noqa: E402

BG = "#07110C"
PANEL = "#0E1D15"
LINE = "#2A4A38"
TEXT = "#F4F6F5"
MUTED = "#9DB0A5"
GOLD = "#F2C14E"
HOME = "#E8EDF2"
AWAY = "#4FB3BF"
W, H, DPI = 12.8, 7.2, 100

_font = ASSETS_DIR / "fonts" / "Anton-Regular.ttf"
DISPLAY = FontProperties(fname=str(_font)) if _font.exists() else FontProperties(weight="bold")
STROKE = [patheffects.withStroke(linewidth=10, foreground=BG)]


def _facts(pack):
    return {f["id"]: f["value"] for f in pack["facts"]}


def _canvas():
    fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 128), ax.set_ylim(0, 72), ax.axis("off")
    return fig, ax


def _fit(fig, ax, x, y, text, size, max_w, **kw):
    """Draw text and shrink it until it is narrower than max_w (axis units)."""
    t = ax.text(x, y, text, fontproperties=DISPLAY, fontsize=size, **kw)
    r = fig.canvas.get_renderer()
    for _ in range(40):
        bb = t.get_window_extent(renderer=r).transformed(ax.transData.inverted())
        if bb.width <= max_w or size <= 20:
            break
        size *= 0.92
        t.set_fontsize(size)
    return t


def _headline(text: str) -> str:
    words = text.upper().split()
    if len(words) >= 3:  # two short lines read better than one long one
        mid = (len(words) + 1) // 2
        return " ".join(words[:mid]) + "\n" + " ".join(words[mid:])
    return " ".join(words)


def _score(f):
    return f"{f.get('score_home')}-{f.get('score_away')}"


def shot_map(pack, text, path):
    f = _facts(pack)
    fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=BG)
    pax = fig.add_axes([0.02, 0.02, 0.96, 0.70])
    pitch = Pitch(pitch_type="opta", pitch_color=BG, line_color=LINE, linewidth=2.5, goal_type="box")
    pitch.draw(ax=pax)
    pax.set_ylim(10, 90)   # crop the touchline strips so the pitch fills the frame
    for s in pack.get("shots", []):
        # Understat: x, y in 0-1 towards the goal being attacked. Home attacks right, away attacks left.
        x, y = s["x"] * 100, s["y"] * 100
        if s["side"] == "away":
            x, y = 100 - x, 100 - y
        goal = s["result"] == "Goal"
        colour = HOME if s["side"] == "home" else AWAY
        pitch.scatter(x, y, s=220 + 4200 * float(s["xg"]), ax=pax, zorder=3,
                      color=GOLD if goal else colour, alpha=0.95 if goal else 0.45,
                      edgecolors=colour if goal else "none", linewidths=3)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 128), ax.set_ylim(0, 72), ax.axis("off")
    _fit(fig, ax, 4, 63, text.upper(), 96, 88, color=GOLD, ha="left", va="center", zorder=5)
    _fit(fig, ax, 124, 63, _score(f), 110, 30, color=TEXT, ha="right", va="center", zorder=5)
    fig.savefig(path, dpi=DPI, facecolor=BG)
    plt.close(fig)


def big_number(pack, text, path):
    f = _facts(pack)
    fig, ax = _canvas()
    Pitch(pitch_type="custom", pitch_length=128, pitch_width=72, pitch_color=BG, line_color=PANEL,
          linewidth=3).draw(ax=ax)
    ax.set_xlim(0, 128), ax.set_ylim(0, 72)
    _fit(fig, ax, 6, 52, _score(f), 190, 62, color=TEXT, ha="left", va="center")
    if f.get("home_xg") is not None and f.get("away_xg") is not None:
        top, sub = f"{f['home_xg']} v {f['away_xg']}", "EXPECTED GOALS"
    elif f.get("ht_home") is not None:
        top, sub = f"HT {f.get('ht_home')}-{f.get('ht_away')}", "AT HALF-TIME"
    else:
        top, sub = "", ""
    if top:
        _fit(fig, ax, 122, 58, top, 88, 52, color=GOLD, ha="right", va="center")
        ax.text(122, 47, sub, fontproperties=DISPLAY, fontsize=30, color=MUTED, ha="right", va="center")
    ax.add_patch(plt.Rectangle((0, 0), 128, 26, color=GOLD, zorder=2))
    _fit(fig, ax, 64, 13, text.upper(), 96, 120, color=BG, ha="center", va="center", zorder=3)
    fig.savefig(path, dpi=DPI, facecolor=BG)
    plt.close(fig)


def team_split(pack, text, path):
    f = _facts(pack)
    fig, ax = _canvas()
    ax.add_patch(plt.Polygon([(0, 22), (68, 22), (60, 72), (0, 72)], color=PANEL, zorder=1))
    ax.plot([68, 60], [22, 72], color=GOLD, lw=6, zorder=2)
    _fit(fig, ax, 29, 56, pack["home"].upper(), 84, 50, color=HOME, ha="center", va="center", zorder=3)
    _fit(fig, ax, 97, 56, pack["away"].upper(), 84, 50, color=AWAY, ha="center", va="center", zorder=3)
    _fit(fig, ax, 29, 35, str(f.get("score_home")), 120, 30, color=TEXT, ha="center", va="center", zorder=3)
    _fit(fig, ax, 97, 35, str(f.get("score_away")), 120, 30, color=TEXT, ha="center", va="center", zorder=3)
    ax.add_patch(plt.Rectangle((0, 0), 128, 22, color=GOLD, zorder=2))
    _fit(fig, ax, 64, 11, text.upper(), 86, 120, color=BG, ha="center", va="center", zorder=3)
    fig.savefig(path, dpi=DPI, facecolor=BG)
    plt.close(fig)


def render(script: dict, pack: dict, workdir: Path) -> list[Path]:
    texts = (script.get("thumbnail_texts") or ["Explained"] * 3) + ["Explained"] * 3
    styles = [shot_map, big_number, team_split] if pack.get("shots") else [big_number, team_split, shot_map]
    paths = []
    for i, (style, text) in enumerate(zip(styles, texts[:3])):
        p = workdir / f"thumbnail_{i + 1}.png"
        style(pack, text, p)
        paths.append(p)
    return paths
