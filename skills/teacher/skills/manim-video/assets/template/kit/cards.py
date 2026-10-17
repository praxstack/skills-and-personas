"""Cards: title card, chapter card + corner tag, question card with countdown ring, lower third.

    chapter_tag(n)                         the "01 · THE PROBLEM" pill pinned top-left (FilmScene adds it)
    self.chapter_card()                    stage out, big card over the chapter gap, collapse into the tag, stage back in
    self.question("q1", 1)                 question card + countdown ring for the line's `think` seconds
    title_block("Cheapest Flights", "Within K Stops", "LEETCODE 787")    the intro hero
    lower_third("EXAMPLE 1", "k = 1")      a small label box above the caption band (like a time stamp)
"""
import numpy as np
from manim import (BOLD, DOWN, LEFT, ORIGIN, RIGHT, UP, Arc, Circle, Create, FadeIn, FadeOut, Line,
                   Rectangle, ReplacementTransform, RoundedRectangle, UpdateFromAlphaFunc, ValueTracker, VGroup,
                   always_redraw, rate_functions, linear)

from . import timing as TM
from .fx import glow, soft_shadow
from .style import (ACCENT, AMBER, BG, BG_DEEP, DIM, FH, FW, INK, MUTED, PANEL, PANEL_HI, SAFE_TOP, SAFE_X, SIZE, Z,
                    ink, on_fill, px)
from .text import H, T, Mono, wrap_lines


def _z(mob, z):
    for m in mob.get_family():
        m.z_index = z
    return mob


def chapter_count():
    return max([c["n"] for c in TM.CHAPTERS] + [1])


def chapter_tag(n, name=None):
    """Top-left pill: accent number (AMBER in the original palette), chapter name in caps, progress pips."""
    name = (name or TM.CHAPTER_NAMES.get(n, f"Chapter {n}")).upper()
    num = H(f"{n:02d}", 36, ACCENT, BOLD)
    lab = T(name, SIZE["small"], INK, BOLD)
    total = chapter_count()
    pips = VGroup(*[RoundedRectangle(corner_radius=0.02, width=0.32, height=0.07, stroke_width=0,
                                     fill_color=ACCENT if i == n else (MUTED if i < n else DIM), fill_opacity=1)
                    for i in range(1, total + 1)]).arrange(RIGHT, buff=0.07)
    row = VGroup(num, lab, pips).arrange(RIGHT, buff=0.24)
    lab.align_to(num, DOWN).shift(UP * 0.01)
    pips.match_y(lab)
    pill = RoundedRectangle(corner_radius=0.14, width=row.width + 0.5, height=row.height + 0.3,
                            stroke_color=DIM, stroke_width=1.2, fill_color=BG_DEEP, fill_opacity=0.78)
    pill.move_to(row)
    g = VGroup(pill, num, lab, pips)
    g.move_to([-SAFE_X + g.width / 2, SAFE_TOP - g.height / 2 + px(20), 0])
    g.num, g.lab, g.pips, g.pill = num, lab, pips, pill
    _z(g, Z["hud"])
    _z(pill, Z["hud"] - 1)             # the pill always under its text, also when the parts are animated one by one
    return g


COLLAPSE_LEAD = 0.6   # the card starts to collapse this long before the chapter's first word


