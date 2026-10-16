"""Style tokens: palette, fonts, sizes, layers, layout. Change the look of the whole film here.

Units: Manim's frame is 14.22 x 8 units; at 1080p one unit is 135 px. Sizes below are written in CSS pixels
at 1080p (what quality-bar.md talks about) and converted with px() / fs().
"""
import os
import shutil

from manim import config

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.dirname(HERE)

# ----------------------------------------------------------------------------- palette (dark editorial / 3b1b)
BG = "#0A0F1E"          # base background (the PNG backdrop adds gradient, vignette, grain)
BG_DEEP = "#060912"
PANEL = "#131B34"       # cards, cells, code background
PANEL_HI = "#1B2546"    # raised card / active cell
INK = "#EEF1F8"         # main text
MUTED = "#9DA7C8"       # secondary text, labels: 7.1:1 on PANEL, 8:1 on BG (quality bar: text >= 4.5:1)
DIM = "#3A4672"         # inactive strokes, grid, never text (2:1)
EDGE = "#56638F"        # graph edges at rest
AMBER = "#FFB547"       # warm accent: the thing being looked at, prices, the answer
CYAN = "#3DD9C9"        # cool accent: valid, start, reads
CORAL = "#FF6B6B"       # illegal, wrong, over the limit
VIOLET = "#A48CFF"      # alternative route, destinations
MINT = "#7BE3B5"        # accepted, the pick
SHADOW = "#000000"
COMIC = "#FFD84D"       # comic burst fill
COMIC_INK = "#1A1206"   # comic outlines

# Roles the original palette fills with the colours above (a theme maps each one to its own token):
ACCENT = AMBER          # chapter numbers, card rules, progress pips, the title's second line
BG2 = BG                # backdrop gradient partner (the original paints BG -> BG_DEEP)
EDGE_UNDER = BG_DEEP    # the dark underlay that separates graph edges from the grid
SHADOW_K = 1.0          # opacity factor for drop shadows
CODE_COMMENT = "#AEB7D5"    # 8.4:1 on PANEL, 5.6:1 dimmed
CODE_KEYWORD = "#BBA8FF"    # violet lifted for code: 8.2:1, 5.5:1 dimmed
CODE_PUNCT = "#BCC3DD"
CODE_OP = "#FFAE90"
CODE_LINENO = "#8D98BC"     # line numbers: 5.9:1 (they were #4E5A86, 2.5:1)
CODE_FUNC = "#9CC8FF"
CODE_IDLE = None            # themes: colour of the code lines out of focus (None: dim them by opacity instead)
KEY_LIGHTS = None           # themes: six chapter key lights for the backdrop (None: AMBER key, CYAN rim)

# ----------------------------------------------------------------------------- theme (optional)
# A registry theme is one file, source/kit/theme.py, written by
#     python3 $S/theme.py emit <id> --format py --out source/kit/theme.py
# With no such file the film keeps the original palette above, unchanged. Delete the file to go back to it.
try:
    from .theme import THEME  # noqa: F401
except ImportError:
    THEME = None
THEMED = THEME is not None
THEME_ID = THEME["id"] if THEMED else "original"
TONE = THEME["tone"] if THEMED else "dark"
LIGHT = TONE == "light"

_INK_OF, _ON_OF = {}, {}        # fill colour -> its text ink / its on-fill text colour (empty: original)


def _hex(c):
    if isinstance(c, str):
        return c.upper()
    from manim import ManimColor
    return ManimColor(c).to_hex().upper()


