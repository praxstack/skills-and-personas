"""Values gate: every displayed value equals both its captured fact and its independent expect.

Artifacts mark values with data-fact="<fact id>" (SVG, HTML) or carry them in cue payloads
(IVE metadata track). The gate reads the artifact bytes, never projector internals.
"""
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from .. import errors, expect, text


def check_expectations(lesson):
    """AC-2.7: capture vs independent expect, for every fact. Raises ExpectationMismatch."""
    bad = []
    platform = lesson.data.get("platform", {})
    for f in lesson.data["facts"]:
        want = expect.evaluate(f["expect"], platform)
        if f.get("value") != want:
            bad.append({"fact": f["id"], "captured": f.get("value"), "expected": want})
    if bad:
        raise errors.ExpectationMismatch(f"{len(bad)} fact(s) differ from their independent expectation",
                                         mismatches=bad)
    return {"facts": len(lesson.data["facts"]), "mismatches": 0}


def _compare(fid, shown, lesson, where, bad):
    facts = lesson.by_id("facts")
    if fid not in facts:
        bad.append({"where": where, "fact": fid, "shown": shown, "problem": "unknown fact id"})
        return
    f = facts[fid]
    captured = text.display(f)
    expected = expect.evaluate(f["expect"], lesson.data.get("platform", {})).rstrip("\n")
    if shown != captured or shown != expected:
        bad.append({"where": where, "fact": fid, "shown": shown, "captured": captured, "expected": expected})


def _alt_output(root, lesson, where, bad):
    """The alt text's "Output of <program>: <values>." sentence, value by value (review P2-4)."""
    fig = lesson.data.get("figure")
    desc = next((el for el in root.iter() if el.tag.split("}")[-1] == "desc"), None)
    if not fig or desc is None:
        return 0
    tpl = re.escape(text.ui("alt_output", program="\0", lines="\1"))
    pat = tpl.replace(re.escape("\0"), "(?P<program>.+?)").replace(re.escape("\1"), "(?P<lines>.+)")
    found = [m for m in (re.fullmatch(pat, s) for s in text.sentences(desc.text or "")) if m]
    fids = lesson.state(fig["states"][-1])["state"]["output"]
    if len(found) != 1:
        bad.append({"where": f"{where}:<desc>", "problem": f"{len(found)} alt output sentence(s), expected 1"})
        return 0
    m = found[0]
    if m["program"] != lesson.program(fig["program"])["path"]:
        bad.append({"where": f"{where}:<desc>", "problem": "wrong program", "shown": m["program"]})
    shown = m["lines"].split(", ")
    if len(shown) != len(fids):
        bad.append({"where": f"{where}:<desc>", "problem": "wrong number of values", "shown": m["lines"],
                    "facts": fids})
        return len(fids)
    for fid, val in zip(fids, shown):
        _compare(fid, val, lesson, f"{where}:<desc>", bad)
    return len(fids)


def check_svg(path, lesson):
    root = ET.parse(path).getroot()
    bad, n = [], 0
    for el in root.iter():
        fid = el.get("data-fact")
        if fid is not None:
            n += 1
            _compare(fid, "".join(el.itertext()), lesson, path.name, bad)
    n += _alt_output(root, lesson, path.name, bad)
    return n, bad


class _FactParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.found = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.stack.append([tag, a.get("data-fact"), ""])

    def handle_endtag(self, tag):
        while self.stack:
            t, fid, txt = self.stack.pop()
            if fid is not None:
                self.found.append((fid, txt))
            if self.stack:
                self.stack[-1][2] += txt
            if t == tag:
                break

    def handle_data(self, data):
        if self.stack:
            self.stack[-1][2] += data


def check_html(path, lesson):
    p = _FactParser()
    p.feed(path.read_text())
    bad = []
    for fid, shown in p.found:
        _compare(fid, shown.strip(), lesson, path.name, bad)
    return len(p.found), bad


def check_cue_payloads(vtt_path, lesson):
    """IVE metadata cues: {"state": {"output": [{"fact": id, "text": shown}, ...]}}."""
    bad, n = [], 0
    for block in re.split(r"\n\n+", vtt_path.read_text()):
        lines = block.strip().split("\n")
        if len(lines) < 2 or "-->" not in "".join(lines[:2]):
            continue
        body = "\n".join(lines[[i for i, ln in enumerate(lines) if "-->" in ln][0] + 1:])
        payload = json.loads(body)
        for item in payload.get("state", {}).get("output", []):
            n += 1
            _compare(item["fact"], item["text"], lesson, f"{vtt_path.name}:{payload.get('cue')}", bad)
    return n, bad


def gate(lesson, medium, checks):
    """checks: list of (kind, path). Returns a gate dict."""
    total, bad = 0, []
    for kind, path in checks:
        fn = {"svg": check_svg, "html": check_html, "vtt": check_cue_payloads}[kind]
        n, b = fn(path, lesson)
        total += n
        bad += b
    status = "passed" if total and not bad else "failed"
    reason = "" if total else "no data-fact values found in the artifacts"
    return {"id": f"values.{medium}", "medium": medium, "status": status,
            "measured": {"values_checked": total, "mismatches": bad, "files": [str(p.name) for _, p in checks]},
            "reason": reason}