def play_chapter_card(scene, n, title=None, also=()):
    """Card in, hold, collapse into the corner tag. Keyed to the first line of the chapter.
    `also`: animations to play during the collapse (move the subject into this chapter's layout under the card),
    or better a function returning them (lambda: [...]) so they are built at that moment, not before the card.

    Timing (chapter gap 0.8 s + chapter_lead 1.0 s = about 1.8 s before the voice), in steps that never put the
    card over content (the starter's 02-05 cards faded in while the graph was still at 70%, so its edges and node 3
    crossed the title, and the graph stayed a 15% ghost behind the card text):
      1. the stage goes out: an opaque shade (BG_DEEP, under the card layer) covers everything below the card
         layer over 0.28 s, starting at the segment start (0.35 s after the last word of the previous chapter);
      2. the card enters (0.42 s) and holds on the empty stage;
      3. COLLAPSE_LEAD (0.6 s) before the voice it collapses into the corner tag (0.45 s); `also` moves the subject
         into this chapter's layout under the shade;
      4. the shade lifts in the second half of the collapse, once the title has gone (the subject comes in as the
         card leaves), and is gone 0.15 s before the first word: the subject is on screen when the voice starts
         (qa.py "chapter-entry"; it used to lift after the collapse, about 0.6 s into the first line).
    That line's caption waits for the collapse (FilmScene.hold_caption), so no caption ever shows under a card.
    Anything at z >= Z["card"] - 1 (callouts, HUD, captions) is drawn over the shade: keep it off stage then.

    Each part moves as one piece (fixes seen in the LC 70 test film and the starter, at every chapter change):
      * the number's glow slides in WITH the number (it was built at the end position while the number slid
        from the left: a "0404" double image on entry),
      * the glow follows the number into the tag and is gone in the first quarter of the collapse (it used to
        fade in place: a ghost "04" left behind),
      * the title flies to the tag and is gone by mid-way, then the caps label fades in there (a
        ReplacementTransform from "Every approach" to "EVERY APPROACH" morphed glyph into different glyph:
        scrambled text),
      * the new tag's pill sits under the flying parts (at the HUD layer it covered them: a dim tag), and the
        old tag is gone in the first half (no two tags at once)."""
    first = scene.lines[0]
    name = title or TM.CHAPTER_NAMES.get(n, f"Chapter {n}")
    fps = scene.fps
    collapse_at = first.voiceAt - COLLAPSE_LEAD
    if scene.left(collapse_at) < 0.75:
        print(f"note: chapter card for {n} has little room before {first.id}", flush=True)
    shade = Rectangle(width=FW * 3, height=FH * 3, stroke_width=0, fill_color=BG_DEEP, fill_opacity=0)
    kicker = T("CHAPTER", SIZE["small"], MUTED, BOLD)
    big = H(f"{n:02d}", SIZE["hero"] * 1.6, ACCENT, BOLD)
    ttl = H(name, SIZE["headline"] * 1.15, INK, BOLD)
    row = VGroup(big, ttl).arrange(RIGHT, buff=0.55).move_to(UP * 0.15)
    if row.width > FW - 2 * px(140):
        row.scale_to_fit_width(FW - 2 * px(140))
    kicker.next_to(ttl, UP, buff=0.18).align_to(ttl, LEFT)
    rule = Line(ttl.get_corner(DOWN + LEFT) + DOWN * 0.22, ttl.get_corner(DOWN + RIGHT) + DOWN * 0.22,
                stroke_color=ACCENT, stroke_width=6)
    total = chapter_count()
    pips = VGroup(*[RoundedRectangle(corner_radius=0.03, width=0.62, height=0.1, stroke_width=0,
                                     fill_color=ACCENT if i == n else (MUTED if i < n else DIM), fill_opacity=1)
                    for i in range(1, total + 1)]).arrange(RIGHT, buff=0.12)
    pips.next_to(rule, DOWN, buff=0.35).align_to(ttl, LEFT)
    halo_big = glow(big, ACCENT, width=1, layers=(6, 14, 26), opacities=(0.28, 0.12, 0.05), text=True)
    _z(shade, Z["card"] - 1)
    for m in (kicker, big, ttl, rule, pips, halo_big):
        _z(m, Z["card"])
    big_t, ttl_t = big.copy(), ttl.copy()
    scene.add(shade)
    slide = 2.5
    big.shift(LEFT * slide).set_opacity(0)
    ttl.shift(RIGHT * slide).set_opacity(0)
    scene.until(scene.now() + 1.0 / fps)
    # 1. the outgoing stage goes fully out before any card text shows (an opaque shade, measured: nothing of the
    #    subject is left behind the card; at 0.84 the graph stayed a ghost behind the title)
    room = scene.left(collapse_at)
    scene.play(shade.animate.set_fill(opacity=1.0), run_time=scene.fit(collapse_at, min(0.28, 0.33 * room)),
               rate_func=rate_functions.ease_in_out_sine)
    if getattr(scene, "prev_backdrop", None) is not None:      # a theme: the new chapter's key light, under the shade
        scene.remove(scene.prev_backdrop)
        scene.prev_backdrop = None
    # 2. the card enters on the empty stage; the rule and pips draw in the second half of the same move
    out = rate_functions.ease_out_cubic
    later = lambda t: out(min(1.0, max(0.0, (t - 0.4) / 0.6)))  # noqa: E731
    scene.play(big.animate(rate_func=out).move_to(big_t).set_opacity(1),
               ttl.animate(rate_func=out).move_to(ttl_t).set_opacity(1),
               FadeIn(kicker, shift=DOWN * 0.15, rate_func=out), FadeIn(halo_big, shift=RIGHT * slide, rate_func=out),
               Create(rule, rate_func=later), FadeIn(pips, lag_ratio=0.2, rate_func=later),
               run_time=scene.fit(collapse_at - 0.1, 0.42))
    scene.until(collapse_at)
    new_tag = chapter_tag(n, name if title else None)
    # the card's parts (z card) fly into the tag: its pill must sit under them, not at the HUD layer over them
    # (it dimmed the arriving number, label and pips to about 20% for the whole collapse)
    _z(new_tag.pill, Z["card"] - 0.5)
    # the title flies to the tag label's place, shrinking, and is gone by mid-way; the caps label fades in
    # there only after that (no two labels on top of each other)
    smooth = lambda x: x * x * (3 - 2 * x)  # noqa: E731
    ttl_src = ttl.copy()
    ttl_dst = ttl.copy().scale(new_tag.lab.height / ttl.height).move_to(new_tag.lab, aligned_edge=LEFT)

    def fly(m, a):
        e = rate_functions.ease_in_out_cubic(a)
        for part, p0, p1 in zip(m.get_family(), ttl_src.get_family(), ttl_dst.get_family()):
            part.interpolate(p0, p1, e)
        m.set_opacity(1.0 - smooth(min(1.0, a / 0.5)))

    late = lambda t: smooth(max(0.0, (t - 0.6) / 0.4))  # noqa: E731   (the number has nearly landed by then)
    # the glow tracks the number (centre and size) and is gone in the first quarter of the collapse
    h0, ops = big.height, [(m, m.get_stroke_opacity()) for m in halo_big]
    halo_big.save_state()

    def follow(m, a):
        m.restore()
        m.scale(max(1e-3, big.height / h0)).move_to(big.get_center())
        k = max(0.0, 1.0 - a / 0.25)
        for part, o in ops:
            part.set_stroke(opacity=o * k)

    ease = rate_functions.ease_in_out_cubic
    early = lambda t: min(1.0, t / 0.45)  # noqa: E731
    # rate functions are set per animation (play(rate_func=...) would override them all)
    anims = [ReplacementTransform(big, new_tag.num, rate_func=ease),
             UpdateFromAlphaFunc(halo_big, follow, rate_func=linear),
             UpdateFromAlphaFunc(ttl, fly, rate_func=linear), FadeIn(new_tag.lab, rate_func=late),
             FadeIn(new_tag.pill, rate_func=ease), ReplacementTransform(pips, new_tag.pips, rate_func=ease),
             FadeOut(kicker, rate_func=early), FadeOut(rule, rate_func=early)]
    if scene.tag is not None:
        anims.append(FadeOut(scene.tag, rate_func=early))   # the old tag is gone before the new one shows
    extra = list(also()) if callable(also) else list(also)
    for a in extra:                    # the layout moves under the shade while the card collapses
        a.rate_func = ease
    run = 0.45
    scene.hold_caption(first.id, scene.now() + run - 0.1)
    # 3 + 4. the card collapses into the tag; the shade stays opaque for the first half (the title and the glow
    # are gone by then) and lifts in the second, so the subject fades in, already in its layout, as the card leaves
    lift = lambda t: rate_functions.ease_in_out_sine(max(0.0, (t - 0.5) / 0.5))  # noqa: E731
    scene.play(*anims, *extra, shade.animate(rate_func=lift).set_fill(opacity=0), run_time=run)
    scene.remove(new_tag.num, new_tag.lab, new_tag.pill, new_tag.pips, halo_big, ttl, kicker, rule)
    if scene.tag is not None:
        scene.remove(scene.tag)
    scene.tag = scene.hud(chapter_tag(n, name if title else None))
    scene.add(scene.tag)
    scene.remove(shade)

