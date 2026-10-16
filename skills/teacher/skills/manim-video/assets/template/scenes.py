"""The film: one FilmScene per chapter. THIS is the file a new film replaces; kit/ stays.

This demo implements examples/mini/script.json (LeetCode 787 in one minute, 14 lines) end to end, so every kit
piece is shown in use: title card, chapter cards, captions, the flight graph as the persistent subject, the input
decoder, the travelling plane, comic bursts, question cards with countdown rings, DP rows, the complexity ladder,
the code panel with an active line, and camera push-ins.

Rules that keep the film in sync and continuous:
  * Every moment is keyed to a line: self.beat("p3"), self.until(L["p4"].said("seven hundred")),
    self.play_until(L["a1"].voiceEnd, ...). run_time= is only for how long a motion takes, never for when.
  * Each scene starts in the HOME pose (graph centred, nothing lit) and ends there, so the cut between two
    separately rendered segments is invisible under the chapter card. g.pose() moves the graph to a layout and
    keeps its weights and node numbers at least 32 px on screen, however small the graph is posed.
  * Legibility (quality bar, checked by legibility.py on the stills): nothing under 32 px in the kit, small
    labels in capitals, dimmed things still >= 4.5:1, and text lands before the moment a still is taken
    (start a reveal ~0.4 s before the word it belongs to, so it has landed when the word is spoken).
  * Unpack animation lists into self.play(*a, *b); never wrap sub-mobject animations in AnimationGroup.
  * Colours come from kit/style.py only (a theme remaps them). AMBER, CYAN... are fills: T/H/Mono/Rich turn them
    into text inks by themselves; for a thin stroke or a set_color on text write ink(AMBER); for a label on a
    filled shape write on_fill(AMBER).

Render one segment as a draft:  ../.venv/bin/manim render -ql scenes.py Problem
Render the film:                 python3 <skill>/scripts/render_manim.py --project ..
"""
import numpy as np
from manim import *  # noqa: F401,F403

from kit import *  # noqa: F401,F403

# ---------------------------------------------------------------------------- the subject's data (from the brief)
N = 4
FLIGHTS = [[0, 1, 100], [1, 2, 100], [2, 0, 100], [1, 3, 600], [2, 3, 200]]
POS = {0: (-3.5, 0.0), 1: (0.0, 1.9), 2: (0.0, -1.9), 3: (3.5, 0.0)}      # layout from data (scene units)
SIDE = {(2, 3): -1}                                                       # weight label on the other side
HOME = dict(center=(0.0, 0.35), scale=0.92)                               # every scene starts and ends here

# The compiled solution from the brief, re-wrapped to 50 columns with 2-space indents so the panel fits beside the
# graph at 30 px (code is 30-36 px in the quality bar; a wider panel had been scaled down to 28 px). The comments
# moved onto the lines they explain. 0-based lines: 6 the round loop, 7 the copy, 10-11 the relax, 13 the swap.
CPP = """int findCheapestPrice(int n,
    vector<vector<int>>& flights,
    int src, int dst, int k) {
  const int INF = 1e9;
  vector<int> dist(n, INF);
  dist[src] = 0;
  for (int round = 0; round <= k; ++round) {
    vector<int> next = dist;  // read old
    for (auto& f : flights) {
      int u = f[0], v = f[1], w = f[2];
      if (dist[u] != INF && dist[u] + w < next[v])
        next[v] = dist[u] + w;  // write new
    }
    dist = next;
  }
  return dist[dst] == INF ? -1 : dist[dst];
}"""


def flight_map(hidden=False):
    g = WGraph(list(range(N)), [tuple(f) for f in FLIGHTS], pos=POS, label_side=SIDE)
    g.place(HOME["center"], HOME["scale"])            # place/pose/settle keep the labels >= 32 px on screen
    return g.hide() if hidden else g


def pose(g, center, scale, **kw):
    """Animation moving the graph to a layout given as absolute centre and scale (relative to its built size),
    labels kept legible (g.pose). One MoveToTarget: play it alongside other mobjects' animations, never alongside
    the graph's own member animations (light, mark, reset), which it would undo. For rest + move: g.settle()."""
    return g.pose(center, scale, **kw)


