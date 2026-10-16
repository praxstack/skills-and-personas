"""The persistent subject: a directed weighted graph, and a token that travels its routes.

    g = WGraph(nodes=[0, 1, 2, 3], edges=[(0, 1, 100), (1, 3, 600), ...], pos={0: (-3.4, 0), ...})
    self.play(*g.appear())                              # nodes pop, edges grow, weights fade in
    self.play(*g.light(1, 3, AMBER))                    # edge stays lit (colour + glow)
    self.play(g.fire(0, 1, CYAN))                       # a pulse runs along the edge (temporary)
    self.play(*g.mark(0, CYAN, "START"))                # ring colour + glow + a small tag
    tok = Token()                                        # the plane
    fly(self, g, tok, [0, 1, 3], until=L["p4"].said("seven hundred"), color=AMBER,
        on_edge=lambda i, u, v: [...])                  # flies the route, drawing a glowing trail, landing at `until`
    anims, marks = reject(g, 2, 3, "too many stops")     # an illegal move: coral fire, crossed disc, wiggle

Layout comes from data: pass `pos` (scene units) or let auto_layout() place the nodes (circle or force layout).
Every method returns animations; unpack them into self.play(...), never wrap them in AnimationGroup on a
sub-mobject (that re-adds it on top: the z-order jump seen in the first Manim film).

Labels keep their size: move or shrink the graph with g.place() (instant), g.pose() or g.settle() (animations),
which keep every weight and node number at least MIN_TEXT px on screen (style.py) and re-seat each weight pill
just clear of its edge. A plain g.scale() shrinks the labels with the graph (a 0.5x graph had 15 px weights).
"""
import numpy as np
from manim import (DOWN, LEFT, PI, RIGHT, TAU, UP, Arrow, Circle, Create, CurvedArrow, FadeIn, FadeOut,
                   GrowArrow, GrowFromCenter, LaggedStart, Line, MoveToTarget, Polygon, RoundedRectangle, ShowPassingFlash,
                   TracedPath, Transform, UpdateFromAlphaFunc, VectorizedPoint, VGroup, Wiggle, angle_of_vector,
                   normalize, rate_functions)

from .fx import conceal, disc_shadow, glow, halo, ripple, unconceal
from .style import (AMBER, BG_DEEP, CORAL, CYAN, DIM, EDGE, EDGE_UNDER, INK, MIN_TEXT, MUTED, PANEL, PANEL_HI, SIZE, Z,
                    ink)
from .text import H, Mono, T


def auto_layout(nodes, edges, width=7.0, height=4.4, kind="auto", seed=3):
    """Positions for nodes when the data does not give them: a circle for small graphs, a force layout otherwise."""
    n = len(nodes)
    if kind == "circle" or (kind == "auto" and n <= 6):
        ang = [PI - TAU * i / n for i in range(n)]
        return {u: (width / 2 * np.cos(a), height / 2 * np.sin(a)) for u, a in zip(nodes, ang)}
    import networkx as nx
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from([(u, v) for u, v, *_ in edges])
    p = nx.kamada_kawai_layout(G)
    xs = np.array([p[u][0] for u in nodes])
    ys = np.array([p[u][1] for u in nodes])
    sx = width / max(1e-6, xs.max() - xs.min())
    sy = height / max(1e-6, ys.max() - ys.min())
    return {u: ((p[u][0] - xs.mean()) * sx, (p[u][1] - ys.mean()) * sy) for u in nodes}


