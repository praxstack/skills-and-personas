"""AC-7.3 (lint half): no literal teaching sentence in a template or a projector.

Spec name tests/test_lint.py::test_no_literal_sentences_in_templates; WP2 owns tests/test_lint.py, so the
claims lint lives here. Fixed UI strings come only from ptk/templates/chrome.json (E4). Every other sentence
comes from the lesson model, so the claims gate can map it.

Scanned:
- ptk/templates/** (html, svg, js, mjs, txt, md), except chrome.json, tokens.json and vendor/;
- ptk/project/*.py: string constants holding markup text (`>A sentence.<`), `.text = "..."` on SVG
  elements, and textContent / innerText / aria-label literals in embedded scripts.
"""
import ast
import re
from html.parser import HTMLParser

from ptk import host, text

TEMPLATES = host.PKG / "ptk" / "templates"
PROJECT = host.PKG / "ptk" / "project"
SKIP_FILES = {"chrome.json", "tokens.json"}
TEMPLATE_EXT = {".html", ".svg", ".js", ".mjs", ".txt", ".md"}
JS_TEXT = re.compile(r"""(?:textContent|innerText|innerHTML|ariaLabel|\.title|placeholder)\s*=\s*(["'`])((?:(?!\1)[^\n;{}]){3,}?)\1"""
                     r"""|setAttribute\(\s*["'](?:aria-label|title|alt)["']\s*,\s*(["'`])((?:(?!\3)[^\n;{}]){3,}?)\3""")
CODE_MARKS = re.compile(r"[;{}\n]|=>|&&|\|\||\bfunction\b|\bvar\b|\breturn\b")


def _squash(s):
    return re.sub(r"\s+", "", s).casefold()


def _chrome_forms():
    """Each chrome string as a regex over squashed text: placeholders match anything short."""
    out = []
    for s in text.chrome()["strings"].values():
        parts = re.split(r"\{[a-z_0-9]+\}", s)
        out.append(re.compile(".{0,80}?".join(re.escape(_squash(p)) for p in parts)))
    return out


def is_sentence(s):
    """Words a learner would read as a statement: three or more words, or two ending in . ! ?"""
    s = re.sub(r"\$\{[^}]*\}|\{\{[^}]*\}\}|\{[a-z_0-9]+\}", " ", s).strip()
    words = re.findall(r"[A-Za-z][A-Za-z'’-]+", s)
    return len(words) >= 3 or (len(words) >= 2 and s.rstrip().endswith((".", "!", "?")))


def _allowed(s, forms):
    q = _squash(s)
    return any(f.fullmatch(q) for f in forms)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.found = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        for k, v in attrs:
            if k in ("alt", "aria-label", "title", "placeholder") and v:
                self.found.append(v)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.found.append(data.strip())


def markup_sentences(src):
    p = _Text()
    p.feed(src)
    return [s for s in p.found if is_sentence(s)]


def js_sentences(src):
    return [m.group(2) or m.group(4) for m in JS_TEXT.finditer(src) if is_sentence(m.group(2) or m.group(4))]


def _consts(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node, node.value


def python_sentences(src):
    """Literal sentences a projector would put in front of the learner."""
    tree = ast.parse(src)
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
                  and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    out = []
    for node, s in _consts(tree):
        if id(node) in docstrings:
            continue
        for seg in re.findall(r">([^<>]+)<", s):
            if is_sentence(seg) and not CODE_MARKS.search(seg):
                out.append((node.lineno, seg.strip()))
        out += [(node.lineno, x) for x in js_sentences(s)]
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            if any(isinstance(t, ast.Attribute) and t.attr in ("text", "tail") for t in node.targets) \
                    and is_sentence(node.value.value):
                out.append((node.lineno, node.value.value))
    return out


def scan():
    forms = _chrome_forms()
    bad = []
    for p in sorted(TEMPLATES.rglob("*")):
        if not p.is_file() or p.name in SKIP_FILES or "vendor" in p.parts or p.suffix not in TEMPLATE_EXT:
            continue
        src = p.read_text(errors="replace")
        found = js_sentences(src) if p.suffix in (".js", ".mjs") else markup_sentences(src) + js_sentences(src)
        bad += [f"{p.relative_to(host.PKG)}: {s!r}" for s in found if not _allowed(s, forms)]
    for p in sorted(PROJECT.glob("*.py")):
        for line, s in python_sentences(p.read_text()):
            if not _allowed(s, forms):
                bad.append(f"{p.relative_to(host.PKG)}:{line}: {s!r}")
    return bad


def test_no_literal_sentences_in_templates():
    # the lint catches each way a sentence can be hard-coded
    planted = {
        "markup": markup_sentences('<p class="x">A case label stops the switch.</p>'),
        "attr": markup_sentences('<img alt="The program prints two then three">'),
        "js": js_sentences('el.textContent = "The switch ends here.";'),
        "py-markup": python_sentences('h = f\'<p class="n">Execution falls through here.</p>\''),
        "py-svg": python_sentences('el.text = "This line prints done."'),
    }
    missed = [k for k, v in planted.items() if not v]
    assert not missed, f"the lint missed planted sentences: {missed}"
    # chrome strings and placeholders are allowed
    forms = _chrome_forms()
    assert _allowed(text.ui("explore_hint"), forms) and _allowed("Captions on", forms)
    assert not is_sentence("{title}") and not is_sentence("n") and not is_sentence("00:12")
    bad = scan()
    assert not bad, f"literal sentences outside chrome.json: {bad[:20]}"
    return {"scanned_templates": sum(1 for p in TEMPLATES.rglob("*") if p.is_file()),
            "scanned_projectors": len(list(PROJECT.glob("*.py")))}