def think_ring(center, radius=0.42, secs_label="THINK"):
    """A countdown ring: returns (group, tracker). Animate tracker 0 -> 1 with rate_func=linear."""
    tr = ValueTracker(0.0)
    back = Circle(radius=radius, stroke_color=DIM, stroke_width=7).move_to(center)
    arc = always_redraw(lambda: Arc(radius=radius, start_angle=np.pi / 2, angle=-2 * np.pi * max(1e-3, 1 - tr.get_value()),
                                    stroke_color=ink(AMBER), stroke_width=7).move_arc_center_to(center))
    dot = Circle(radius=0.07, stroke_width=0, fill_color=AMBER, fill_opacity=1).move_to(center)
    lab = T(secs_label, SIZE["small"], MUTED, BOLD).next_to(back, DOWN, buff=0.14)
    g = VGroup(back, arc, dot, lab)
    return _z(g, Z["card_text"]), tr


def play_question(scene, line_id, number, text=None):
    """Question card keyed to a line: in as the voice starts, countdown ring during `think`, out at the line's end.
    The shade darkens the backdrop and grid only (it sits under the subject's layers), so the subject the viewer
    reasons on stays at full contrast; a 50% dim over the stage made its labels unreadable (2.9:1)."""
    ln = TM.L[line_id]
    q = text or ln.cap
    scene.until(max(scene.now(), ln.voiceAt - 0.25))
    if scene.camera.frame.width < scene.home_width - 1e-3 or np.linalg.norm(scene.camera.frame.get_center()) > 1e-3:
        scene.play(scene.home(), run_time=0.25)
    shade = _z(Rectangle(width=FW * 3, height=FH * 3, stroke_width=0, fill_color=BG_DEEP, fill_opacity=0),
               Z["grid"] + 1)
    badge = VGroup(Circle(radius=0.44, stroke_width=0, fill_color=AMBER, fill_opacity=1),
                   H(f"Q{number}", 40, on_fill(AMBER), BOLD))
    words = wrap_lines(q, 40)
    body = VGroup(*[H(w, SIZE["question"], INK, BOLD) for w in words]).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
    if body.width > 8.6:
        body.scale_to_fit_width(8.6)
    content = VGroup(badge, body).arrange(RIGHT, buff=0.45)
    card = RoundedRectangle(corner_radius=0.24, width=content.width + 2.3, height=max(1.5, content.height + 0.6),
                            stroke_color=ink(AMBER), stroke_width=2, stroke_opacity=0.55, fill_color=PANEL_HI,
                            fill_opacity=0.97)
    card.move_to([0, 2.05, 0])
    content.move_to(card).align_to(card, LEFT).shift(RIGHT * 0.4)
    ring, tr = think_ring(card.get_right() + LEFT * 0.85 + UP * 0.12, radius=0.36)
    shadow = soft_shadow(card)
    grp = VGroup(shadow, card, content)
    _z(grp, Z["card"])
    _z(content, Z["card_text"])
    scene.add(shade)
    scene.play(shade.animate.set_fill(opacity=0.6), FadeIn(grp, shift=DOWN * 0.5),
               run_time=0.5, rate_func=rate_functions.ease_out_cubic)
    scene.until(ln.thinkAt)
    if ln.think > 0.5:
        scene.play(FadeIn(ring[0]), FadeIn(ring[2]), FadeIn(ring[3]), run_time=0.2)
        scene.add(ring[1])
        scene.play_until(ln.end - 0.4, tr.animate.set_value(1.0), rate_func=linear)
        scene.remove(ring[1])
        scene.play(FadeOut(VGroup(ring[0], ring[2], ring[3])), FadeOut(grp, shift=UP * 0.4),
                   shade.animate.set_fill(opacity=0), run_time=scene.fit(ln.end, 0.35))
    else:
        scene.until(ln.end - 0.35)
        scene.play(FadeOut(grp, shift=UP * 0.4), shade.animate.set_fill(opacity=0), run_time=scene.fit(ln.end, 0.35))
    scene.remove(shade)