def back_home(scene, g, extra=(), by=None, run_time=0.5):
    """Clear marks and lit edges, fade `extra`, and return the graph to HOME so the next segment starts here.
    g.settle() rests and moves in one target: never put g.reset() and g.animate... in one play()."""
    by = by if by is not None else scene.t1
    anims = g.settle(center=HOME["center"], scale=HOME["scale"])
    anims += [FadeOut(m) for m in extra]
    for n in g.nodes.values():
        if hasattr(n, "tag"):
            anims.append(FadeOut(n.tag))
            del n.tag
    anims.append(scene.home())
    scene.until(by - run_time - 0.05)
    scene.play(*anims, run_time=run_time, rate_func=rate_functions.ease_in_out_cubic)


# ============================================================================ 0. intro
class Intro(FilmScene):
    chapters = [0]

    def film(self):
        hero = title_block("Cheapest Flights", "Within K Stops", "LEETCODE 787  ·  GRAPHS")
        hero.move_to(UP * 0.35)
        hero.glow.move_to(hero.line2)
        arc = ArcBetweenPoints([-8.2, -2.75, 0], [8.2, -1.55, 0], angle=-PI / 9)   # passes under the title
        trail = DashedVMobject(arc.copy().set_stroke(ink(AMBER), 3), num_dashes=70)
        plane = Token(scale=1.15)
        plane.move_to(arc.get_start())

        def ride(m, a):
            p = arc.point_from_proportion(min(a, 0.999))
            q = arc.point_from_proportion(min(a + 0.002, 1.0))
            m.move_to(p)
            m.face(angle_of_vector(q - p))

        i1 = L["i1"]
        self.play(FadeIn(hero[0], shift=RIGHT * 0.3), FadeIn(hero.line1, shift=UP * 0.25),
                  FadeIn(hero.line2, shift=UP * 0.25), FadeIn(hero.glow),
                  run_time=0.6, rate_func=rate_functions.ease_out_cubic)
        self.add(plane)
        self.play_until(i1.voiceEnd, UpdateFromAlphaFunc(plane, ride), Create(trail),
                        self.cam(UP * 0.2, zoom=1.06), rate_func=rate_functions.ease_in_out_sine)
        # the title flies past the camera; chapter 1 opens on an empty, lit stage
        self.play_until(self.t1, hero.animate.scale(2.4).set_opacity(0), FadeOut(hero.glow), FadeOut(trail),
                        FadeOut(plane), self.home(), rate_func=rate_functions.ease_in_cubic)


# ============================================================================ 1. the problem
class Problem(FilmScene):
    chapters = [1]

    def film(self):
        g = flight_map(hidden=True)                       # the subject is born here: nodes first, edges from the input
        g.place((-2.75, 0.2), 0.82)
        self.add(g)
        dec = InputDecoder("flights", FLIGHTS, per_row=1, size=32,
                           more=[("src = 0", CYAN), ("dst = 3", AMBER), ("k = 1", CORAL)])
        dec.move_to([3.65, 0.1, 0])
        self.chapter_card(also=lambda: [*g.appear_nodes(), *dec.write()])   # on screen as p1 starts

        per = self.split(L["p2"].voiceAt - 0.1, len(FLIGHTS))   # all five land before p2 speaks
        for i, (u, v, w) in enumerate(FLIGHTS):            # each entry flies into its edge
            dec.send(self, i, g, (u, v), run_time=per)

        p2 = L["p2"]
        self.until(p2.said("start"))
        self.play(*g.mark(0, CYAN, "START"), *dec.show_more(0), run_time=0.45)
        self.until(p2.said("end") - 0.45)                 # text lands as its word is spoken, not after it
        self.play(*g.mark(3, AMBER, "END"), *dec.show_more(1), run_time=0.45)

        p3 = L["p3"]
        ring = DashedVMobject(Circle(radius=0.62, color=ink(CORAL), stroke_width=4), num_dashes=26).move_to(g.c(1))
        stop = T("STOP", SIZE["small"], CORAL, "BOLD").next_to(ring, UP, buff=0.08)
        self.until(p3.voiceAt - 0.45)
        self.play(*dec.show_more(2), Create(ring), FadeIn(stop), run_time=0.5)
        self.until(p3.said("on the way"))
        self.play(ring.animate.move_to(g.c(2)), stop.animate.next_to(g.c(2) + DOWN * 0.62, DOWN, buff=0.08),
                  run_time=0.6, rate_func=rate_functions.ease_in_out_cubic)
        self.play(FadeOut(ring), FadeOut(stop), run_time=0.3)

        p4 = self.beat("p4")
        tok = Token()
        cost = VGroup(T("COST", SIZE["small"], MUTED, "BOLD"), Mono("0", 40, AMBER, weight="BOLD"))
        cost.arrange(RIGHT, buff=0.25).move_to(g.c(0) + DOWN * 1.75 + RIGHT * 0.4)
        self.play(FadeIn(cost, shift=UP * 0.1), dec.animate.shift(RIGHT * 6), run_time=0.4,
                  rate_func=rate_functions.ease_in_cubic)
        sums = {0: 100, 1: 700}

        def tick(i, u, v):                                  # the running total rolls as each leg is flown
            new = Mono(str(sums[i]), 40, AMBER, weight="BOLD")
            out = roll(cost[1], new)
            cost.submobjects[1] = new
            return out

        fly(self, g, tok, [0, 1, 3], until=p4.said("seven hundred", 0.15), on_edge=tick)
        ok = T("1 STOP ✓", SIZE["small"], MINT, "BOLD").next_to(g.nodes[1], UP, buff=0.18)
        self.play(ripple(g.nodes[1].disc, MINT), FadeIn(ok, shift=UP * 0.1), run_time=0.5)
        self.until(p4.said("the answer"))
        b = burst("700!", size=80).move_to(g.c(3) + UP * 1.5 + RIGHT * 0.5)
        self.play(self.push(g, zoom=1.16, offset=(1.0, 0.25)), run_time=0.6)
        pop(self, b)
        back_home(self, g, extra=[b, tok, cost, dec, ok])


