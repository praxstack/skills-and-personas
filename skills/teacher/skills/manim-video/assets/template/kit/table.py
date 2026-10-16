"""Array rows and DP tables that fill cell by cell.

    row = ArrayRow([0, INF, INF, INF], label="dist", header=["0", "1", "2", "3"])
    self.play(*row.appear())
    self.play(*row.set(1, 100, AMBER))            # cell flashes, old value rolls out, new rolls in
    nxt = row.clone_below("next")                  # a copy one row down (read old, write new)
    self.play(*row.pull(nxt, 1, MINT))             # dist = next: the value travels up from nxt into row

    tab = DPTable(rows=["round 0", "round 1"], cols=["0", "1", "2", "3"], init=INF)
    self.play(*tab.set(1, 3, 700, AMBER))
INF (or None) shows as ∞.
"""
from manim import (DOWN, LEFT, RIGHT, UP, FadeIn, FadeOut, Indicate, LaggedStart, RoundedRectangle, Transform,
                   VGroup, rate_functions)

from .fx import glow, roll
from .style import AMBER, DIM, INK, MUTED, PANEL, SIZE, Z, ink
from .text import Mono, T

INF = 10 ** 9


def show(v):
    return "∞" if v is None or (isinstance(v, (int, float)) and v >= INF) else str(v)


class ArrayRow(VGroup):
    def __init__(self, values, label=None, header=None, cell=0.92, height=0.74, size=34, gap=0.12, label_w=None):
        super().__init__()
        self.size, self.cell_w, self.cell_h = size, cell, height
        self.values = list(values)
        self.cells = VGroup(*[RoundedRectangle(corner_radius=0.12, width=cell, height=height, stroke_color=DIM,
                                               stroke_width=2, fill_color=PANEL, fill_opacity=0.96)
                              for _ in values]).arrange(RIGHT, buff=gap)
        self.vals = VGroup(*[Mono(show(v), size, MUTED if show(v) == "∞" else INK, weight="BOLD").move_to(c)
                             for v, c in zip(values, self.cells)])
        self.add(self.cells, self.vals)
        self.label = None
        if label:
            self.label = T(label, SIZE["small"], MUTED, "BOLD")
            self.label.next_to(self.cells, LEFT, buff=0.3)
            self.add(self.label)
        self.header = None
        if header:
            self.header = VGroup(*[T(str(h), SIZE["small"], MUTED, "BOLD").next_to(c, UP, buff=0.14)
                                   for h, c in zip(header, self.cells)])
            self.add(self.header)
        self.glows = VGroup()
        self.add(self.glows)
        self.set_z_index(Z["panel"])
        self.vals.set_z_index(Z["panel_text"])

    def appear(self, lag=0.08):
        anims = [LaggedStart(*[FadeIn(VGroup(c, v), shift=UP * 0.15) for c, v in zip(self.cells, self.vals)],
                             lag_ratio=lag)]
        if self.label is not None:
            anims.append(FadeIn(self.label, shift=RIGHT * 0.15))
        if self.header is not None:
            anims.append(FadeIn(self.header))
        return anims

    def k(self):
        """The row's current scale relative to its built size (it may have been posed with the subject)."""
        return self.cells[0].width / self.cell_w

    def set(self, i, v, color=AMBER, keep_color=True):
        """Write v into cell i: the cell lights up and the number rolls. Unpack into play().
        The new number is scaled to the row's current size (a posed row would otherwise get full-size text)."""
        new = Mono(show(v), self.size, color if keep_color else INK, weight="BOLD").scale(self.k())
        new.set_z_index(Z["panel_text"])
        new.move_to(self.cells[i])
        old = self.vals[i]
        anims = roll(old, new)
        self.vals.submobjects[i] = new
        self.values[i] = v
        anims.append(self.cells[i].animate.set_stroke(ink(color), width=3.5).set_fill(PANEL, opacity=1))
        g = glow(self.cells[i], color, width=2, layers=(6, 14), opacities=(0.3, 0.1))
        self.glows.add(g)
        anims.append(FadeIn(g))
        return anims

    def pull(self, src, i, color=None):
        """Copy src's value i into cell i (dist = next): the number travels from src's cell into this one at full
        opacity while the old value fades, so the copy is seen (and readable) the whole way. Unpack into play()."""
        color = color or AMBER
        new = src.vals[i].copy()
        new.set_z_index(Z["panel_text"] + 1)
        target = Mono(show(src.values[i]), self.size, color, weight="BOLD").scale(self.k()).move_to(self.cells[i])
        target.set_z_index(Z["panel_text"] + 1)
        old = self.vals[i]
        self.vals.submobjects[i] = new
        self.values[i] = src.values[i]
        g = glow(self.cells[i], color, width=2, layers=(6, 14), opacities=(0.3, 0.1))
        self.glows.add(g)
        return [Transform(new, target, rate_func=rate_functions.ease_in_out_cubic),
                FadeOut(old, rate_func=lambda t: min(1.0, 2.5 * t)),
                self.cells[i].animate.set_stroke(ink(color), width=3.5), FadeIn(g)]

    def focus(self, i, color=AMBER):
        """Briefly point at a cell (reads): the cell and its value swell a little and a ring in `color` leaves it.
        The value stays readable (a colour Indicate on the filled cell flooded it: 100 on cyan read 1.6:1)."""
        ring = self.cells[i].copy().set_fill(opacity=0).set_stroke(ink(color), width=5)
        ring.set_z_index(Z["panel_text"] + 1)
        return [Indicate(VGroup(self.cells[i], self.vals[i]), color=None, scale_factor=1.08),
                FadeOut(ring, scale=1.25, rate_func=rate_functions.ease_out_cubic)]

    def calm(self):
        """All cells back to resting stroke, glows off."""
        anims = [c.animate.set_stroke(DIM, width=2) for c in self.cells]
        if len(self.glows):
            anims.append(self.glows.animate.set_opacity(0))
        return anims

    def clone_below(self, label=None, buff=0.32):
        """A copy of this row (same values) placed underneath, e.g. next = dist."""
        r = ArrayRow(self.values, label=label or (self.label.text if self.label is not None else None),
                     cell=self.cell_w, height=self.cell_h, size=self.size)
        r.scale(self.k())
        r.next_to(self, DOWN, buff=buff).align_to(self.cells, RIGHT)
        r.shift(RIGHT * (self.cells.get_center()[0] - r.cells.get_center()[0]))
        return r


class DPTable(VGroup):
    """Rows of ArrayRow under one header. set(r, c, v) fills one cell."""

    def __init__(self, rows, cols, init=INF, cell=0.92, height=0.7, size=32, row_gap=0.16):
        super().__init__()
        self.rows = []
        for j, name in enumerate(rows):
            r = ArrayRow([init] * len(cols), label=name, header=cols if j == 0 else None, cell=cell,
                         height=height, size=size)
            self.rows.append(r)
        VGroup(*self.rows).arrange(DOWN, buff=row_gap, aligned_edge=RIGHT)
        self.add(*self.rows)

    def appear(self, lag=0.12):
        return [LaggedStart(*[a for r in self.rows for a in r.appear()], lag_ratio=lag)]

    def set(self, r, c, v, color=AMBER):
        return self.rows[r].set(c, v, color)