def _lum(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        v = int(h[i:i + 2], 16) / 255
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def _contrast(a, b):
    la, lb = _lum(_hex(a)), _lum(_hex(b))
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _mix(a, b, t):
    a, b = _hex(a).lstrip("#"), _hex(b).lstrip("#")
    return "#" + "".join(f"{round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t):02X}" for i in (0, 2, 4))


def _reach(c, toward, ratio, against):
    """c moved toward `toward` just far enough to stand `ratio`:1 against `against` (for strokes and shapes)."""
    for k in range(0, 101):
        m = _mix(c, toward, k / 100)
        if _contrast(m, against) >= ratio:
            return m
    return _hex(toward)


if THEMED:
    _t = THEME
    BG, BG2, BG_DEEP = _t["bg"], _t["bg2"], _t["deep"]
    PANEL, PANEL_HI = _t["panel"], _t["panel2"]
    INK, MUTED = _t["text"], _t["muted"]
    DIM = _t["line2"]                                   # strokes, grid, pips to come (never text)
    EDGE = _reach(_t["line2"], _t["muted"], 3.0, BG)     # edges at rest: about 3:1 on the ground
    AMBER, CYAN, CORAL = _t["warm"], _t["cool"], _t["bad"]
    VIOLET, MINT, COMIC, ACCENT = _t["violet"], _t["good"], _t["gold"], _t["accent"]
    SHADOW = _t["shadow"]
    SHADOW_K = 0.35 if LIGHT else 1.0
    COMIC_INK = _t["shadow"]
    EDGE_UNDER = BG if LIGHT else BG_DEEP
    CODE_COMMENT = CODE_PUNCT = CODE_LINENO = CODE_IDLE = _t["muted"]
    CODE_KEYWORD, CODE_OP, CODE_FUNC = _t["violetInk"], _t["badInk"], _t["accentInk"]
    KEY_LIGHTS = list(_t["lights"])
    for _h in ("accent", "warm", "good", "bad", "cool", "gold", "violet"):
        _INK_OF[_hex(_t[_h])] = _t[_h + "Ink"]
        _ON_OF[_hex(_t[_h])] = _t["on" + _h[0].upper() + _h[1:]]


def ink(c):
    """The colour for TEXT or a THIN STROKE in hue c (AMBER, CYAN...). In the original palette it is c itself; in a
    theme it is the solved ink (same hue, contrast >= 4.6:1 on every surface). T/H/Mono/Rich apply it for you."""
    if not _INK_OF or c is None:
        return c
    return _INK_OF.get(_hex(c), c)


def on_fill(c):
    """The colour for a label sitting ON a filled shape of hue c (a badge, a pill)."""
    if not _ON_OF:
        return BG
    return _ON_OF.get(_hex(c), INK)


AMBER_INK, CYAN_INK, CORAL_INK, VIOLET_INK, MINT_INK, ACCENT_INK = (ink(c) for c in (AMBER, CYAN, CORAL, VIOLET, MINT, ACCENT))


def key_light(chapter):
    """The backdrop's warm key light for a chapter (themes take it from their six `lights`)."""
    if not KEY_LIGHTS:
        return AMBER
    return KEY_LIGHTS[max(0, int(chapter)) % len(KEY_LIGHTS)]

# ----------------------------------------------------------------------------- fonts
DISPLAY = "Inter Display"   # headlines (system font here; brew/apt install Inter on a laptop)
SANS = "Inter"              # body, captions, labels
MONO = "DejaVu Sans Mono"   # code and numbers: no programming ligatures, so != stays != (shipped in fonts/)

# ----------------------------------------------------------------------------- sizes (CSS px at 1080p)
PX_PER_UNIT = 135.0
FS_PER_PX = 1 / 1.877       # Manim font_size per CSS px of em (measured: Inter font_size 100 = 187.7 px em)

SIZE = dict(
    hero=150,        # chapter numbers
    title=96,        # film title
    headline=72,     # chapter names, question text upper bound
    question=50,
    body=44,
    label=36,        # node numbers, row labels
    caption=42,
    code=30,         # quality bar: code 30-36 px
    small=32,        # the kit's floor for tags, chips, headers (START, INPUT, TIME, weights)
)
# The quality bar says nothing under 26 px. The kit's floor is 32 px because legibility.py measures the cap height,
# and on a 480p draft still a 26-28 px label reads 1-3 px low; lowercase-only words ("new", "row") read at their
# x-height (75% of the size), so small labels are set in capitals. MIN_TEXT is what WGraph.fit_labels() keeps
# weights and node numbers at when the graph is posed small (pose(), settle()).
MIN_TEXT = 32


def px(n):
    """CSS pixels at 1080p -> scene units."""
    return n / PX_PER_UNIT


def fs(n):
    """CSS pixel em size -> Manim font_size."""
    return n * FS_PER_PX


# ----------------------------------------------------------------------------- layout (scene units)
FW, FH = config.frame_width, config.frame_height          # 14.22 x 8
SAFE_X = FW / 2 - px(96)                                  # text stays 96 px from the sides
SAFE_TOP = FH / 2 - px(96)
CAPTION_BAND = px(180)                                    # bottom band reserved for captions
STAGE_BOTTOM = -FH / 2 + CAPTION_BAND + px(16)            # the subject lives above this line
STAGE_TOP = SAFE_TOP - px(60)                             # below the chapter tag

# ----------------------------------------------------------------------------- z layers (higher draws on top)
Z = dict(grid=-20, glow=-5, edge=0, edge_label=2, node=4, token=8, panel=10, panel_text=11,
         card=40, card_text=41, callout=50, hud=60, caption=70, overlay=80)

# ----------------------------------------------------------------------------- motion
RUN = dict(enter=0.5, exit=0.3, move=0.9, pop=0.45)       # default run times in seconds (motion, not placement)
DRIFT = 0.012                                             # camera breath per hold (fraction of frame width)

HAS_LATEX = shutil.which("latex") is not None and shutil.which("dvisvgm") is not None


def register_fonts():
    """Make the fonts shipped in fonts/ visible to Pango (no system install needed)."""
    try:
        import manimpango
    except ImportError:
        return
    d = os.path.join(SOURCE, "fonts")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".ttf", ".otf")):
                manimpango.register_font(os.path.join(d, f))


register_fonts()


def _check_fonts():
    try:
        import manimpango
        have = set(manimpango.list_fonts())
    except Exception:
        return
    missing = [f for f in (SANS, DISPLAY, MONO) if f not in have]
    if missing:
        import sys
        print(f"FONT-MISSING {', '.join(missing)}: text falls back to another face. Install Inter (Linux: apt-get "
              "install fonts-inter; macOS: brew install --cask font-inter) or drop the .otf/.ttf files into "
              "source/fonts/.", file=sys.stderr, flush=True)


_check_fonts()