# ============================================================================ 2. brute force
class Brute(FilmScene):
    chapters = [2]

    def film(self):
        g = flight_map()
        self.add(g)
        b1 = L["b1"]
        # the recursion tree, grown level by level while the same edges fire on the map
        X, lv = 2.4, [2.3, 1.0, -0.3, -1.6]
        spec = {"r": (0, 0, X, None), "a": (1, 1, X, "r"), "b": (2, 2, X - 1.7, "a"), "c": (3, 2, X + 1.7, "a"),
                "d": (0, 3, X - 2.6, "b"), "e": (3, 3, X - 0.8, "b")}
        nodes, links = {}, {}
        for k, (city, L_, x, par) in spec.items():
            p = np.array([x, lv[L_], 0])
            nodes[k] = VGroup(Circle(radius=0.32, stroke_color=INK, stroke_width=3, fill_color=PANEL_HI,
                                     fill_opacity=1).move_to(p), H(str(city), 34).move_to(p))
            if par:
                pp = np.array([spec[par][2], lv[spec[par][1]], 0])
                links[k] = Line(pp, p, buff=0.34, stroke_color=EDGE, stroke_width=3)
        # a short chapter (3.6 s): the tree's root grows under the card, and the cost lands with the last level,
        # a second before its word, so it is never caught half faded
        self.chapter_card(also=lambda: [pose(g, (-3.9, 0.3), 0.6), GrowFromCenter(nodes["r"])])
        steps = [(["a"], [(0, 1)]), (["b", "c"], [(1, 2), (1, 3)])]
        per = self.split(self.now() + 0.5, len(steps), least=0.22)
        for keys, edges in steps:
            self.play(*[GrowFromCenter(nodes[k]) for k in keys], *[Create(links[k]) for k in keys if k in links],
                      *[g.fire(u, v, AMBER) for u, v in edges], run_time=per)
        o = Rich("O(n^(k+1))", 64, CORAL, "BOLD").move_to([X + 2.3, -1.5, 0])
        lab = T("TIME", SIZE["small"], MUTED, "BOLD").next_to(o, UP, buff=0.14)
        bad, marks = reject(g, 2, 3)                       # 0 -> 1 -> 2 -> 3 has two stops: k = 1 rules it out
        # the rejected leaf gets a small coral cross at its shoulder, so its number stays readable
        cross = VGroup(Line(LEFT, RIGHT), Line(UP, DOWN)).rotate(PI / 4).scale(0.13).set_stroke(ink(CORAL), 6)
        cross.move_to(nodes["e"].get_corner(UR) + RIGHT * 0.06).set_z_index(Z["token"])
        self.play(*[GrowFromCenter(nodes[k]) for k in ("d", "e")], *[Create(links[k]) for k in ("d", "e")],
                  g.fire(2, 0, AMBER), FadeIn(o, scale=1.4, rate_func=rate_functions.ease_out_back), FadeIn(lab),
                  run_time=0.4)
        self.play(*bad, nodes["e"][0].animate.set_stroke(ink(CORAL)), Create(cross), run_time=0.4)
        tree = VGroup(*nodes.values(), *links.values(), o, lab, cross)
        back_home(self, g, extra=[tree, marks], run_time=0.4)