class WGraph(VGroup):
    LABEL_GAP = 0.1          # space between an edge and its weight pill (scene units at scale 1)

    def __init__(self, nodes, edges, pos=None, radius=0.46, bend=None, label_side=None, weight_size=34,
                 node_size=38, node_color=PANEL_HI, ring_color=INK, edge_color=EDGE, show_weights=True,
                 min_text=MIN_TEXT):
        super().__init__()
        pos = pos or auto_layout(nodes, edges)
        self.r = radius
        self.edge_color = edge_color
        self.weight_size, self.node_size, self.min_text = weight_size, node_size, min_text
        self.nodes, self.edges, self.shafts, self.weights, self.glows, self.node_glows = {}, {}, {}, {}, {}, {}
        self.perps, self.anchors = {}, {}
        self.glow_layer, self.under_layer, self.edge_layer = VGroup(), VGroup(), VGroup()
        self.weight_layer, self.node_layer, self.anchor_layer = VGroup(), VGroup(), VGroup()
        self._weight_alpha = None          # saved opacities while pose(weights=False) hides the weights
        pairs = {(u, v) for u, v, *_ in edges}
        bend = dict(bend or {})
        for u, v, *_ in edges:          # two-way pairs curve apart automatically
            if (v, u) in pairs and (u, v) not in bend:
                bend[(u, v)] = -0.45
        for u in nodes:
            p = np.array([*pos[u], 0.0])
            disc = Circle(radius=radius, stroke_width=0).move_to(p)
            disc.set_fill([node_color, BG_DEEP], opacity=1)
            disc.set_sheen_direction(DOWN + RIGHT * 0.4)
            ring = Circle(radius=radius, stroke_color=ring_color, stroke_width=3.5, fill_opacity=0).move_to(p)
            lab = H(str(u), node_size, INK).move_to(p)
            shadow = disc_shadow(p, radius)
            node = VGroup(shadow, disc, ring, lab)
            node.disc, node.ring, node.lab, node.shadow = disc, ring, lab, shadow
            node.lab_h0 = lab.height
            self.nodes[u] = node
            self.node_layer.add(node)
        for e in edges:
            u, v = e[0], e[1]
            w = e[2] if len(e) > 2 else None
            a, b = np.array([*pos[u], 0.0]), np.array([*pos[v], 0.0])
            d = normalize(b - a)
            s, t = a + d * (radius + 0.08), b - d * (radius + 0.08)
            ang = bend.get((u, v), 0)
            if ang:
                arr = CurvedArrow(s, t, angle=ang, color=edge_color, stroke_width=4, tip_length=0.24)
            else:
                arr = Arrow(s, t, buff=0, color=edge_color, stroke_width=4, tip_length=0.24,
                            max_tip_length_to_length_ratio=0.25, max_stroke_width_to_length_ratio=12)
            under = arr.copy().set_stroke(EDGE_UNDER, width=10, opacity=0.55)
            under.set_fill(opacity=0)
            self.edges[(u, v)] = arr
            self.edge_layer.add(arr)
            self.under_layer.add(under)
            side = (label_side or {}).get((u, v), 1)
            perp = np.array([-d[1], d[0], 0.0]) * side
            mid = (a + b) / 2
            if ang:
                mid = mid + np.array([d[1], -d[0], 0.0]) * np.linalg.norm(b - a) * np.tan(ang / 4) / 2 * 1.0
            self.perps[(u, v)] = perp
            anchor = VectorizedPoint(mid)               # the edge's midpoint; moves and scales with the graph
            self.anchors[(u, v)] = anchor
            self.anchor_layer.add(anchor)
            if w is not None and show_weights:
                txt = Mono(str(w), weight_size, AMBER, weight="BOLD")
                pill = RoundedRectangle(corner_radius=0.12, width=txt.width + 0.3, height=txt.height + 0.22,
                                        stroke_color=DIM, stroke_width=1.5, fill_color=PANEL, fill_opacity=0.95)
                lab = VGroup(pill, txt).move_to(mid)
                lab.pill, lab.txt, lab.perp, lab.h0 = pill, txt, perp, pill.height
                self.weights[(u, v)] = lab
                self.weight_layer.add(lab)
        self.add(self.glow_layer, self.under_layer, self.edge_layer, self.weight_layer, self.node_layer,
                 self.anchor_layer)
        self.under_layer.set_z_index(Z["edge"] - 1)
        self.edge_layer.set_z_index(Z["edge"])
        self.weight_layer.set_z_index(Z["edge_label"])
        self.node_layer.set_z_index(Z["node"])
        self.fit_labels()

    # ------------------------------------------------------------------ labels that keep their size
    def fit_labels(self, m=None):
        """Size every weight pill and node number for the graph's current scale: they shrink with the graph
        but never below min_text px, and each pill sits LABEL_GAP clear of its edge on its side. Works on the
        graph itself or on its target (pose/settle call it). Returns m."""
        m = self if m is None else m
        s = m.scale_factor()
        kw = max(s, m.min_text / m.weight_size)
        for key, lab in m.weights.items():
            lab.scale(lab.h0 * kw / lab.pill.height)
            perp = lab.perp
            he = abs(perp[0]) * lab.pill.width / 2 + abs(perp[1]) * lab.pill.height / 2
            lab.move_to(m.anchors[key].get_center() + perp * (m.LABEL_GAP * s + he))
        kn = max(s, m.min_text / m.node_size)
        for node in m.nodes.values():
            node.lab.scale(node.lab_h0 * kn / node.lab.height).move_to(node.disc.get_center())
        return m

    def place(self, center=None, scale=None):
        """Move/scale the graph now (no animation), keeping the labels legible. `scale` is absolute (relative
        to the built size)."""
        if scale is not None:
            self.scale(scale / self.scale_factor())
        if center is not None:
            self.move_to([*center, 0])
        return self.fit_labels()

    def pose(self, center=None, scale=None, weights=None, **kw):
        """Animation moving the graph to a layout (absolute centre and scale), labels kept legible.
        weights=False fades the weight pills out (for a small decorative thumbnail, where they carry nothing),
        weights=True brings them back. One MoveToTarget on the whole group: play it alongside other mobjects'
        animations, never alongside the graph's own member animations (light, mark, reset), which it would undo;
        for rest + move use settle()."""
        self.generate_target()
        t = self.target
        if scale is not None:
            t.scale(scale / self.scale_factor())
        if center is not None:
            t.move_to([*center, 0])
        self.fit_labels(t)
        self._weights_to(t, weights)
        return MoveToTarget(self, **kw)

    def _weights_to(self, t, show):
        """Set the weight pills' opacity in target t: show=False hides them (remembering their opacities),
        show=True puts them back; None leaves them."""
        fam_live = self.weight_layer.get_family()
        fam_t = t.weight_layer.get_family()
        if show is False and self._weight_alpha is None:
            self._weight_alpha = [(m.fill_rgbas[:, 3].copy(), m.stroke_rgbas[:, 3].copy()) for m in fam_live]
            for m in fam_t:
                m.fill_rgbas[:, 3] = 0
                m.stroke_rgbas[:, 3] = 0
        elif show is True and self._weight_alpha is not None:
            for m, (f, st) in zip(fam_t, self._weight_alpha):
                if len(m.fill_rgbas) == len(f):
                    m.fill_rgbas[:, 3] = f
                if len(m.stroke_rgbas) == len(st):
                    m.stroke_rgbas[:, 3] = st
            self._weight_alpha = None

    def free_point(self, u, v, w, h, off=0.0, pad=0.02, fracs=(0.5, 0.4, 0.6, 0.3, 0.7, 0.22, 0.78, 0.15, 0.85)):
        """A point along edge (u, v), `off` units to the side away from its weight pill, where a w x h box
        keeps `pad` clear of every weight pill and node: the first free one of `fracs` (fractions of the edge)."""
        perp = -self.perps[(u, v)]
        sh = self.shaft(u, v)
        boxes = [(m.get_center(), m.width / 2, m.height / 2) for m in self.weights.values()]
        boxes += [(n.disc.get_center(), n.disc.width / 2, n.disc.height / 2) for n in self.nodes.values()]
        for f in fracs:
            p = sh.point_from_proportion(f) + perp * off
            if all(abs(p[0] - c[0]) > w / 2 + hw + pad or abs(p[1] - c[1]) > h / 2 + hh + pad
                   for c, hw, hh in boxes):
                return p
        return sh.point_from_proportion(0.5) + perp * off

    def beside(self, u, v, mob, buff=0.1, pad=0.12):
        """Where to put `mob` (a badge, a count) next to edge (u, v): on the side away from its weight pill and
        clear of every other pill and node. Returns a point; mob.move_to(g.beside(0, 1, mob))."""
        perp = -self.perps[(u, v)]
        he = abs(perp[0]) * mob.width / 2 + abs(perp[1]) * mob.height / 2
        return self.free_point(u, v, mob.width, mob.height, off=buff + he, pad=pad)

    # ------------------------------------------------------------------ geometry
    def c(self, u):
        return self.nodes[u].disc.get_center()

    def ring(self, u):
        return self.nodes[u].ring

    def edge(self, u, v):
        return self.edges[(u, v)]

    def shaft(self, u, v):
        """A tip-less copy of the edge's current shape (for glows, trails and pulses)."""
        s = self.edges[(u, v)].copy()
        s.pop_tips()
        s.clear_updaters()
        return s

    def scale_factor(self):
        return self.nodes[next(iter(self.nodes))].disc.width / (2 * self.r)

    # ------------------------------------------------------------------ appearance
    def hide(self):
        """Start with nothing shown; the layout stays intact and moves with the group. Parts come back with
        appear(), appear_nodes(), grow_edge() and show_weight()."""
        for layer in (self.edge_layer, self.under_layer, self.weight_layer, self.node_layer):
            conceal(layer)
        return self

    def appear(self, lag=0.12):
        """Nodes pop with overshoot, then edges grow and weights fade in."""
        for layer in (self.edge_layer, self.under_layer, self.weight_layer, self.node_layer):
            unconceal(layer)
        return [LaggedStart(*[GrowFromCenter(n, rate_func=rate_functions.ease_out_back) for n in self.node_layer],
                            lag_ratio=lag),
                LaggedStart(*[GrowArrow(e) for e in self.edge_layer], lag_ratio=lag),
                Create(self.under_layer, lag_ratio=0),
                LaggedStart(*[FadeIn(w, scale=0.6) for w in self.weight_layer], lag_ratio=lag)]

    def appear_nodes(self, lag=0.15):
        """Only the nodes (edges come later, e.g. from an InputDecoder)."""
        unconceal(self.node_layer)
        return [LaggedStart(*[GrowFromCenter(n, rate_func=rate_functions.ease_out_back) for n in self.node_layer],
                            lag_ratio=lag)]

    def grow_edge(self, u, v):
        """Animations that grow one hidden edge (and its underlay)."""
        e = self.edges[(u, v)]
        under = self.under_layer[list(self.edges).index((u, v))]
        unconceal(e)
        unconceal(under)
        return [GrowArrow(e), Create(under)]

    def show_weight(self, u, v):
        """Make a hidden weight label visible (no animation); returns it."""
        return unconceal(self.weights[(u, v)])

    # ------------------------------------------------------------------ states
    def light(self, u, v, color=AMBER, width=6):
        """Edge stays lit: colour, width and a glow behind it. Undo with unlight()."""
        e = self.edges[(u, v)]
        anims = [e.animate.set_color(ink(color)).set_stroke(width=width)]
        if (u, v) in self.glows:
            self.glow_layer.remove(self.glows[(u, v)])
        gl = glow(self.shaft(u, v), color, width=width)
        self.glows[(u, v)] = gl
        self.glow_layer.add(gl)
        anims.append(FadeIn(gl))
        return anims

    def unlight(self, u, v):
        e = self.edges[(u, v)]
        anims = [e.animate.set_color(self.edge_color).set_stroke(width=4)]
        gl = self.glows.pop((u, v), None)
        if gl is not None:
            anims.append(FadeOut(gl))
            self.glow_layer.remove(gl)
        return anims

    def _edge_to(self, e, color=None, width=None, opacity=None):
        """Transform an arrow's shaft stroke and tip fill together (set_opacity would fill a curved shaft)."""
        return Transform(e, self._style_edge(e.copy(), color, width, opacity))

    @staticmethod
    def _style_edge(t, color=None, width=None, opacity=None):
        """Restyle an arrow in place (shaft stroke and tip together) and return it."""
        if color is not None:
            t.set_stroke(color)
            t.tip.set_fill(color).set_stroke(color)
        if width is not None:
            t.set_stroke(width=width)
            t.tip.set_stroke(width=width)
        if opacity is not None:
            t.set_stroke(opacity=opacity)
            t.tip.set_fill(opacity=opacity).set_stroke(opacity=opacity)
        return t

    def dim(self, keep=(), opacity=0.25):
        """Fade every edge except `keep` (list of (u, v)) to make a route stand out."""
        return [self._edge_to(e, opacity=opacity) for k, e in self.edges.items() if k not in keep]

    def undim(self):
        return [self._edge_to(e, opacity=1) for e in self.edges.values()]

    def reset(self):
        """Every edge and ring back to rest. Do not play these in the same play() as g.animate (a pose):
        use settle() for 'rest and move' in one go."""
        anims = [self._edge_to(e, self.edge_color, 4, 1) for e in self.edges.values()]
        anims += [self.nodes[u].ring.animate.set_stroke(INK, width=3.5) for u in self.nodes]
        return anims + self._drop_glows()

    def settle(self, center=None, scale=None, **kw):
        """Rest every edge, ring and glow AND move/scale the graph, as one animation list to play.
        Why: a group's .animate (pose) snapshots every member at its current state and puts them back at the
        end, so reset()/light()/mark() played in the same play() as g.animate... are silently undone (a test
        film's edges stayed lit through back_home). Here every change goes onto one target instead.
        `scale` is absolute (relative to the built size), like pose(). Weights hidden by pose(weights=False)
        come back (rest means fully shown), and the labels keep their legible size."""
        anims = self._drop_glows()            # out of the group first, so the target has none
        self.generate_target()
        t = self.target
        for e in t.edges.values():
            self._style_edge(e, self.edge_color, 4, 1)
        for n in t.nodes.values():
            n.ring.set_stroke(INK, width=3.5)
        if scale is not None:
            t.scale(scale / self.scale_factor())
        if center is not None:
            t.move_to([*center, 0])
        self.fit_labels(t)
        self._weights_to(t, True)
        return [MoveToTarget(self, **kw), *anims]

    def _drop_glows(self):
        anims = []
        # take a part out of its group BEFORE fading it: FadeOut restores the mobject afterwards, so a faded part
        # still inside the group would come back the next time the group is drawn
        for k in list(self.glows):
            gl = self.glows.pop(k)
            self.glow_layer.remove(gl)
            anims.append(FadeOut(gl))
        for k in list(self.node_glows):
            h = self.node_glows.pop(k)
            self.glow_layer.remove(h)
            anims.append(FadeOut(h))
        return anims

    def fire(self, u, v, color=AMBER, width=12, time_width=0.7):
        """A pulse that runs along the edge (the edge 'fires' / relaxes). Play it."""
        s = self.shaft(u, v).set_stroke(ink(color), width=width)
        s.set_z_index(Z["edge"] + 1)
        return ShowPassingFlash(s, time_width=time_width)

    def mark(self, u, color=CYAN, tag=None, side=DOWN, glow_on=True):
        """Ring colour + glow on a node, optionally a small caps tag (START, END, a cost)."""
        node = self.nodes[u]
        anims = [node.ring.animate.set_stroke(ink(color), width=5), ripple(node.disc, color)]
        if glow_on:
            if u in self.node_glows:
                self.glow_layer.remove(self.node_glows[u])
            h = halo(self.c(u), node.disc.width / 2, color, opacity=0.2)
            self.node_glows[u] = h
            self.glow_layer.add(h)
            anims.append(FadeIn(h))
        if tag:
            t = T(tag, SIZE["small"], color, "BOLD").next_to(node, side, buff=0.14)
            t.set_z_index(Z["edge_label"])
            node.tag = t
            anims.append(FadeIn(t, shift=-side * 0.1))
        return anims

    def unmark(self, u):
        node = self.nodes[u]
        anims = [node.ring.animate.set_stroke(INK, width=3.5)]
        h = self.node_glows.pop(u, None)
        if h is not None:
            anims.append(FadeOut(h))
            self.glow_layer.remove(h)
        return anims

    def badge(self, u, text, color=AMBER, side=UP, size=SIZE["small"]):
        """A value label next to a node (a running cost, a dist value). Returns the mobject (add/FadeIn it)."""
        txt = Mono(str(text), size, color, weight="BOLD")
        pill = RoundedRectangle(corner_radius=0.1, width=txt.width + 0.26, height=txt.height + 0.18,
                                stroke_color=ink(color), stroke_width=1.5, fill_color=BG_DEEP, fill_opacity=0.9)
        g = VGroup(pill, txt.move_to(pill)).next_to(self.nodes[u].disc, side, buff=0.12)
        g.set_z_index(Z["token"] - 1)
        return g


