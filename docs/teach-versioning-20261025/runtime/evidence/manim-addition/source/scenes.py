"""Original authored mathematical vector addition; coordinates drive all endpoints."""
import numpy as np
from manim import Arrow, Create, Dot, FadeIn, Line, Text
from kit.film import FilmScene

ORIGIN = np.array([-3.0, -1.2, 0.0])
UNIT = 1.8
U = np.array([2.0, 0.0, 0.0])
V = np.array([0.0, 1.0, 0.0])


def point(vector):
    return ORIGIN + UNIT*np.asarray(vector, dtype=float)


def label(text, at, color='#F4F1E8', size=34):
    return Text(text, font_size=size, color=color).move_to(at)


class VectorAddition(FilmScene):
    chapters = [1]
    grid = False
    drift = 0

    def film(self):
        title = label('Vector addition: head to tail', [0, 2.75, 0], size=46)
        x_axis = Arrow(point([-0.15,0,0]), point([2.6,0,0]), color='#B7C8CD', stroke_width=2, buff=0)
        y_axis = Arrow(point([0,-0.15,0]), point([0,1.65,0]), color='#B7C8CD', stroke_width=2, buff=0)
        origin = label('0', point([-0.15,-0.2,0]), size=26)
        x_labels = [label(str(i), point([i,-0.2,0]), size=26) for i in [1,2]]
        y_one = label('1', point([-0.2,1,0]), size=26)
        ticks = [Line(point([i,-0.04,0]), point([i,0.04,0]), color='#B7C8CD', stroke_width=2) for i in [1,2]]
        ticks += [Line(point([-0.04,1,0]), point([0.04,1,0]), color='#B7C8CD', stroke_width=2)]
        u = Arrow(point([0,0,0]), point(U), color='#75D6BC', buff=0, stroke_width=7)
        v = Arrow(point(U), point(U+V), color='#F3C969', buff=0, stroke_width=7)
        result = Arrow(point([0,0,0]), point(U+V), color='#8FC8FF', buff=0, stroke_width=7)
        u_label = label('u = (2, 0)', point([1,-0.55,0]), '#75D6BC')
        v_label = label('v = (0, 1)', point([2.75,0.5,0]), '#F3C969')
        r_label = label('u + v = (2, 1)', point([0.9,1.1,0]), '#8FC8FF')
        endpoint = Dot(point(U+V), radius=0.065, color='#8FC8FF')
        endpoint_label = label('(2, 1)', point([2.42,1.2,0]), '#8FC8FF', size=30)
        self.add(title, x_axis, y_axis, origin, *x_labels, y_one, *ticks)
        self.play_until(0.8, Create(u), FadeIn(u_label))
        self.play_until(1.8, Create(v), FadeIn(v_label))
        self.play_until(2.8, Create(result), FadeIn(r_label), FadeIn(endpoint), FadeIn(endpoint_label))
        self.until(4.0)
