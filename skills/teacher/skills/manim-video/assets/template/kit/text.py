"""Text helpers. No LaTeX is needed: Text/MarkupText (Pango) render everything, superscripts included.

    T("Cheapest flights", "headline", font=DISPLAY, weight=BOLD)
    Mono("flights = [[0,1,100]]", "code")                 # monospace, ligatures impossible (DejaVu Sans Mono)
    Rich("O(n^(k+1))", "body")                            # ^(...) and ^x become superscripts, _(i) subscripts
    Formula(r"O(n^{k+1})", "O(n^(k+1))", "body")          # MathTex when LaTeX is installed (laptop), else Rich
"""
import re

from manim import BOLD, MEDIUM, NORMAL, MarkupText, Text, VGroup

from .style import DISPLAY, HAS_LATEX, INK, MONO, SANS, SIZE, fs, ink


def size_of(size):
    return fs(SIZE[size]) if isinstance(size, str) else fs(size)


def T(s, size="body", color=INK, weight=NORMAL, font=SANS, **kw):
    """Plain text. `size` is a SIZE key ("body", "caption"...) or CSS px at 1080p. A hue (AMBER, CYAN...) becomes
    its text ink (ink(): the hue itself in the original palette, the solved ink in a theme)."""
    return Text(s, font=font, font_size=size_of(size), color=ink(color), weight=weight, **kw)


def H(s, size="headline", color=INK, weight=BOLD, **kw):
    """Headline in the display face."""
    return T(s, size, color, weight, font=DISPLAY, **kw)


def Mono(s, size="code", color=INK, weight=NORMAL, **kw):
    """Monospace text for code, arrays and numbers. DejaVu Sans Mono has no programming ligatures."""
    return Text(s, font=MONO, font_size=size_of(size), color=ink(color), weight=weight, **kw)


def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_SUP = re.compile(r"\^\(([^()]*)\)|\^([A-Za-z0-9+\-]+)")
_SUB = re.compile(r"_\(([^()]*)\)")          # only x_(i): snake_case names stay intact


def to_markup(s):
    """'O(n^(k+1))' -> 'O(n<sup>k+1</sup>)'. Plain text is escaped first."""
    s = escape(s)
    s = _SUP.sub(lambda m: f"<sup>{m.group(1) or m.group(2)}</sup>", s)
    s = _SUB.sub(lambda m: f"<sub>{m.group(1)}</sub>", s)
    return s


def Rich(s, size="body", color=INK, weight=NORMAL, font=SANS, markup=False, **kw):
    """Text with ^superscripts and _(subscripts): O(n^(k+1)), 10^22, x_(i). Plain characters (<, &) are escaped.
    Pass markup=True to write Pango markup yourself (<b>, <span foreground='...'>, <sup>)."""
    m = s if markup else to_markup(s)
    return MarkupText(m, font=font, font_size=size_of(size), color=ink(color), weight=weight, **kw)


def Formula(tex, fallback, size="body", color=INK, **kw):
    """LaTeX math when LaTeX exists (a laptop with MacTeX/TeX Live), the Rich fallback otherwise.
    The cloud sandbox has no LaTeX, so the fallback is what renders there."""
    if HAS_LATEX:
        from manim import MathTex
        return MathTex(tex, font_size=size_of(size) * 1.25, color=ink(color), **kw)
    return Rich(fallback, size, color, **kw)


def wrap_lines(s, max_chars):
    """Greedy word wrap; returns a list of lines."""
    words, lines, cur = s.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def balanced_two(s, max_chars):
    """Split a caption into at most two balanced lines (at punctuation when it is near the middle)."""
    if len(s) <= max_chars:
        return [s]
    mid, best, bd = len(s) / 2, -1, 1e9
    for m in re.finditer(r"[.:;,?!] | — |: ", s):
        i = m.start() + 1
        if abs(i - mid) < bd:
            bd, best = abs(i - mid), i
    if best < 0 or bd > len(s) * 0.22:
        spaces = [i for i, c in enumerate(s) if c == " "]
        best = min(spaces, key=lambda i: abs(i - mid)) if spaces else len(s)
    return [s[:best].strip(), s[best:].strip()]


def stack(*mobs, buff=0.12, aligned_edge=None):
    from manim import DOWN, LEFT
    g = VGroup(*mobs).arrange(DOWN, buff=buff, aligned_edge=aligned_edge if aligned_edge is not None else LEFT)
    return g


__all__ = ["T", "H", "Mono", "Rich", "Formula", "to_markup", "escape", "wrap_lines", "balanced_two", "stack",
           "BOLD", "MEDIUM", "NORMAL", "DISPLAY", "SANS", "MONO", "size_of"]