# ---------------------------------------------------------------------- the travelling token
def plane_shape(color=INK, scale=1.0):
    P = lambda pts: Polygon(*[np.array([x, y, 0.0]) for x, y in pts])  # noqa: E731
    body = P([(0.40, 0), (0.31, 0.065), (-0.27, 0.065), (-0.38, 0.028), (-0.38, -0.028), (-0.27, -0.065),
              (0.31, -0.065)])
    wing = P([(0.10, 0.05), (-0.11, 0.38), (-0.20, 0.38), (-0.07, 0.05)])
    tail = P([(-0.21, 0.05), (-0.31, 0.2), (-0.37, 0.2), (-0.33, 0.05)])
    g = VGroup(wing, wing.copy().flip(RIGHT, about_point=np.zeros(3)), tail,
               tail.copy().flip(RIGHT, about_point=np.zeros(3)), body)
    g.set_fill(color, 1).set_stroke(EDGE_UNDER, 1.5).scale(scale)
    return g


class Token(VGroup):
    """The mascot that travels routes: a small plane with a warm halo. token.heading is its angle (radians)."""

    def __init__(self, color=INK, glow_color=AMBER, scale=1.0):
        super().__init__()
        self.plane = plane_shape(color, scale)
        self.halo = halo(np.zeros(3), 0.32 * scale, glow_color, layers=4, opacity=0.22)
        self.add(self.halo, self.plane)
        self.heading = 0.0
        self.set_z_index(Z["token"])
        self.halo.set_z_index(Z["token"] - 1)

    def face(self, angle):
        self.rotate(angle - self.heading, about_point=self.get_center())
        self.heading = angle
        return self


