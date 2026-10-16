"""FilmScene: the base class every segment of the film derives from.

One FilmScene subclass renders one segment of the film (usually one chapter). It knows its slice of the voice
timing, so it can wait for narration lines instead of guessing seconds, and it always lasts exactly its share of
TIMING.total (render_manim.py renders the segments in parallel and concatenates them frame-exactly).

    class Problem(FilmScene):
        chapters = [1]                       # or span = ("p1", "p7") to split a long chapter into two segments

        def film(self):                      # not construct(): FilmScene.construct runs film() then pads to the end
            self.chapter_card()
            self.beat("p1")                  # waits until the voice starts line p1; the caption appears by itself
            self.play(...)
            self.play_until(L["p2"].voiceEnd, token_flight...)   # lands when the sentence ends

What you get for free: the painted backdrop and world grid, captions for every line in the segment (bottom band,
pinned to the screen, synced by construction), the chapter tag, camera helpers with a gentle drift during holds,
and an overrun report when a scene's animations run past the line they belong to.
"""
import hashlib
import inspect
import os
import sys

import numpy as np
from manim import (DOWN, LEFT, ORIGIN, RIGHT, UP, MovingCameraScene, RoundedRectangle, VGroup, config,
                   rate_functions)

from . import timing as TM
from .backdrop import backdrop_png, dot_grid
from .style import (BG_DEEP, DRIFT, FH, FW, INK, CAPTION_BAND, SIZE, THEMED, Z, fs, key_light, px, SANS)
from .text import balanced_two

STOP_AT = os.environ.get("FILM_STOP_AT")      # render_manim.py --stills: stop at this film time and save the frame


class _Stop(Exception):
    pass


def _park(g):
    """Empty a group's points (kept aside) so the camera skips it; _unpark puts them back."""
    for m in g.get_family():
        if len(m.points):
            m._saved_points = m.points
            m.points = np.zeros((0, 3))
    g._parked = True


def _unpark(g):
    for m in g.get_family():
        sp = getattr(m, "_saved_points", None)
        if sp is not None:
            m.points = sp
            m._saved_points = None
    g._parked = False