# ============================================================================ 3. intuition
class Intuition(FilmScene):
    chapters = [3]

    def film(self):
        g = flight_map()
        self.add(g)
        self.chapter_card(also=lambda: [pose(g, (0, -0.75), 0.74)])
        self.question("q1", 1)

        # a1: the plane takes off as the card leaves; each leg gets a flight number beside its edge (on the side
        # away from the weight, clear of other labels), and the rule lands with the second leg
        a1 = L["a1"]
        tok = Token(scale=0.85)
        badges = []
        eq = Rich("≤ k stops  ⇔  ≤ k+1 flights", 44, INK, "BOLD").move_to([0, 2.45, 0])
        eq[0:7].set_color(ink(CORAL))

        def badge(i, u, v):
            b = VGroup(Circle(radius=0.29, stroke_color=ink(CYAN), stroke_width=3, fill_color=BG_DEEP, fill_opacity=1),
                       H(str(i + 1), 34, CYAN))
            b.move_to(g.beside(u, v, b))
            badges.append(b)
            return [FadeIn(b, scale=0.5)] + ([FadeIn(eq, shift=UP * 0.15)] if i == 1 else [])

        fly(self, g, tok, [0, 1, 3], until=a1.at(0.45), color=CYAN, on_edge=badge)
        self.play(ripple(g.nodes[1].disc, CORAL), run_time=0.5)
        self.until(a1.end - 0.3)
        self.play(FadeOut(VGroup(eq, tok, *badges)), *g.reset(), run_time=0.3)

        # rows under the next question: the viewer can reason on them during the think pause
        old = ArrayRow([0, INF, INF, INF], label="OLD", header=["0", "1", "2", "3"], cell=0.82, size=32)
        new = ArrayRow([0, INF, INF, INF], label="NEW", cell=0.82, size=32)
        VGroup(old, new).arrange(DOWN, buff=0.75).move_to([2.9, -0.65, 0])
        new.align_to(old, RIGHT)
        arrows = VGroup(*[Arrow(old.cells[i].get_bottom(), new.cells[i].get_top(), buff=0.06, stroke_width=3,
                                color=DIM, tip_length=0.14) for i in range(4)])
        self.play(pose(g, (-3.6, -0.6), 0.6), *old.appear(), *new.appear(), run_time=0.45)
        self.question("q2", 2)

        a2 = self.beat("a2")
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.12), g.fire(0, 1, AMBER),
                  *old.focus(0, CYAN), run_time=0.5)
        self.play(*new.set(1, 100, AMBER), *g.light(0, 1, AMBER), run_time=0.4)
        note = T("one round = one more flight", SIZE["small"], AMBER, "BOLD").next_to(new, DOWN, buff=0.3)
        self.play(FadeIn(note, shift=UP * 0.1), run_time=0.35)
        back_home(self, g, extra=[old, new, arrows, note], run_time=0.4)


# ============================================================================ 4. every approach
class Approaches(FilmScene):
    chapters = [4]

    def film(self):
        g = flight_map()
        self.add(g)
        lad = Ladder([("Brute-force DFS", "O(n^(k+1))", "O(k)", 1.0),
                      ("DFS + memo", "O(k·E)", "O(n·k)", 0.42),
                      ("Bellman-Ford", "O(k·E)", "O(n)", 0.3)]).hide()
        lad.move_to([-0.55, -0.75, 0])
        head = T("CHEAPER AS YOU CLIMB  ↑", SIZE["small"], MUTED, "BOLD")
        head.align_to(lad, LEFT).match_y(lad.heads)          # one header row with TIME and SPACE
        # the map shrinks to a decorative thumbnail: its weights fade out there (unreadable at that size, and
        # nothing in this chapter refers to them); settle() in back_home brings them back
        self.chapter_card(also=lambda: [pose(g, (4.8, 2.3), 0.4, weights=False), FadeIn(head),
                                        *lad.show_heads()])
        self.play(*lad.reveal(0), run_time=0.3)              # the stage is back as x1 starts: land before "memo"
        x1 = L["x1"]
        self.until(x1.said("memo") - 0.55)
        self.play(*lad.reveal(1), run_time=0.5)
        self.play(ripple(g.nodes[2].disc, AMBER), run_time=0.5)
        x2 = L["x2"]
        self.until(x2.voiceAt - 0.45)
        self.play(*lad.reveal(2), run_time=0.5)
        self.until(x2.said("rounds"))
        self.play(*[g.fire(u, v, CYAN, width=8) for u, v, _ in FLIGHTS], run_time=0.6)
        self.play(*[g.fire(u, v, CYAN, width=8) for u, v, _ in FLIGHTS], run_time=0.6)
        self.until(x2.said("order n space"))
        self.play(*lad.pick(2), self.push(lad.rungs[2], zoom=1.12, offset=(0.6, 0)), run_time=0.6)
        back_home(self, g, extra=[lad, head], run_time=0.45)            # also brings the camera home


