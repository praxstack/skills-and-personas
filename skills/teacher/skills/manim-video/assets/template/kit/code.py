"""CodePanel: Manim's Code (Pygments + Paragraph) in the film's palette, with an active-line highlight and
chunked reveal.

    code = CodePanel(CPP, language="cpp", size=30).move_to(LEFT * 3)
    code.hide_lines()                       # start with every line hidden (reveal in chunks as they are explained)
    self.play(*code.reveal(0, 4))           # lines 0..4 (0-based, inclusive) type in
    self.play(*code.focus(5, 6))            # highlight bar moves to lines 5-6, the rest dims (still >= 4.5:1)
    self.play(*code.unfocus())
    glyphs = code.find(9, "dist[u]")        # the glyphs of a substring on line 9 (pulse them with the subject)

Ligatures: Code/Paragraph render through Text, which cannot switch off OpenType 'calt', so the code font must be
one without programming ligatures. DejaVu Sans Mono (shipped in fonts/) keeps != <= ++ -> as typed. Do not
switch to JetBrains Mono or Fira Code here (Manim raises an error for them, or they turn != into a single glyph).

Legibility (quality bar: code 30-36 px, every text >= 4.5:1): the panel is set at 30 px and never scaled below
it (max_width only shrinks it down to min_size; wrap long lines instead, about 50 columns fit beside a side
panel). Focus is the amber bar and highlight; the other lines dim to DIM_OPACITY, and every token colour below
stays above 4.5:1 on the panel even dimmed (the old 0.38 dim left comments at 1.8:1, practically invisible).
"""
from manim import (DOWN, LEFT, RIGHT, UP, Code, FadeIn, RoundedRectangle, VGroup, rate_functions)
from pygments.style import Style
from pygments.token import (Comment, Keyword, Name, Number, Operator, Punctuation, String, Text, Token)

from .fx import conceal, soft_shadow, unconceal
from .style import (ACCENT, AMBER, CODE_COMMENT, CODE_FUNC, CODE_IDLE, CODE_KEYWORD, CODE_LINENO, CODE_OP,
                    CODE_PUNCT, COMIC, CORAL, CYAN, DIM, INK, MINT, MONO, PANEL, PANEL_HI, THEMED, Z, fs, ink)

DIM_OPACITY = 0.78          # inactive lines in focus(); with the original colours the dimmest token stays >= 5:1
# Syntax colours are inks (style.py: CODE_* and ink()). A theme's inks sit just over 4.6:1, so dimming them by
# opacity would break 4.5:1: in a theme, lines out of focus turn CODE_IDLE (muted) instead, and the active
# line's highlight is PANEL_HI (a surface every ink is solved against) rather than an amber wash.


class FilmCodeStyle(Style):
    """Pygments style in the film palette (keywords violet, types cyan, numbers amber, comments grey-blue)."""
    background_color = PANEL
    line_number_color = CODE_LINENO
    styles = {
        Token: INK, Text: INK,
        Comment: f"italic {CODE_COMMENT}", Comment.Single: f"italic {CODE_COMMENT}",
        Comment.Multiline: f"italic {CODE_COMMENT}",
        Keyword: CODE_KEYWORD, Keyword.Type: ink(CYAN), Keyword.Constant: ink(AMBER),
        Name: INK, Name.Function: CODE_FUNC, Name.Builtin: ink(CYAN), Name.Class: ink(CYAN),
        Number: ink(AMBER), Number.Integer: ink(AMBER), Number.Float: ink(AMBER),
        Operator: CODE_OP, Punctuation: CODE_PUNCT,
        String: ink(MINT),
    }


