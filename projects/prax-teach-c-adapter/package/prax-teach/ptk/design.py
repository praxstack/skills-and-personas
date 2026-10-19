"""Screenshot design review (AC-9.3, D20.1, D20.2): the six aesthetics items no gate can judge.

The nine automated items of the still bar are gates (contrast, OCR lining figures, overflow at 390 and 1440,
light and dark, portrait, bundled fonts, no network, alt text, source link). These six need a person or an
agent looking at the screenshots, judged against the accepted Neuron Atlas still. A verdict is recorded in
the build report under `design_review`, bound to the lesson sha256 and to the sha256 of every screenshot it
cites, so a rebuild (new report) or a changed screenshot makes it stale.

    ptk design record <lesson> --verdicts verdicts.json

verdicts.json: {"reviewer": "...", "reference": "<path to the Atlas PNG>",
                "items": {"<item id>": {"verdict": "pass" | "pass-with-notes" | "fail",
                                        "note": "...", "shots": ["still/x.png", "shots/ive-390-dark.png", ...]}}}
"""
import json
import time
from pathlib import Path

from . import errors, host

ITEMS = {
    "hierarchy": "One focal mechanism per view; the eye reads title, mechanism, then values, with nothing competing.",
    "mechanism-visible": "Every summary (an output, a total, a result) sits next to the step that produced it (D20.5).",
    "not-color-alone": "States and roles also differ by label, shape or line style, not only by hue.",
    "atlas-dark-parity": "The dark variant matches the Atlas palette and type: navy ground, lavender path, coral "
                         "correction, mint values, sans display over mono numbers; figure ground equals page ground.",
    "composition": "No empty regions, no orphaned words or values, balanced columns, nothing cramped at 390 or 1440.",
    "motion": "Film and IVE: no hard cuts, chrome (gutter, file, output) steady through transitions, captions clear "
              "of the picture and controls.",
}
VERDICTS = ("pass", "pass-with-notes", "fail")


def _report(lesson_dir):
    p = Path(lesson_dir) / "build" / "build-report.json"
    if not p.exists():
        raise errors.ModelReferenceError(f"no build report at {p}; build first")
    return p, json.loads(p.read_text())


def problems(lesson_dir, rep=None):
    """Why the recorded design review does not cover this build ([] when it does)."""
    if rep is None:
        _p, rep = _report(lesson_dir)
    d = rep.get("design_review")
    if not d:
        return ["no design_review in the build report"]
    out = []
    if d.get("lesson_sha256") != rep.get("lesson_sha256"):
        out.append("design_review is for another lesson version")
    ref = Path(d.get("reference", {}).get("path", ""))
    if not ref.exists() or host.sha256_file(ref) != d["reference"].get("sha256"):
        out.append("reference image missing or changed")
    build = Path(lesson_dir) / "build"
    if sorted(d.get("items", {})) != sorted(ITEMS):
        out.append(f"items {sorted(d.get('items', {}))} are not the six {sorted(ITEMS)}")
    for k, it in d.get("items", {}).items():
        if it.get("verdict") not in VERDICTS:
            out.append(f"{k}: verdict {it.get('verdict')!r}")
        if len((it.get("note") or "").split()) < 6:
            out.append(f"{k}: the note does not say what was seen")
        if not it.get("shots"):
            out.append(f"{k}: no screenshots cited")
        for s in it.get("shots", []):
            f = build / s["path"]
            if not f.is_file() or host.sha256_file(f) != s["sha256"]:
                out.append(f"{k}: screenshot {s['path']} missing or changed since the review")
    return out


def record(lesson_dir, verdicts_path):
    p, rep = _report(lesson_dir)
    v = json.loads(Path(verdicts_path).read_text())
    build = Path(lesson_dir) / "build"
    items = {}
    for k, it in v.get("items", {}).items():
        shots = []
        for s in it.get("shots", []):
            f = build / s
            if not f.is_file():
                raise errors.ModelReferenceError(f"{k}: screenshot {s} is not in {build}", pointer=f"/items/{k}/shots")
            shots.append({"path": s, "sha256": host.sha256_file(f)})
        items[k] = {"verdict": it.get("verdict"), "note": it.get("note", ""), "shots": shots,
                    "question": ITEMS.get(k, "")}
    ref = Path(v["reference"])
    rep["design_review"] = {"reviewer": v.get("reviewer", ""), "recorded": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                            "lesson_sha256": rep.get("lesson_sha256"),
                            "reference": {"path": str(ref), "sha256": host.sha256_file(ref) if ref.exists() else None},
                            "items": items}
    probs = problems(lesson_dir, rep)
    if probs:
        raise errors.ModelReferenceError("design review incomplete: " + "; ".join(probs[:5]), problems=probs)
    p.write_text(json.dumps(rep, indent=2, default=str))
    return {"recorded": sorted(items), "verdicts": {k: i["verdict"] for k, i in items.items()}}
