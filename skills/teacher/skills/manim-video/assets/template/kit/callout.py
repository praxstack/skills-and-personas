"""Comic callouts: a jagged starburst with a punchy word ("700!", "POP!", "TOO MANY STOPS!").

    b = burst("700!").next_to(graph.nodes[3], UR, buff=-0.1)
    pop(self, b)                                   # scales in with overshoot and a little wobble
    pop(self, b, hold_until=L["p4"].end - 0.4)     # ...and leaves by itself at that film time
Pair it with an sfx cue in script.json ("sfx": [{"at": 2.1, "kind": "pop"}]).
"""
import numpy as np
from manim import (DOWN, RIGHT, UP, FadeIn, FadeOut, LineJointType, Polygon, Rotate, VGroup, rate_functions)

from .style import COMIC, COMIC_INK, CORAL, THEMED, Z
from .text import H


def starburst(radius=1.0, spikes=13, inner=0.62, jitter=0.12, seed=4):
    rng = np.random.default_rng(seed)
    pts = []
    for i in range(spikes * 2):
        a = np.pi * i / spikes + 0.15
        r = radius * (1 if i % 2 == 0 else inner) * (1 + rng.uniform(-jitter, jitter))
        pts.append([r * np.cos(a), r * np.sin(a) * 0.78, 0])
    return Polygon(*pts)


def burst(word, fill=COMIC, ink=COMIC_INK, text_color=CORAL, size=72, tilt=-0.14, seed=4, pad=1.0):
    """A comic burst sized to its word. Returns a VGroup (shadow, star, word)."""
    w = H(word, size, text_color, "HEAVY")
    if THEMED:                       # a theme: the word keeps the bright fill (H() gave it the ink); its dark
        w.set_fill(text_color)       # outline (COMIC_INK) carries the contrast on the star
    w.set_stroke(ink, width=7, background=True)
    for m in w.get_family():
        m.joint_type = LineJointType.ROUND                 # no miter spikes on the outline
    w.apply_matrix([[1, 0.18], [0, 1]])                  # comic slant
    r = max(w.width * 0.68, w.height * 1.25) * pad + 0.35
    star = starburst(r, seed=seed).set_fill(fill, 1).set_stroke(ink, width=6)
    shadow = starburst(r, seed=seed).set_fill(ink, 0.8).set_stroke(width=0).shift(RIGHT * 0.1 + DOWN * 0.12)
    g = VGroup(shadow, star, w.move_to(star))
    g.rotate(tilt)
    g.set_z_index(Z["callout"])
    w.set_z_index(Z["callout"] + 1)
    g.word, g.star = w, star
    return g


def pop(scene, b, hold_until=None, run_time=0.45):
    """Scale in with overshoot and a wobble; if hold_until is given, pop out at that film time."""
    scene.play(FadeIn(b, scale=0.2, rate_func=rate_functions.ease_out_back), run_time=run_time)
    scene.play(Rotate(b, 0.08, rate_func=rate_functions.wiggle), run_time=0.3)
    if hold_until is not None:
        scene.until(hold_until)
        scene.play(FadeOut(b, scale=1.3), run_time=0.25)
    return b