def fly(scene, graph, token, route, until=None, run_time=None, color=AMBER, keep_lit=True, trail=True,
        on_edge=None, rate=rate_functions.ease_in_out_sine):
    """Fly `token` along `route` (node ids), drawing a glowing trail on each edge it takes.

    Timing: give `until` (film time the token lands on the last node) or `run_time` (seconds in total).
    on_edge(i, u, v) may return extra animations to play during leg i (a running total ticking, a badge).
    Leaves the edges lit when keep_lit (record them in graph.glows so graph.reset() clears them)."""
    legs = list(zip(route, route[1:]))
    if until is not None:
        total = max(0.3 * len(legs), scene.left(until))
    else:
        total = run_time or 1.0 * len(legs)
    per = total / max(1, len(legs))
    if token not in scene.mobjects:
        token.move_to(graph.c(route[0]))
        token.face(angle_of_vector(graph.c(route[1]) - graph.c(route[0])))
        scene.play(FadeIn(token, scale=0.5), run_time=min(0.25, per / 3))
        per = max(0.2, (total - min(0.25, per / 3)) / max(1, len(legs)))
    tp = None
    if trail:
        tp = TracedPath(token.get_center, stroke_color=ink(color), stroke_width=5, dissipating_time=0.45)
        tp.set_z_index(Z["token"] - 2)
        scene.add(tp)
    for i, (u, v) in enumerate(legs):
        path = graph.shaft(u, v)
        a, b = graph.c(u), graph.c(v)
        start_heading = token.heading
        h1 = angle_of_vector(path.point_from_proportion(0.02) - path.point_from_proportion(0.0))
        dh = (h1 - start_heading + PI) % TAU - PI

        def move(m, alpha, a=a, b=b, path=path, sh=start_heading, dh=dh):
            # centre-to-centre along the edge's own curve, turning to face the way during the first 25%
            if alpha < 1e-4:
                p = a
            elif alpha > 1 - 1e-4:
                p = b
            else:
                q = path.point_from_proportion(alpha)
                w = min(1.0, alpha / 0.12)
                w2 = min(1.0, (1 - alpha) / 0.12)
                p = q * min(w, w2) + (a if alpha < 0.5 else b) * (1 - min(w, w2))
            k = min(1.0, alpha / 0.25)
            heading = sh + dh * rate_functions.smooth(k)
            if alpha > 0.25:
                t2 = path.point_from_proportion(min(0.999, alpha + 0.01)) - path.point_from_proportion(max(0.0, alpha - 0.01))
                if np.linalg.norm(t2) > 1e-6:
                    heading = angle_of_vector(t2)
            m.rotate(heading - m.heading, about_point=m.get_center())
            m.heading = heading
            m.move_to(p)

        lit = path.copy().set_stroke(ink(color), width=6)
        gl = glow(path, color, width=6)
        lit.set_z_index(Z["edge"] + 1)
        anims = [UpdateFromAlphaFunc(token, move, rate_func=rate),
                 Create(lit, rate_func=rate), Create(gl, lag_ratio=0, rate_func=rate),
                 graph.edges[(u, v)].animate(rate_func=rate).set_color(ink(color))]
        if on_edge:
            anims += list(on_edge(i, u, v) or [])
        scene.play(*anims, run_time=per)
        scene.remove(lit)
        if keep_lit:
            e = graph.edges[(u, v)]
            e.set_stroke(width=6)
            old = graph.glows.pop((u, v), None)
            if old is not None:
                graph.glow_layer.remove(old)
            scene.remove(gl)
            graph.glows[(u, v)] = gl
            graph.glow_layer.add(gl)
        else:
            scene.remove(gl)
    if tp is not None:
        scene.remove(tp)
    return token


