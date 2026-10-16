"""Depth and light for a 2D film: a painted backdrop (gradient, two soft light pools, vignette, grain) that sits in
screen space, and a faint world-space dot grid that moves with the camera so every push-in reads as motion.

The backdrop is one PNG generated once per resolution (numpy + Pillow, cached in source/.cache/) and used as the
camera's background image, so it costs nothing per frame. In a theme (style.THEMED) it is painted from the
theme's surfaces, with the chapter's key light from the theme's `lights` (style.key_light), one file per theme.
"""
import hashlib
import os

import numpy as np
from manim import VMobject, config

from .style import BG, BG2, BG_DEEP, DIM, LIGHT, SOURCE, THEME_ID, THEMED, Z, AMBER, CYAN


def _rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def backdrop_png(width=None, height=None, warm=AMBER, cool=CYAN, seed=7):
    """Path to the backdrop PNG for this resolution (created on first use)."""
    w = int(width or config.pixel_width)
    h = int(height or config.pixel_height)
    d = os.path.join(SOURCE, ".cache")
    os.makedirs(d, exist_ok=True)
    if THEMED:                      # one file per theme and light colours (the cache outlives a theme switch)
        k = hashlib.sha1(f"{BG}{BG2}{BG_DEEP}{warm}{cool}".encode()).hexdigest()[:8]
        path = os.path.join(d, f"backdrop-{THEME_ID}-{k}-{w}x{h}-{seed}.png")
    else:
        path = os.path.join(d, f"backdrop-{w}x{h}-{seed}.png")
    if os.path.exists(path):
        return path
    from PIL import Image
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (x - w / 2) / (w / 2), (y - h / 2) / (h / 2)
    r = np.sqrt(nx ** 2 * 0.9 + ny ** 2 * 1.1)
    if THEMED:
        img = _themed(nx, ny, r, w, h, warm, cool, seed)
        _save(img, path)
        return path
    base, deep = _rgb(BG), _rgb(BG_DEEP)
    t = np.clip(r / 1.25, 0, 1)[..., None] ** 1.6
    img = base * (1 - t) + deep * t
    # two soft light pools: warm key top-left, cool rim bottom-right
    for col, cx, cy, rad, k in ((warm, -0.62, -0.55, 0.85, 0.075), (cool, 0.70, 0.62, 0.9, 0.06)):
        dd = np.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
        g = np.exp(-(dd / rad) ** 2)[..., None] * k
        img = img * (1 - g) + _rgb(col) * g
    # vignette
    v = np.clip(1 - 0.38 * np.clip(r - 0.55, 0, None) ** 1.4, 0.55, 1)[..., None]
    img = img * v
    # grain (static film texture)
    rng = np.random.default_rng(seed)
    img = img + rng.normal(0, 2.2, size=(h, w, 1)).astype(np.float32)
    img = np.clip(img, 0, 255).astype(np.uint8)
    _save(img, path)
    return path


def _save(img, path):
    from PIL import Image
    tmp = f"{path}.{os.getpid()}.tmp.png"                # parallel segments may build it at the same time
    Image.fromarray(img, "RGB").save(tmp, optimize=True)
    os.replace(tmp, path)


def _themed(nx, ny, r, w, h, warm, cool, seed):
    """The same painting in a theme's colours. The ground is a blend of the theme's surfaces (bg, bg2, deep), which
    its text inks are solved against; the two light pools are faint (5-7.5%) and sit in the corners.
      dark:  bg -> bg2 toward the edges, two light pools, a vignette that sinks toward deep, additive grain;
      light: the same gradient, paler pools, a gentle vignette toward deep (never black), darkening grain."""
    base, part, deep = _rgb(BG), _rgb(BG2), _rgb(BG_DEEP)
    t = np.clip(r / 1.25, 0, 1)[..., None] ** 1.6
    img = base * (1 - t) + part * t
    k1, k2 = (0.05, 0.04) if LIGHT else (0.075, 0.06)
    for col, cx, cy, rad, k in ((warm, -0.62, -0.55, 0.85, k1), (cool, 0.70, 0.62, 0.9, k2)):
        dd = np.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
        g = np.exp(-(dd / rad) ** 2)[..., None] * k
        img = img * (1 - g) + _rgb(col) * g
    v = np.clip(np.clip(r - 0.55, 0, None) ** 1.4 * (0.55 if LIGHT else 0.8), 0, 1)[..., None]
    img = img * (1 - v) + deep * v
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1.0, size=(h, w, 1)).astype(np.float32)
    img = img - np.abs(n) * 1.6 if LIGHT else img + n * 2.2     # light: multiply-like (only darkens); dark: as original
    return np.clip(img, 0, 255).astype(np.uint8)


def dot_grid(step=0.5, extent=(13, 8), radius=0.011, color=DIM, opacity=0.5):
    """One VMobject holding every grid dot (one Cairo path: far cheaper than hundreds of Dot mobjects)."""
    m = VMobject(stroke_width=0, fill_color=color, fill_opacity=opacity)
    xs = np.arange(-extent[0], extent[0] + 1e-6, step)
    ys = np.arange(-extent[1], extent[1] + 1e-6, step)
    k = 0.5523 * radius
    for x in xs:
        for y in ys:
            c = np.array([x, y, 0.0])
            pts = [c + [radius, 0, 0], c + [radius, k, 0], c + [k, radius, 0], c + [0, radius, 0],
                   c + [0, radius, 0], c + [-k, radius, 0], c + [-radius, k, 0], c + [-radius, 0, 0],
                   c + [-radius, 0, 0], c + [-radius, -k, 0], c + [-k, -radius, 0], c + [0, -radius, 0],
                   c + [0, -radius, 0], c + [k, -radius, 0], c + [radius, -k, 0], c + [radius, 0, 0]]
            m.append_points(np.array(pts))
    m.set_z_index(Z["grid"])
    return m
