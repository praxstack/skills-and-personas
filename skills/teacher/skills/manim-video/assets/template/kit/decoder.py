"""InputDecoder: the raw input text on screen, whose entries fly into the subject.

    dec = InputDecoder("flights", [[0, 1, 100], [1, 2, 100], ...], fields=("from", "to", "price"),
                       more=[("src = 0", CYAN), ("dst = 3", AMBER), ("k = 1", CORAL)])
    dec.to_corner(...) / dec.move_to(...)
    self.play(*dec.write())                                     # the text types itself in
    self.play(*dec.show_more(0))                                # extra inputs given as more=[("src = 0", CYAN)]
    dec.send(self, 0, graph, (0, 1), run_time=0.9)              # entry 0 lights, its price flies onto edge 0->1
                                                                # as the edge grows; the from/to cities ripple
The legend `[from, to, price]` is coloured like the fields so the mapping text -> picture is explicit.
"""
import numpy as np
from manim import (DOWN, LEFT, RIGHT, UP, FadeIn, Indicate, LaggedStart, RoundedRectangle, Transform, VGroup,
                   rate_functions)

from .fx import conceal, ripple, soft_shadow, unconceal
from .style import AMBER, CYAN, DIM, INK, MUTED, PANEL, SIZE, VIOLET, Z, ink
from .text import Mono, T

FIELD_COLORS = (CYAN, VIOLET, AMBER)


class InputDecoder(VGroup):
    def __init__(self, name, entries, fields=("from", "to", "price"), colors=FIELD_COLORS, per_row=1, size=32,
                 panel=True, title="INPUT", more=(), more_size=None):
        super().__init__()
        self.entries_data = entries
        head = Mono(f"{name} = [", size, INK)
        self.head = head
        rows, self.entries = VGroup(), []
        for start in range(0, len(entries), per_row):
            chunk = entries[start:start + per_row]
            parts = [("[" + ",".join(str(x) for x in e) + "]") for e in chunk]
            line = ", ".join(parts) + ("," if start + per_row < len(entries) else "")
            txt = Mono(line, size, MUTED)
            # map glyphs (Text drops spaces) to entries and fields
            k = 0
            for e, p in zip(chunk, parts):
                glyphs = txt[k:k + len(p)]
                ent = VGroup(*glyphs)
                ent.fields = []
                j = 1
                for fi, x in enumerate(e):
                    sx = str(x)
                    fg = VGroup(*glyphs[j:j + len(sx)])
                    fg.set_color(ink(colors[fi % len(colors)]))
                    ent.fields.append(fg)
                    j += len(sx) + 1
                self.entries.append(ent)
                k += len(p) + 1          # the comma after the entry (spaces are not glyphs)
            rows.add(txt)
        rows.arrange(DOWN, buff=0.16, aligned_edge=LEFT)
        close = Mono("]", size, INK)
        body = VGroup(head, rows, close)
        rows.next_to(head, DOWN, buff=0.16, aligned_edge=LEFT).shift(RIGHT * 0.45)
        close.next_to(rows, DOWN, buff=0.16, aligned_edge=LEFT).align_to(head, LEFT)
        legend = Mono("[" + ", ".join(fields) + "]", SIZE["small"], MUTED)
        k = 1
        for i, f in enumerate(fields):
            legend[k:k + len(f)].set_color(ink(colors[i % len(colors)]))
            k += len(f) + 1
        legend.next_to(head, RIGHT, buff=0.4)
        self.legend = legend
        self.rows, self.close = rows, close
        # further inputs shown later (src = 0, k = 1): laid out now so the panel is sized for them
        self.more = VGroup()
        anchor = close
        for i, item in enumerate(more):
            txt, col = (item, INK) if isinstance(item, str) else item
            # the extra inputs are short lowercase names (src, k): a size up, so "src" (x-height only) still reads
            # at 26 px or more
            m = Mono(txt, more_size or size + 6, col).next_to(anchor, DOWN, buff=0.3 if i == 0 else 0.14,
                                                              aligned_edge=LEFT)
            self.more.add(m)
            anchor = m
        content = VGroup(body, legend, self.more)
        if panel:
            kicker = T(title, SIZE["small"], MUTED, "BOLD")
            kicker.next_to(content, UP, buff=0.3).align_to(content, LEFT)
            box = RoundedRectangle(corner_radius=0.2, width=max(content.width, kicker.width) + 0.7,
                                   height=content.height + kicker.height + 0.95, stroke_color=DIM, stroke_width=1.5,
                                   fill_color=PANEL, fill_opacity=0.92)
            box.move_to(VGroup(content, kicker)).shift(DOWN * 0.02)
            self.box, self.kicker = box, kicker
            self.shadow = soft_shadow(box)
            self.add(self.shadow, box, kicker)
        else:
            self.box = self.kicker = self.shadow = None
        self.add(content)
        for m in self.more:
            conceal(m)
        self.set_z_index(Z["panel"])
        content.set_z_index(Z["panel_text"])
        if self.kicker is not None:
            self.kicker.set_z_index(Z["panel_text"])

    def write(self, lag=0.08):
        """The panel slides in and the text types itself in (entry by entry)."""
        anims = []
        if self.box is not None:
            anims.append(FadeIn(VGroup(self.shadow, self.box, self.kicker), shift=LEFT * 0.3))
        anims.append(FadeIn(self.head, shift=RIGHT * 0.1))
        anims.append(FadeIn(self.legend, shift=UP * 0.1))
        anims.append(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.15) for r in self.rows], lag_ratio=lag))
        anims.append(FadeIn(self.close))
        return anims

    def show_more(self, i):
        """Reveal the i-th extra input line (given as more=[...] at construction). Unpack into play()."""
        m = unconceal(self.more[i])
        return [FadeIn(m, shift=UP * 0.12)]

    def send(self, scene, i, graph, edge, run_time=0.9, grow=True):
        """Entry i lights up; its last field (the weight) flies to the edge label while the edge grows,
        and the from/to cities ripple in their field colours. Plays and finalises everything."""
        u, v = edge
        ent = self.entries[i]
        lab = graph.weights.get((u, v))
        anims = [Indicate(ent, scale_factor=1.12, color=None)]
        fly = None
        if lab is not None:
            fly = ent.fields[-1].copy()
            target = unconceal(lab.txt.copy())
            anims.append(Transform(fly, target, path_arc=-0.6, rate_func=rate_functions.ease_in_out_cubic))
            unconceal(lab.pill)
            anims.append(FadeIn(lab.pill, scale=0.6))
        if grow:
            anims += graph.grow_edge(u, v)
        anims.append(ripple(graph.nodes[u].disc, ent.fields[0].get_color()))
        anims.append(ripple(graph.nodes[v].disc, ent.fields[1].get_color()))
        scene.play(*anims, run_time=run_time)
        if fly is not None:
            scene.remove(fly)
            graph.show_weight(u, v)
        return ent