def title_block(line1, line2, kicker=None, accent=ACCENT):
    """The intro hero: two-line display title (second line in the accent, with a glow) and a kicker."""
    a = H(line1, SIZE["title"] * 1.15, INK, BOLD)
    b = H(line2, SIZE["title"] * 1.15, accent, BOLD)
    g = VGroup(a, b).arrange(DOWN, buff=0.18, aligned_edge=LEFT)
    parts = [g]
    if kicker:
        k = T(kicker, SIZE["small"], MUTED, BOLD)
        bar = Line(ORIGIN, RIGHT * 0.9, stroke_color=accent, stroke_width=6)
        kk = VGroup(bar, k).arrange(RIGHT, buff=0.22)
        kk.next_to(g, UP, buff=0.35).align_to(g, LEFT)
        parts.insert(0, kk)
    out = VGroup(*parts)
    out.glow = glow(b, accent, width=1, layers=(5, 12, 22), opacities=(0.25, 0.1, 0.04), text=True)
    out.line1, out.line2 = a, b
    return out


def lower_third(label, value=None, color=AMBER):
    """A boxed label in the style of the reference film's time stamps: dark box, accent text, caps."""
    a = T(label.upper(), SIZE["small"], color, BOLD)
    parts = [a]
    if value:
        parts.append(Mono(value, SIZE["small"], INK))
    row = VGroup(*parts).arrange(RIGHT, buff=0.3)
    box = RoundedRectangle(corner_radius=0.06, width=row.width + 0.42, height=row.height + 0.26, stroke_color=ink(color),
                           stroke_width=1.5, fill_color=BG_DEEP, fill_opacity=0.9).move_to(row)
    g = VGroup(box, row)
    return _z(g, Z["hud"])