class CodePanel(VGroup):
    def __init__(self, source, language="cpp", size=30, line_numbers=True, window=True, max_width=None,
                 min_size=30, line_spacing=0.6, buff=0.28):
        super().__init__()
        self.code = Code(code_string=source, language=language, formatter_style=FilmCodeStyle,
                         background="window" if window else "rectangle", add_line_numbers=line_numbers,
                         paragraph_config={"font": MONO, "font_size": fs(size), "line_spacing": line_spacing},
                         background_config={"fill_color": PANEL, "stroke_color": DIM, "stroke_width": 1.5,
                                            "corner_radius": 0.22, "buff": buff, "fill_opacity": 0.96})
        if max_width and self.code.width > max_width:
            k = max(max_width / self.code.width, min(1.0, min_size / size))
            if k < max_width / self.code.width - 1e-6:
                import sys
                print(f"CODE-TOO-WIDE: {self.code.width:.2f} units at {size} px > max_width {max_width}; kept at "
                      f"{min_size} px. Wrap the longest lines.", file=sys.stderr, flush=True)
            self.code.scale(k)
        self.lines = self.code.code_lines
        self.numbers = getattr(self.code, "line_numbers", None)
        self.bg = self.code.background
        if THEMED and window and len(self.bg.submobjects):      # Manim's window buttons, in the theme's hues
            for dot, c in zip(self.bg.submobjects[-1], (CORAL, COMIC, MINT)):
                dot.set_fill(c, opacity=1)
        self.source_lines = source.split("\n")
        self.shown = set(range(len(self.lines)))
        self.shadow = soft_shadow(self.bg)
        self.hl_color, self.hl_opacity = (PANEL_HI, 1.0) if THEMED else (AMBER, 0.13)
        self.hl = RoundedRectangle(corner_radius=0.08, width=self.bg.width - 0.22, height=0.3, stroke_width=0,
                                   fill_color=self.hl_color, fill_opacity=self.hl_opacity)
        self.bar = RoundedRectangle(corner_radius=0.03, width=0.07, height=0.3, stroke_width=0,
                                    fill_color=ACCENT, fill_opacity=1)
        # every glyph's own colour, so a theme's focus() can turn idle lines CODE_IDLE and bring them back
        self.glyph_colors = [[m.get_fill_color() for m in ln] for ln in self.lines]
        self.hl.set_opacity(0)
        self.bar.set_opacity(0)
        self.add(self.shadow, self.code, self.hl, self.bar)
        self.set_z_index(Z["panel"])
        self.hl.set_z_index(Z["panel"] + (0.5 if THEMED else 1))     # a theme's opaque highlight sits under the text
        self.bar.set_z_index(Z["panel"] + 2)
        self.lines.set_z_index(Z["panel_text"])
        if self.numbers is not None:
            self.numbers.set_z_index(Z["panel_text"])

    # ------------------------------------------------------------------ reveal
    def hide_lines(self):
        self.shown = set()
        conceal(self.lines)
        if self.numbers is not None:
            conceal(self.numbers)
        return self

    def reveal(self, i, j=None, lag=0.12):
        """Lines i..j (0-based, inclusive) fade in from the left, staggered."""
        j = i if j is None else j
        anims = []
        for k in range(i, j + 1):
            ln = unconceal(self.lines[k])
            self.shown.add(k)
            anims.append(FadeIn(ln, shift=RIGHT * 0.15, rate_func=rate_functions.ease_out_cubic))
            if self.numbers is not None:
                anims.append(FadeIn(unconceal(self.numbers[k])))
        return anims

    # ------------------------------------------------------------------ focus
    def _span(self, i, j):
        g = VGroup(*[self.lines[k] for k in range(i, j + 1) if len(self.lines[k])])
        if not len(g):
            g = self.lines[i]
        return g

    def focus(self, i, j=None, dim=DIM_OPACITY):
        """Move the highlight to lines i..j and dim the others (to `dim` opacity; keep it >= 0.75 so dimmed code
        stays readable)."""
        j = i if j is None else j
        g = self._span(i, j)
        h = g.height + 0.16
        cy = g.get_center()[1]
        x = self.bg.get_center()[0]
        anims = [self.hl.animate.set_opacity(self.hl_opacity).stretch_to_fit_height(h).move_to([x, cy, 0]),
                 self.bar.animate.set_opacity(1).stretch_to_fit_height(h).move_to([self.bg.get_left()[0] + 0.12, cy, 0])]
        for k, ln in enumerate(self.lines):
            if len(ln) and k in self.shown:
                anims.append(self._line_to(k, i <= k <= j, dim))
        return anims

    def _line_to(self, k, active, dim=DIM_OPACITY):
        ln = self.lines[k]
        if CODE_IDLE is None:                       # original palette: idle lines dim by opacity
            return ln.animate.set_opacity(1 if active else dim)
        ln.generate_target()                        # a theme: idle lines turn CODE_IDLE, active ones get their colours
        for m, c in zip(ln.target, self.glyph_colors[k]):
            m.set_fill(c if active else CODE_IDLE, opacity=1)
        from manim import MoveToTarget
        return MoveToTarget(ln)

    def unfocus(self):
        anims = [self.hl.animate.set_opacity(0), self.bar.animate.set_opacity(0)]
        for k, ln in enumerate(self.lines):
            if len(ln) and k in self.shown:
                anims.append(self._line_to(k, True))
        return anims

    def find(self, line, text):
        """The glyphs of `text` in line `line` (spaces are not glyphs, so the search ignores them)."""
        src = self.source_lines[line].replace(" ", "")
        k = src.find(text.replace(" ", ""))
        if k < 0:
            raise KeyError(f"{text!r} not on line {line}: {self.source_lines[line]!r}")
        return VGroup(*self.lines[line][k:k + len(text.replace(' ', ''))])
