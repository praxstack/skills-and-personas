"""AC-8.5: registry/tools.json ranks report 05's alternatives per artifact type, each with a binary probe
and a fallback order, and `ptk host probe` reports what runs now.

The expected counts and top entries below are copied from report 05
(clean-install-20261018/review-20261018/reports/05-approach-catalog.md, section tables) and from v2's
registry by hand. They are pinned here on purpose: the registry file can't approve itself (D20.12).
"""
import json
import sys

from _util import ptk_cmd
from ptk import host

# report 05: rows per artifact table, and each table's top three (Top 3 sections)
EXPECTED_COUNTS = {"still": 16, "explorer": 15, "qa": 13, "cards": 13, "video": 16, "ive": 15, "tts": 10}
EXPECTED_TOP = {
    "still": ["code-svg", "typst-cetz", "graphviz"],
    "explorer": ["trace-stepper", "compile-server", "marimo-wasm"],
    "qa": ["predict-gated-html", "annotated-code", "obsidian-callouts"],
    "cards": ["genanki-anki", "model-occlusion", "ts-fsrs-cards"],
    "video": ["hyperframes-kokoro", "manim-voiceover", "vhs"],
    "ive": ["state-first-timeline", "mp4-webvtt-cues", "event-replay"],
    "tts": ["kokoro-onnx", "hyperframes-tts", "macos-say"],
}
# v2's visualization-tool-registry.json, all 38 ids (checked 2026-10-18)
V2_IDS = {"svg", "mermaid", "d2", "graphviz", "drawio", "vega-lite", "observable-plot", "echarts", "matplotlib",
          "plotly", "altair", "ggplot2", "excalidraw", "kroki", "plantuml", "structurizr", "penrose", "html", "css",
          "javascript", "canvas-2d", "webgl", "react-flow", "threejs", "d3", "cytoscapejs", "sigmajs", "deckgl", "rive",
          "dotlottie", "manim", "motion-canvas", "remotion", "hyperframes", "openai-image-generation",
          "wikimedia-commons", "unsplash", "ffmpeg"}
PROBE_KINDS = {"binary", "state", "sandbox", "app", "python-module", "node-module", "builtin", "cloud",
               "unsupported-platform"}
DISPOSITIONS = {"route", "alternative", "backend", "format", "handoff-only", "do-not-route",
                "requires-human-authored-asset", "cloud-needs-consent"}


def test_ranked_with_probes():
    reg = host.registry()
    tools, arts = reg["tools"], reg["artifacts"]
    assert {k: len(v) for k, v in arts.items()} == EXPECTED_COUNTS
    for art, alts in arts.items():
        ranks = [a["rank"] for a in alts]
        assert sorted(ranks) == list(range(1, len(alts) + 1)), f"{art}: ranks are not 1..n: {ranks}"
        assert len({a["id"] for a in alts}) == len(alts), f"{art}: duplicate ids"
        by_rank = [a["id"] for a in sorted(alts, key=lambda a: a["rank"])]
        assert reg["fallback_order"][art] == by_rank, f"{art}: fallback_order is not the rank order"
        assert by_rank[:3] == EXPECTED_TOP[art], (art, by_rank[:3])
        for a in alts:
            assert a["needs"], f"{art}/{a['id']}: no probe"
            for n in a["needs"]:
                assert n in tools, f"{art}/{a['id']} needs unknown tool {n}"
                assert tools[n]["probe"] in PROBE_KINDS, (n, tools[n]["probe"])
            cloud = any(tools[n]["probe"] == "cloud" for n in a["needs"])
            assert cloud == (not a["local"]), f"{art}/{a['id']}: local flag disagrees with its probes"
        assert any(a.get("ptk_projector") for a in alts), f"{art}: no alternative ptk can build"
    # the catalog: v2's 38 tools, no more, no less, each corrected entry well-formed
    cat = reg["catalog"]
    assert {c["id"] for c in cat} == V2_IDS and len(cat) == 38
    for c in cat:
        assert c["disposition"] in DISPOSITIONS, c["id"]
        assert c["docs"].startswith("https://"), c["id"]
        assert c.get("probe") is None or c["probe"] in tools, (c["id"], c.get("probe"))
    cat_by = {c["id"]: c for c in cat}
    assert cat_by["manim"]["version"] == "0.22.0"
    assert cat_by["hyperframes"]["version"] == "0.8.169"
    assert {"tts", "transcribe"} <= set(cat_by["hyperframes"]["subcommands"])
    # contradictions v2 had: a ranked alternative may not be do-not-route, a backend is never rank 1
    ranked_ids = {"remotion": "remotion", "motion-canvas": "motion-canvas"}
    for cid in ranked_ids:
        assert cat_by[cid]["disposition"] != "do-not-route", cid
    assert cat_by["ffmpeg"]["disposition"] == "backend"
    for art, alts in arts.items():
        first = min(alts, key=lambda a: a["rank"])
        assert first["needs"] != ["ffmpeg"], f"{art}: a backend ranks first"
    # the node pin agrees with the catalog
    pkg = json.loads((host.PKG / "node" / "package.json").read_text())
    assert pkg["dependencies"]["hyperframes"] == cat_by["hyperframes"]["version"]

    # `ptk host probe` runs, and a missing binary flips the answer (the probe is real, not a constant)
    res = host.run([*ptk_cmd(), "host", "probe"], env=host.child_env(), timeout=300)
    assert res.code == 0, res.stderr[-1500:]
    rep = json.loads(res.stdout)
    assert set(rep["artifacts"]) == set(EXPECTED_COUNTS)
    for art, r in rep["artifacts"].items():
        assert len(r["alternatives"]) == EXPECTED_COUNTS[art]
        assert [a["id"] for a in r["alternatives"]] == reg["fallback_order"][art]
        for a in r["alternatives"]:
            assert a["runnable"] == (not a["missing"])
            if not a["local"]:
                assert not a["runnable"], f"{art}/{a['id']}: a cloud alternative probed runnable"
    assert rep["tools"]["ptk"]["runnable"] is True
    bare = host.run([sys.executable, "-B", "-m", "ptk", "host", "probe", "--artifact", "still"],
                    env=host.child_env({"PATH": "/nonexistent", "PYTHONPATH": str(host.PKG)}), timeout=300)
    assert bare.code == 0, bare.stderr[-1500:]
    rb = json.loads(bare.stdout)
    assert set(rb["artifacts"]) == {"still"}
    for name, t in rb["tools"].items():
        if t["probe"] == "binary":
            assert not t["runnable"], f"{name} probed runnable with an empty PATH"
    assert rb["artifacts"]["still"]["selected"] is None, "code-svg needs node, which an empty PATH hides"
    return {"artifacts": {k: (v["selected"], v["runnable"]) for k, v in rep["artifacts"].items()}}
