"""The complexity ladder: one rung per approach, bar length = cost, the pick marked.

    lad = Ladder([("Brute-force DFS", "O(n^(k+1))", "O(k)", 1.0),
                  ("DFS + memo",      "O(k·E)",     "O(n·k)", 0.42),
                  ("Bellman-Ford",    "O(k·E)",     "O(n)",   0.30)])
    self.play(*lad.reveal(0))     # rung 0 (bottom) grows; rungs climb upward, cheaper as you go up
    self.play(*lad.pick(2))       # mint outline, glow and an INTERVIEW PICK badge that pops
Superscripts in the O(...) strings are real superscripts (Rich text).
"""
from manim import (DOWN, LEFT, RIGHT, UP, FadeIn, GrowFromEdge, Line, ManimColor, RoundedRectangle, VGroup,
                   interpolate_color, rate_functions)

from .fx import conceal, glow, unconceal
from .style import BG, COMIC, CORAL, DIM, INK, MINT, MUTED, PANEL, AMBER, SIZE, THEMED, Z, ink, on_fill
from .text import H, Rich, T


def _cost_color(cost):
    """Bar colour: CORAL (costly) to MINT (cheap). A theme goes through COMIC (its gold) on the way, because a
    straight mix of its red and green is a muddy grey in the middle."""
    k = 1 - max(0.0, min(1.0, cost))
    if not THEMED:
        return interpolate_color(ManimColor(CORAL), ManimColor(MINT), k)
    if k < 0.5:
        return interpolate_color(ManimColor(CORAL), ManimColor(COMIC), k * 2)
    return interpolate_color(ManimColor(COMIC), ManimColor(MINT), k * 2 - 1)


class Ladder(VGroup):
    TIME_W = 2.3

    def __init__(self, rungs, bar_max=3.8, rung_h=0.78, gap=0.36, name_w=3.3, size=34, headers=("TIME", "SPACE")):
        super().__init__()
        self.rungs = []
        rail_h = len(rungs) * (rung_h + gap)
        for i, (name, tc, sc, cost) in enumerate(rungs):
            y = i * (rung_h + gap)
            col = _cost_color(cost)
            nm = T(name, size, INK, "BOLD")
            if nm.width > name_w:
                nm.scale_to_fit_width(name_w)
            nm.move_to([0, y, 0]).align_to([-name_w, 0, 0], LEFT)
            track = RoundedRectangle(corner_radius=rung_h / 2.6, width=bar_max, height=rung_h * 0.58,
                                     stroke_color=DIM, stroke_width=1.2, fill_color=PANEL, fill_opacity=0.9)
            track.move_to([0.35 + bar_max / 2, y, 0])
            bar = RoundedRectangle(corner_radius=rung_h / 2.6, width=max(0.3, bar_max * cost), height=rung_h * 0.58,
                                   stroke_width=0, fill_color=col, fill_opacity=0.92)
            bar.align_to(track, LEFT).match_y(track)
            t = Rich(tc, size, INK, "BOLD")
            t.move_to([track.get_right()[0] + 0.3 + self.TIME_W / 2, y, 0])
            s = Rich(sc, SIZE["small"], MUTED, "BOLD") if sc else VGroup()
            if sc:
                s.move_to([track.get_right()[0] + 0.3 + self.TIME_W + 0.3 + s.width / 2, y, 0])
            rung = VGroup(nm, track, bar, t, s)
            rung.label, rung.track, rung.bar, rung.time, rung.space, rung.tone = nm, track, bar, t, s, col
            self.rungs.append(rung)
            self.add(rung)
        rail = Line([-name_w - 0.35, -rung_h / 2 - 0.1, 0], [-name_w - 0.35, rail_h - gap - rung_h / 2 + 0.1, 0],
                    stroke_color=DIM, stroke_width=3)
        self.rail = rail
        self.add(rail)
        self.heads = VGroup()
        if headers:
            x_t = self.rungs[0].track.get_right()[0] + 0.3 + self.TIME_W / 2
            top = rail_h - gap - rung_h / 2 + 0.42
            ht = T(headers[0], SIZE["small"], MUTED, "BOLD").move_to([x_t, top, 0])
            hs = T(headers[1], SIZE["small"], MUTED, "BOLD").move_to([x_t + self.TIME_W / 2 + 0.3, top, 0])
            hs.align_to([x_t + self.TIME_W / 2 + 0.3, 0, 0], LEFT)
            self.heads = VGroup(ht, hs)
            self.add(self.heads)
        self.center()
        self.set_z_index(Z["panel"])
        for r in self.rungs:
            r.time.set_z_index(Z["panel_text"])
            r.label.set_z_index(Z["panel_text"])

    def hide(self):
        """Rungs and headers invisible (layout kept); reveal(i) / show_heads() bring them in."""
        for r in self.rungs:
            conceal(r)
        conceal(self.heads)
        return self

    def show_heads(self):
        unconceal(self.heads)
        return [FadeIn(self.heads)]

    def reveal(self, i):
        r = unconceal(self.rungs[i])
        return [FadeIn(r.label, shift=RIGHT * 0.2), FadeIn(r.track),
                GrowFromEdge(r.bar, LEFT, rate_func=rate_functions.ease_out_cubic),
                FadeIn(r.time, shift=LEFT * 0.2), FadeIn(r.space, shift=LEFT * 0.2)]

    def pick(self, i, label="INTERVIEW PICK"):
        r = self.rungs[i]
        box = RoundedRectangle(corner_radius=0.2, width=r.width + 0.5, height=r.height + 0.36, stroke_color=ink(MINT),
                               stroke_width=3, fill_opacity=0).move_to(r)
        gl = glow(box, MINT, width=3, layers=(8, 18), opacities=(0.28, 0.1))
        tag = T(label, SIZE["small"], on_fill(MINT), "BOLD")
        pill = RoundedRectangle(corner_radius=0.16, width=tag.width + 0.4, height=tag.height + 0.24, stroke_width=0,
                                fill_color=MINT, fill_opacity=1)
        badge = VGroup(pill, tag.move_to(pill)).next_to(box, UP, buff=-0.18).align_to(box, LEFT).shift(RIGHT * 0.3)
        badge.rotate(-0.05)
        badge.set_z_index(Z["callout"])
        self.pick_box = VGroup(gl, box, badge)
        self.add(self.pick_box)
        return [FadeIn(gl), FadeIn(box, scale=1.04),
                FadeIn(badge, scale=1.6, rate_func=rate_functions.ease_out_back)]