def reject(graph, u, v=None, label=None, color=CORAL):
    """An illegal move (a route with too many stops, an edge that breaks a rule): the edge fires coral, a crossed
    disc pops on it (or on node u when v is None) and the edge or node wiggles.
    Returns (anims, marks): play the anims, later FadeOut(marks) when the point is made.

        anims, marks = reject(g, 2, 3, "3 flights > k + 1")
        self.play(*anims, run_time=0.6)
        ...
        self.play(FadeOut(marks), *g.reset(), run_time=0.4)
    """
    r = 0.17 * max(0.75, min(1.0, graph.scale_factor()))
    # on the edge, but where the crossed disc covers no weight pill or node (at the midpoint it hid the weight)
    p = graph.free_point(u, v, 3.5 * r, 3.5 * r) if v is not None else graph.c(u)
    target = graph.edges[(u, v)] if v is not None else graph.nodes[u]
    cross = VGroup(Line(p + np.array([-r, -r, 0]), p + np.array([r, r, 0])),
                   Line(p + np.array([-r, r, 0]), p + np.array([r, -r, 0]))).set_stroke(ink(color), width=8)
    disc = Circle(radius=r * 1.75, stroke_color=ink(color), stroke_width=4, fill_color=BG_DEEP, fill_opacity=0.94)
    disc.move_to(p)
    marks = VGroup(disc, cross)
    anims = [FadeIn(disc, scale=1.8, rate_func=rate_functions.ease_out_back), Create(cross, lag_ratio=0.5),
             Wiggle(target, scale_value=1.05, rotation_angle=0.03 * TAU)]
    if v is not None:
        anims.append(graph.fire(u, v, color))
    if label:
        t = T(label, SIZE["small"], color, "BOLD").next_to(disc, UP, buff=0.12)
        marks.add(t)
        anims.append(FadeIn(t, shift=UP * 0.1))
    marks.set_z_index(Z["token"] + 1)
    return anims, marks