# ============================================================================ 5. code and dry run
class CodeDryRun(FilmScene):
    chapters = [5]

    def film(self):
        g = flight_map()
        self.add(g)
        code = CodePanel(CPP, size=30)                  # 30 px, never scaled down: the listing is wrapped to fit
        code.shift(RIGHT * (-SAFE_X - code.bg.get_left()[0]) + UP * (STAGE_TOP - code.bg.get_top()[1]))
        code.hide_lines()
        dist = ArrayRow([0, INF, INF, INF], label="dist", header=["0", "1", "2", "3"], cell=0.76, height=0.64,
                        size=30)
        dist.move_to([4.15, -0.75, 0]).align_to([SAFE_X, 0, 0], RIGHT)
        nxt = dist.clone_below("next", buff=0.3)
        # "Dry run." is short: everything that sets the stage happens under the card's collapse
        self.chapter_card(also=lambda: [pose(g, (4.3, 1.6), 0.5), FadeIn(VGroup(code.shadow, code.code.background)),
                                        *code.reveal(0, 16, lag=0.02), *dist.appear()])
        c1 = L["c1"]
        state = [0, INF, INF, INF]
        for rnd, phrase in ((0, "round zero"), (1, "round one")):
            self.until(c1.said(phrase))
            new = list(state)
            enter = [*nxt.appear(), *g.mark(0, CYAN)] if rnd == 0 else [*nxt.calm()]
            self.play(*code.focus(6, 7), *enter, run_time=0.3)
            fired = []
            for u, v, w in FLIGHTS:                         # one round: every flight, reading the old row
                if state[u] < INF and state[u] + w < new[v]:
                    new[v] = state[u] + w
                    fired.append((u, v))
                    self.play(*code.focus(10, 11), g.fire(u, v, AMBER), *dist.focus(u, CYAN), run_time=0.3)
                    self.play(*nxt.set(v, new[v], AMBER), *g.light(u, v, AMBER), run_time=0.3)
                else:                                       # unreachable source: the edge is skipped
                    self.play(*code.focus(10), g.fire(u, v, DIM, width=8), run_time=0.14)
            changed = [i for i in range(4) if new[i] != state[i]]
            self.play(*code.focus(13), *[a for i in changed for a in dist.pull(nxt, i, MINT)],   # dist = next
                      *[a for u, v in fired for a in g.unlight(u, v)], run_time=0.45)
            state = new
        self.play(*code.focus(15), *g.light(0, 1, AMBER), *g.light(1, 3, AMBER), *g.mark(3, AMBER),
                  run_time=0.4)
        o1 = self.beat("o1")
        self.play(FadeOut(VGroup(code, nxt, dist)), pose(g, (0, 0.75), 0.82), run_time=0.6,
                  rate_func=rate_functions.ease_in_out_cubic)
        take1 = Rich("k stops → k+1 rounds", 46, CYAN, "BOLD")
        take2 = Rich("copy before you update", 46, AMBER, "BOLD")
        row = VGroup(take1, T("·", 46, MUTED), take2).arrange(RIGHT, buff=0.4).move_to([0, -1.75, 0])
        cx = Rich("O(k·E) time  ·  O(n) space", 34, MUTED, "BOLD").next_to(row, DOWN, buff=0.3)
        self.until(o1.said("rounds") - 0.45)                # each takeaway lands as its words are spoken
        self.play(FadeIn(take1, shift=UP * 0.15), FadeIn(row[1]), run_time=0.4)
        self.until(o1.said("copy") - 0.45)
        self.play(FadeIn(take2, shift=UP * 0.15), FadeIn(cx), run_time=0.4)
        self.play_until(self.t1, self.push(g, zoom=1.06, offset=(0, -0.7)), rate_func=rate_functions.smooth)
