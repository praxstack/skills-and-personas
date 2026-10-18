"""The only value formatter and the only HTML/SVG escaper (E6), plus chrome.json lookup.

Projectors format every fact through display() and escape every model string through esc(),
so one fact can never render two ways in two artifacts.
"""
import html
import json
import re
from functools import lru_cache

from . import host

CHROME = host.PKG / "ptk" / "templates" / "chrome.json"


def esc(s):
    return html.escape(str(s), quote=True)


def display(fact):
    """Display text of a captured fact (no trailing newline, tabs as spaces)."""
    return fact["value"].rstrip("\n").replace("\t", "    ")


def vtt_time(t):
    t = max(0.0, float(t))
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


@lru_cache(maxsize=1)
def chrome():
    return json.loads(CHROME.read_text())


def ui(key, **kw):
    """A fixed UI string from templates/chrome.json (exempt from the claims gate, E4)."""
    s = chrome()["strings"][key]
    return s.format(**kw) if kw else s


SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def sentences(text):
    return [s.strip() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def norm_words(text):
    """Lowercase words for WER / leak comparison; digits 0-20 spelled out."""
    nums = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
            "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
    out = []
    for w in re.findall(r"[a-z0-9']+", text.lower().replace("-", " ")):
        out.append(nums[int(w)] if w.isdigit() and int(w) <= 20 else w)
    return out
