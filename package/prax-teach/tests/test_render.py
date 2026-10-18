"""AC-8.3: the ported renderer passes its tests on Node 22 and on Node 24.

Runs tests/test_render.mjs (v2's 16 renderer tests, ported, plus test_svg_math_video and the v2.1 fixes)
with `node --test` under each major version, through ptk/node.py so the env contract and
PTK_NODE_PREFIX apply. A missing Node major or missing node tools is not-run, never a pass.
"""
import json
import re

from ptk import host, node
from selftest_support import NotRun

MJS = host.PKG / "tests" / "test_render.mjs"
EXPECTED_TESTS = 20  # 16 ported from v2 + 4 new; pinned here, not read from the file


def _run(major):
    found = node.node_for_major(major)
    if not found:
        raise NotRun(f"no Node {major} (set PTK_NODE{major} or `mise install node@{major}`)")
    for mod in ("marked", "sanitize-html", "entities", "mathjax-full", "playwright"):
        if not (node.tools_dir() / "node_modules" / mod / "package.json").is_file():
            raise NotRun(f"{mod} missing under $PTK_STATE/tools/node: run `ptk host setup --yes`")
    tmp = host.make_tmp("render-")
    extra = {"PTK_TEST_TMP": str(tmp), "TMPDIR": str(tmp) + "/"}
    mp4 = sorted(host.PKG.parent.parent.glob("lessons/*/build/video/*.mp4"))
    if mp4:
        extra["PTK_TEST_MP4"] = str(mp4[0])
    res = host.run([found["path"], "--test", "--test-reporter=tap", str(MJS)], cwd=host.PKG,
                   env=node.env(extra=extra), timeout=900)
    out = res.stdout
    counts = {k: int(v) for k, v in re.findall(r"^# (tests|pass|fail|cancelled|skipped|todo) (\d+)$", out, re.M)}
    failed = re.findall(r"^not ok \d+ - (.+)$", out, re.M)
    assert res.code == 0 and counts.get("fail") == 0, f"Node {found['version']}: failed {failed}\n{out[-3000:]}"
    assert counts.get("tests") == EXPECTED_TESTS and counts.get("pass") == EXPECTED_TESTS, (found["version"], counts)
    assert counts.get("skipped", 0) == 0 and counts.get("todo", 0) == 0
    assert re.search(r"^ok \d+ - test_svg_math_video$", out, re.M), "test_svg_math_video did not run"
    return {"node": found["version"], **counts}


def test_svg_math_video():
    results = [_run(22), _run(24)]
    return {"runs": results}


def test_render_through_ptk():
    """ptk's own entry point (node.render_markdown) sets SOURCE_DATE_EPOCH from the source hash."""
    tmp = host.make_tmp("render-ptk-")
    md = tmp / "note.md"
    md.write_text("# Note\n\nOne $x$.\n")
    res = node.render_markdown(md)
    if res.code != 0 and "not installed under $PTK_NODE_PREFIX" in res.stderr:
        raise NotRun(res.stderr.strip())
    assert res.code == 0, res.stderr
    html = (tmp / "note.html").read_text()
    stamp = re.search(r'name="generated-at" content="([^"]+)"', html).group(1)
    epoch = int(host.source_date_epoch(host.sha256_file(md)))
    import datetime
    assert stamp == datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    assert node.render_markdown(md, check=True).code == 0
    return {"generated_at": stamp}
