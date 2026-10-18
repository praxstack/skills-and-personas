"""WP4 explorer: AC-4.1, AC-4.2, AC-4.6, AC-4.7, AC-4.8 (spec names test_explorer.mjs::*; the ptk
test harness is Python-driven, so the browser part runs in ptk/templates/html/drive.mjs and the
judging happens here, in Python, against expect.py and expect_switch.py).

Each test also drives a tampered copy of the page and requires the same check to fail, so a
check that cannot see the defect it names does not pass.
"""
import re
from functools import lru_cache

from _util import SLICE
from ptk import host, model
from ptk.project import explorer


@lru_cache(maxsize=1)
def _built():
    lesson = model.load(SLICE)
    out = host.make_tmp("t-explorer-") / "explorer"
    r = explorer.project(lesson, out)
    return lesson, r["model"], out / "index.html"


@lru_cache(maxsize=1)
def _clean():
    _lesson, m, page = _built()
    return explorer.drive_explorer(m, page)


def _tampered(old, new, where="script", rehash=True):
    """Copy the built page with one edit inside its <script> or <style>, keeping the CSP hash valid
    (unless rehash=False), and drive the copy."""
    _lesson, m, page = _built()
    src = page.read_text()
    tag = "<script>" if where == "script" else "<style>"
    end = "</script>" if where == "script" else "</style>"
    i = src.rindex(tag) + len(tag)
    j = src.index(end, i)
    body = src[i:j]
    assert old in body, f"tamper fixture out of date: {old!r} not in the page {where}"
    new_body = body.replace(old, new, 1)
    out = src[:i] + new_body + src[j:]
    if rehash:
        out = out.replace(explorer.csp_hash(body), explorer.csp_hash(new_body))
    dst = host.make_tmp("t-explorer-bad-") / "index.html"
    dst.write_text(out)
    return explorer.drive_explorer(m, dst)


def test_a11y_csp_noscript():
    """AC-4.1: hash CSP enforced, keyboard operable, visible focus, reduced motion, full noscript."""
    _lesson, m, _page = _built()
    rec = _clean()
    probs = explorer.check_a11y(m, rec)
    assert not probs, probs
    csp = rec["a11y"]["csp"]
    assert re.search(r"script-src 'sha256-[A-Za-z0-9+/=]+';", csp) and "unsafe" not in csp, csp
    # negative: a script edited after the build no longer matches its hash, so the CSP blocks it
    bad = explorer.check_a11y(m, _tampered("st.brk = !st.brk", "st.brk = st.brk", rehash=False))
    assert any("did not run" in p for p in bad), f"a script blocked by the CSP passed: {bad[:3]}"
    return {"tab_order": [t["id"] or t["name"] for t in rec["tabOrder"][:2]], "csp": csp[:80]}


def test_full_domain():
    """AC-4.2: every (n, break) state reached through the controls, each step's display equal to
    expect.switch_output / expect_switch.switch_trace for the state that step should produce."""
    _lesson, m, _page = _built()
    rec = _clean()
    probs, steps = explorer.check_domain(m, rec, prose=False)
    assert not probs, probs[:10]
    assert len(explorer.states(m)) == 2 * len(m["domain"]) and m["domain"] == [0, 1, 2, 3, 4, 5], m["domain"]
    assert steps >= 4 * len(m["domain"]), steps
    # negative: the page ignores the break when n is 3 (only that state is wrong)
    bad, _ = explorer.check_domain(m, _tampered("if (cs[i].brk) {", "if (cs[i].brk && n !== 3) {"), prose=False)
    assert bad and all("n=3" in p or "toggle" in p or "load" in p for p in bad), f"a wrong n=3 path passed: {bad[:3]}"
    assert any("output" in p for p in bad), bad[:5]
    return {"control_steps": steps, "states": len(explorer.states(m))}


def test_prose_follows_state():
    """AC-4.6: every bound sentence and the provenance line recomputed from the live state."""
    _lesson, m, _page = _built()
    probs, steps = explorer.check_domain(m, _clean(), prose=True)
    assert not probs, probs[:10]
    # negative: prose rendered once and never again keeps describing the captured default
    bad, _ = explorer.check_domain(m, _tampered("live.textContent = '';\n    V.prose.forEach",
                                                 "if (!live.childNodes.length) V.prose.forEach"), prose=True)
    assert any("default-state sentences still shown" in p for p in bad), f"stale prose passed: {bad[:3]}"
    return {"control_steps": steps}


def test_key_nodes_visible_390():
    """AC-4.7: code, output and the live note fully on screen at 390 px with no inner scroll, in every
    state and both themes (1440 px is checked by the build gate explorer.layout)."""
    rec = _clean()
    probs, n = explorer.check_layout(rec, width=390)
    assert not probs, probs[:10]
    assert n == 2 * 2 * len(_built()[1]["domain"]), n
    all_probs, _ = explorer.check_layout(rec)
    assert not all_probs, all_probs[:5]
    # negative: a code line too wide for a phone
    bad, _ = explorer.check_layout(_tampered(".ln .src{white-space:pre;font-family:inherit}",
                                             ".ln .src{white-space:pre;font-family:inherit;min-width:30rem}",
                                             where="style"), width=390)
    assert any("key-node" in p or "overflow" in p for p in bad), f"an overflowing code panel passed: {bad[:3]}"
    return {"layouts_390": n}


def test_file_protocol():
    """AC-4.8: opened straight from disk (file://) in Chromium, no server, nothing fetched."""
    rec = _clean()
    probs = explorer.check_file(rec)
    assert not probs, probs
    assert rec["url"].startswith("file:///") and len(rec["contexts"]) >= 8, rec["url"]
    return {"contexts": len(rec["contexts"]), "url": rec["url"][:60]}