class FilmScene(MovingCameraScene):
    chapters = None        # list of chapter numbers this segment covers, e.g. [1]
    span = None            # or (first_line_id, last_line_id)
    drift = DRIFT          # camera breath during holds; 0 turns it off for this scene
    grid = True            # world-space dot grid (moves with the camera)

    # ------------------------------------------------------------------ setup
    @classmethod
    def segment(cls):
        """(t0, t1, first_line_id, last_line_id) of this scene's slice of the film."""
        if cls.span:
            a, b = cls.span
            t0, t1 = TM.bounds(a, b)
            return t0, t1, a, b
        if cls.chapters is None:
            raise ValueError(f"{cls.__name__}: set chapters = [n] or span = (first_id, last_id)")
        (t0, t1), a, b = TM.chapter_bounds(cls.chapters)
        return t0, t1, a, b

    def setup(self):
        super().setup()
        self.t0, self.t1, self.first_id, self.last_id = self.segment()
        self.fps = config.frame_rate
        ids = [ln.id for ln in TM.LINES]
        self.lines = TM.LINES[ids.index(self.first_id): ids.index(self.last_id) + 1]
        self.home_width = FW
        self.overruns = []
        self.stop_at = float(STOP_AT) if STOP_AT else None
        first = self.lines[0]
        starts_chapter = ids.index(first.id) == 0 or TM.LINES[ids.index(first.id) - 1].chapter != first.chapter
        self.prev_backdrop = None
        if THEMED:
            # a theme lights each chapter with its own key light (theme `lights`). The previous chapter's backdrop
            # stays on as an image until the chapter card's shade covers the stage, so the cut shows no jump.
            self.camera.background_image = backdrop_png(warm=key_light(first.chapter))
            if starts_chapter and ids.index(first.id) > 0:
                prev = key_light(TM.LINES[ids.index(first.id) - 1].chapter)
                if prev != key_light(first.chapter):
                    from manim import ImageMobject
                    self.prev_backdrop = ImageMobject(backdrop_png(warm=prev)).set_height(FH).move_to(ORIGIN)
                    self.prev_backdrop.set_z_index(Z["grid"] - 1)
                    self.add(self.prev_backdrop)
        else:
            self.camera.background_image = backdrop_png()
        self.camera.init_background()
        if self.grid:
            self.world_grid = dot_grid()
            self.add(self.world_grid)
        self._build_captions()
        self.tag = None
        show = first.chapter - 1 if starts_chapter else first.chapter
        if show >= 1:
            from .cards import chapter_tag
            self.tag = self.hud(chapter_tag(show))
            self.add(self.tag)

    def construct(self):
        try:
            self.film()
            self.finish()
        except _Stop:
            pass

    def film(self):
        raise NotImplementedError("write the segment in film(self)")

    def play(self, *args, **kw):
        """Scene.play, plus the stills mode: when FILM_STOP_AT falls inside this play, the play is cut there
        (each animation's rate curve is remapped so it ends in its exact state at that moment) and the scene stops."""
        if self.stop_at is None:
            return super().play(*args, **kw)
        from manim.animation.animation import prepare_animation
        anims = [prepare_animation(a) for a in args]
        for a in anims:
            for k, v in kw.items():
                setattr(a, k, v)
        dur = max([a.get_run_time() for a in anims] + [0.0])
        if self.now() + dur < self.stop_at - 0.5 / self.fps:
            return super().play(*anims)
        tau = max(1.0 / self.fps, self.stop_at - self.now())
        for a in anims:
            ta = a.get_run_time()
            frac = 1.0 if ta <= 0 else min(1.0, tau / ta)
            a.rate_func = (lambda f, k: (lambda x: f(x * k)))(a.rate_func, frac)
            a.run_time = tau
            # no clean-up after a cut play: it would remove a half-faded FadeOut and swap a half-done
            # ReplacementTransform for its finished target, so the still would not show what the video shows
            a.clean_up_from_scene = lambda scene: None
        super().play(*anims)
        raise _Stop()

    # ------------------------------------------------------------------ the clock
    def now(self):
        """Current film time in seconds (the segment starts at self.t0)."""
        return self.t0 + self.renderer.time

    def frames_done(self):
        return int(round(self.renderer.time * self.fps))

    def frame_of(self, t):
        """Frame index of film time t inside this segment. Counted the way the render script cuts segments
        (round(t*fps) - round(t0*fps)), so a segment always has exactly its share of frames."""
        return int(round(t * self.fps)) - int(round(self.t0 * self.fps))

    def left(self, t):
        """Seconds from now until film time t (negative when t has passed)."""
        return t - self.now()

    def fit(self, t, run_time):
        """A run time that fits before t: min(run_time, time left), at least one frame."""
        return max(1.0 / self.fps, min(run_time, self.left(t)))

    def _check_stop(self, t):
        if self.stop_at is not None and t >= self.stop_at - 1e-6:
            self._wait_frames(self.frame_of(self.stop_at) - self.frames_done(), drift=0)
            raise _Stop()

    def until(self, t, drift=None, note=""):
        """Hold (camera breathing gently) until film time t. Frame-accurate: it measures what has been rendered,
        so small rounding in earlier play() calls never accumulates."""
        self._check_stop(t)
        target = self.frame_of(t)
        n = target - self.frames_done()
        if n < -1:
            msg = f"FILM-OVERRUN {type(self).__name__}: {(-n) / self.fps:.2f} s late for t={t:.2f} {note}".strip()
            self.overruns.append(msg)
            print(msg, file=sys.stderr, flush=True)
        self._wait_frames(n, drift)

    def _wait_frames(self, n, drift=None):
        if n <= 0:
            return
        d = self.drift if drift is None else drift
        secs = max(1, n - 0.5) / self.fps          # arange(0, secs, 1/fps) yields exactly n frames
        if d and n / self.fps >= 1.0 and not self.renderer.skip_animations:
            f = self.camera.frame
            k = d * min(1.0, (n / self.fps) / 3.0)
            zoom_in = f.width > self.home_width * (1 - 0.05)
            self.play(f.animate.scale(1 - k if zoom_in else 1 + k), run_time=secs, rate_func=rate_functions.smooth)
        else:
            self.wait(secs)

    def beat(self, line_id, offset=0.0):
        """Wait until the voice starts line `line_id` (+offset). Returns the Line."""
        ln = TM.L[line_id]
        self.until(ln.voiceAt + offset, note=f"(beat {line_id})")
        return ln

    def play_until(self, t, *anims, **kw):
        """Play animations so they end exactly at film time t."""
        n = self.frame_of(t) - self.frames_done()
        if n < 1:
            if n < -1:
                msg = f"FILM-OVERRUN {type(self).__name__}: play_until({t:.2f}) started {-n / self.fps:.2f} s late"
                self.overruns.append(msg)
                print(msg, file=sys.stderr, flush=True)
            n = 1
        self.play(*anims, run_time=max(1, n - 0.5) / self.fps, **kw)     # exactly n frames

    def split(self, t, n, least=0.3):
        """Run time for each of n back-to-back plays that should all be done by film time t, counted in whole
        frames (n plays of left/n seconds each round up to a frame apiece and land late, worst in a 15 fps draft)."""
        k = int(max(0.0, self.left(t)) * self.fps / max(1, n))
        return max(least, (max(1, k) - 0.5) / self.fps)

    def play_at(self, t, *anims, run_time=0.6, **kw):
        """Wait until t, then play (run_time is motion length, the placement in time comes from t)."""
        self.until(t)
        self.play(*anims, run_time=run_time, **kw)

    def finish(self):
        """Hold the last frame until the segment's end time (called for you after film())."""
        self.until(self.t1, drift=0 if self.left(self.t1) < 1.0 else None, note="(segment end)")

    # ------------------------------------------------------------------ camera
    def cam(self, center=ORIGIN, width=None, zoom=None):
        """Animation that moves the camera to an absolute framing. zoom=1.3 means 1.3x closer than home."""
        f = self.camera.frame
        w = width if width is not None else self.home_width / (zoom or 1.0)
        return f.animate.set_width(w).move_to(np.array(center, dtype=float))

    def push(self, target, zoom=1.35, offset=(0, 0)):
        """Push in on a mobject or point."""
        c = target.get_center() if hasattr(target, "get_center") else np.array(target, dtype=float)
        return self.cam(c + np.array([offset[0], offset[1], 0]), zoom=zoom)

    def home(self):
        """Camera back to the full frame."""
        return self.cam(ORIGIN, width=self.home_width)

    # ------------------------------------------------------------------ HUD (screen-space layer)
    def hud(self, mob):
        """Pin mob to the screen at its current place, so camera moves do not affect it.
        Animate HUD mobjects while the camera is still (an animation suspends the pin while it runs)."""
        f = self.camera.frame
        s = f.width / FW
        mob._hud = {"pos": (mob.get_center() - f.get_center()) / s, "s": s}

        def upd(m):
            fr = self.camera.frame
            sc = fr.width / FW
            h = m._hud
            if abs(sc - h["s"]) > 1e-9:
                m.scale(sc / h["s"])
                h["s"] = sc
            m.move_to(fr.get_center() + h["pos"] * sc)

        mob.add_updater(upd)
        return mob

    def unpin(self, mob):
        mob.clear_updaters()
        return mob

    # ------------------------------------------------------------------ captions
    def _build_captions(self):
        """One caption per line in the segment, shown from its voice start to its end, cross-faded."""
        caps = []
        self._cap_from = {}            # line id -> earliest film time its caption may start (hold_caption)
        y = -FH / 2 + CAPTION_BAND / 2 + px(4)
        for ln in self.lines:
            parts = balanced_two(ln.cap, 78)
            from .text import Rich
            txt = VGroup(*[Rich(p, SIZE["caption"], INK, weight="MEDIUM") for p in parts])
            txt.arrange(DOWN, buff=px(10))
            maxw = FW - 2 * px(120)
            if txt.width > maxw:
                txt.scale_to_fit_width(maxw)
            pill = RoundedRectangle(corner_radius=0.16, width=txt.width + px(56), height=txt.height + px(30),
                                    stroke_width=0, fill_color=BG_DEEP, fill_opacity=0.74)
            g = VGroup(pill, txt).move_to([0, y, 0])
            g.z_index = Z["caption"]
            for m in g.get_family():
                m.z_index = Z["caption"]
            caps.append((ln, g, pill, txt))
        self._caps = caps
        last = self.lines[-1]
        track = VGroup(*[g for _, g, _, _ in caps])
        for _, g, _, _ in caps:
            g._s, g._alpha = 1.0, None
            _park(g)

        def upd(m, dt):
            # dt makes this a time-based updater, so plain waits are not frozen frames and captions keep fading.
            # Manim renders the family list captured when play() starts, so the captions stay in the track for
            # good; an invisible caption is "parked" (its points emptied) and the camera skips it for free.
            t = self.now()
            fr = self.camera.frame
            sc = fr.width / FW
            for ln, g, pill, txt in caps:
                a0, a1 = max(ln.voiceAt - 0.12, self._cap_from.get(ln.id, -1.0)), ln.end - 0.06
                if ln is last:
                    a1 = min(a1, self.t1 - 0.2)    # fully faded before the cut (it used to vanish at 80% in one frame)
                a = 0.0
                if a0 <= t <= a1 + 0.16:
                    a = min(1.0, (t - a0) / 0.18) if t < a0 + 0.18 else 1.0
                    if t > a1:
                        a = max(0.0, 1 - (t - a1) / 0.16)
                if a <= 0.0:
                    if not g._parked:
                        _park(g)
                    continue
                if g._parked:
                    _unpark(g)
                if g._alpha != a:
                    pill.set_fill(opacity=0.74 * a)
                    txt.set_fill(opacity=a)
                    g._alpha = a
                if abs(g._s - sc) > 1e-9:
                    g.scale(sc / g._s)
                    g._s = sc
                g.move_to(fr.get_center() + np.array([0, y, 0]) * sc)

        track.add_updater(upd)
        self.captions = track
        self.add(track)
        upd(track, 0)

    def hold_caption(self, line_id, t):
        """Keep line_id's caption back until film time t (the chapter card does this for the chapter's first
        line, so its caption appears as the card leaves, never underneath it)."""
        self._cap_from[line_id] = t

    # ------------------------------------------------------------------ cards (see cards.py for the builders)
    def chapter_card(self, n=None, title=None, also=()):
        """Big chapter card over the chapter gap: the stage goes out (opaque shade), the card enters, collapses
        into the corner tag just before the voice begins, and the stage fades back in as it leaves (the card never
        sits over content; the subject is on screen when the voice starts). `also`: a function returning animations to play under the shade during the collapse, e.g.
        also=lambda: [*g.appear_nodes(), pose(g, ...)] (a function, so they are built when the card collapses).
        It returns 0.15 s before the chapter's first word: the next beat can start the first line's motion."""
        from .cards import play_chapter_card
        play_chapter_card(self, n if n is not None else self.lines[0].chapter, title, also)

    def question(self, line_id, number, text=None):
        """Question card for a line with a think pause: card + countdown ring for `think` seconds."""
        from .cards import play_question
        return play_question(self, line_id, number, text)


