"""Light and emphasis: glows, soft shadows, ripples, pulses, number rolls.

    glow(edge_line, AMBER)          VGroup of wide translucent copies; add it behind the thing that glows
    soft_shadow(card)               blurred-looking drop shadow (stacked offsets) for cards and nodes
    ripple(node, CYAN)              an expanding ring that fades (play it)
    pulse(mob, color)               a quick scale + color flash (play it)
    roll(old_text, new_text)        animations for a number that rolls to a new value (unpack into play)
"""
import numpy as np
from manim import (DOWN, UP, Circle, FadeIn, FadeOut, Indicate, LineJointType, RoundedRectangle, VGroup, VMobject,
                   rate_functions)

from .style import LIGHT, SHADOW, SHADOW_K, Z, ink


def glow(mob, color, width=None, layers=(10, 20, 34), opacities=(0.32, 0.14, 0.06), text=False):
    """Translucent wide-stroke copies of `mob` (a line, arc or outline). Put it behind `mob`.

    For filled shapes use halo() instead. On a light theme a glow reads as a smudge, so it becomes a narrow tint
    of the colour with a soft `SHADOW` under it, and a glow behind text (text=True) is left out (it would sit
    under the words and cut their contrast)."""
    base_w = width if width is not None else max(2.0, mob.get_stroke_width())
    g = VGroup()
    if LIGHT:
        if text:
            g.set_z_index(Z["glow"])
            return g
        specs = [(color, layers[0] * 0.6, opacities[0] * 0.55, 0.0)]
        specs += [(SHADOW, w * 0.7, o * 0.35, -0.03) for w, o in zip(layers[1:], opacities[1:])]
        for col, w, o, dy in specs:
            c = mob.copy().clear_updaters()
            c.set_fill(opacity=0)
            c.set_stroke(col, width=base_w + w, opacity=o)
            c.shift([0, dy, 0])
            for m in c.get_family():
                m.joint_type = LineJointType.ROUND
            g.add(c)
        g.set_z_index(Z["glow"])
        return g
    for w, o in zip(layers, opacities):
        c = mob.copy().clear_updaters()
        c.set_fill(opacity=0)
        c.set_stroke(color, width=base_w + w, opacity=o)
        for m in c.get_family():                 # round joins: thick strokes on sharp glyph corners spike otherwise
            m.joint_type = LineJointType.ROUND
        g.add(c)
    g.set_z_index(Z["glow"])
    return g


def halo(center, radius, color, layers=5, spread=0.55, opacity=0.18):
    """Soft radial light around a point: concentric translucent discs."""
    g = VGroup()
    if LIGHT:                    # a light ground: a tinted disc, a little tighter (a wide wash reads as a stain)
        spread, opacity = spread * 0.7, opacity * 0.75
    for i in range(layers):
        r = radius * (1 + spread * (i + 1) / layers)
        g.add(Circle(radius=r, stroke_width=0, fill_color=color, fill_opacity=opacity * (1 - i / layers) ** 1.5)
              .move_to(center))
    g.set_z_index(Z["glow"])
    return g


def soft_shadow(mob, offset=(0.06, -0.12), spread=0.05, layers=4, opacity=0.34, corner_radius=0.18):
    """A drop shadow for a card-like mobject: stacked rounded rects growing and fading."""
    w, h = mob.width, mob.height
    c = mob.get_center() + np.array([offset[0], offset[1], 0])
    g = VGroup()
    for i in range(layers):
        k = (i + 1) / layers
        g.add(RoundedRectangle(corner_radius=corner_radius + spread * i, width=w + 2 * spread * i * 2,
                               height=h + 2 * spread * i * 2, stroke_width=0, fill_color=SHADOW,
                               fill_opacity=(opacity * (1 - k) + 0.04) * SHADOW_K).move_to(c))
    g.set_z_index(getattr(mob, "z_index", 0) - 1)
    return g


def disc_shadow(center, radius, offset=(0.04, -0.09), opacity=0.4):
    g = VGroup(*[Circle(radius=radius * (1 + 0.12 * i), stroke_width=0, fill_color=SHADOW,
                        fill_opacity=opacity * (1 - i / 3) * 0.6 * SHADOW_K)
                 .move_to(np.array(center) + np.array([offset[0], offset[1], 0])) for i in range(3)])
    return g


def ripple(mob, color, scale=1.9, width=6):
    """An expanding ring that fades: 'look here'."""
    r = max(mob.width, mob.height) / 2 + 0.03
    ring = Circle(radius=r, stroke_color=ink(color), stroke_width=width).move_to(mob.get_center())
    ring.set_z_index(Z["token"])
    return FadeOut(ring, scale=scale, rate_func=rate_functions.ease_out_cubic)


def pulse(mob, color=None, scale=1.15):
    """Scale + colour flash. The colour goes on fills too: use it on text or strokes, not on a filled cell with
    text on it (the cell floods and its text vanishes; ArrayRow.focus rings the cell instead)."""
    return Indicate(mob, color=ink(color), scale_factor=scale) if color else Indicate(mob, scale_factor=scale)


def roll(old, new, direction=UP, shift=0.32):
    """Old value slides out, new value slides in from the opposite side (both are Text mobjects).
    Unpack the returned list into self.play(...). After it, keep a reference to `new`, not `old`."""
    new.move_to(old)
    return [FadeOut(old, shift=direction * shift, rate_func=rate_functions.ease_in_cubic),
            FadeIn(new, shift=direction * shift, rate_func=rate_functions.ease_out_cubic)]


def conceal(mob):
    """Make mob invisible but keep it in its group (so it still moves and scales with the group).
    Each part's own fill/stroke opacities are remembered and put back exactly by unconceal(); never use
    set_opacity(1) to show things again: it would also make zero-opacity fills (a ring's inside) solid."""
    for m in mob.get_family():
        if not hasattr(m, "fill_rgbas") or getattr(m, "_vis", None) is not None:
            continue
        m._vis = (m.fill_rgbas[:, 3].copy(), m.stroke_rgbas[:, 3].copy(),
                  m.background_stroke_rgbas[:, 3].copy() if hasattr(m, "background_stroke_rgbas") else None)
        m.fill_rgbas[:, 3] = 0
        m.stroke_rgbas[:, 3] = 0
        if hasattr(m, "background_stroke_rgbas"):
            m.background_stroke_rgbas[:, 3] = 0
    return mob


def unconceal(mob):
    """Restore what conceal() hid. Call it right before the animation that brings the thing in."""
    for m in mob.get_family():
        v = getattr(m, "_vis", None)
        if v is None:
            continue
        f, s_, b = v
        if len(m.fill_rgbas) == len(f):
            m.fill_rgbas[:, 3] = f
        if len(m.stroke_rgbas) == len(s_):
            m.stroke_rgbas[:, 3] = s_
        if b is not None and len(m.background_stroke_rgbas) == len(b):
            m.background_stroke_rgbas[:, 3] = b
        m._vis = None
    return mob


def straight_path(points):
    """A polyline through points (used for tokens travelling along routes)."""
    m = VMobject()
    m.set_points_as_corners([np.array(p) for p in points])
    return m