# ---------------------------------------------------------------------- segment listing for render_manim.py
def _sha(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode() if isinstance(p, str) else p)
    return h.hexdigest()[:16]


def list_segments(module, fps=None):
    """Every FilmScene subclass in `module` with its time span and a content key, sorted by start time.

    Checks that the segments tile [0, TOTAL] exactly. The key changes when the timing, the kit, the module's
    shared code or the scene's own class body changes, so render_manim.py re-renders only what changed."""
    import ast

    fps = fps or TM.FPS
    src_path = inspect.getsourcefile(module)
    src = open(src_path, encoding="utf-8").read()
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    classes = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes[node.name] = "".join(lines[node.lineno - 1: node.end_lineno])
    common = src
    for body in classes.values():
        common = common.replace(body, "")
    kit_dir = os.path.dirname(os.path.abspath(__file__))
    kit_src = "".join(open(os.path.join(kit_dir, f), encoding="utf-8").read()
                      for f in sorted(os.listdir(kit_dir)) if f.endswith(".py"))
    timing_src = open(TM.TIMING_PATH, encoding="utf-8").read()
    segs = []
    for name, obj in vars(module).items():
        if inspect.isclass(obj) and issubclass(obj, FilmScene) and obj is not FilmScene \
                and obj.__module__ == module.__name__ and (obj.chapters is not None or obj.span):
            t0, t1, a, b = obj.segment()
            f0, f1 = int(round(t0 * fps)), int(round(t1 * fps))
            segs.append({"id": name, "scene": name, "from": round(t0, 3), "to": round(t1, 3), "lines": [a, b],
                         "frames": f1 - f0,
                         "key": _sha(kit_src, timing_src, common, classes.get(name, name))})
    segs.sort(key=lambda s: s["from"])
    problems = []
    if not segs:
        problems.append("no FilmScene subclasses with chapters/span found")
    else:
        if abs(segs[0]["from"]) > 1e-6:
            problems.append(f"first segment starts at {segs[0]['from']} (must start at 0)")
        if abs(segs[-1]["to"] - TM.TOTAL) > 1e-6:
            problems.append(f"last segment ends at {segs[-1]['to']} (must end at TOTAL {TM.TOTAL})")
        for a, b in zip(segs, segs[1:]):
            if abs(a["to"] - b["from"]) > 1e-6:
                problems.append(f"{a['id']} ends at {a['to']} but {b['id']} starts at {b['from']} (gap or overlap)")
    return {"segments": segs, "total": TM.TOTAL, "fps": fps, "hash": TM.TIMING.get("hash"), "problems": problems}
