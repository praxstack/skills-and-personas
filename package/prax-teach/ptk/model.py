"""Lesson model: load, schema + reference validation (JSON pointers), and the build state machine.

Build state machine (spec §5.3, D18.1):

    draft ─validate─▶ valid ─capture─▶ captured ─project─▶ projected ─verify─▶ claims-pending
                                                                                   │
                                                              claims check ────────┤
                                                                                   ▼
                                                                               verified ─package─▶ packaged
      any failure ─────────────▶ failed      (exit 1 gate / 2 host / 3 model)
      a gate not-run ──────────▶ incomplete  (exit 5)   never "verified"
      a fallback used ─────────▶ degraded    (exit 6)   e.g. `say` TTS; never "verified"

    Invalid: projected → packaged without verify; verified with any not-run gate.
"""
import hashlib
import json
from pathlib import Path

from . import errors, host

SCHEMA = host.PKG / "schemas" / "lesson.schema.json"

TRANSITIONS = {
    "draft": {"valid", "failed"},
    "valid": {"captured", "failed"},
    "captured": {"projected", "failed"},
    "projected": {"claims-pending", "incomplete", "degraded", "failed"},
    "claims-pending": {"verified", "incomplete", "degraded", "failed", "claims-pending"},
    "verified": {"packaged", "claims-pending"},
    "incomplete": {"claims-pending", "failed", "incomplete", "verified", "degraded"},
    "degraded": {"claims-pending", "failed", "degraded"},
    "failed": {"draft"},
    "packaged": set(),
}
FINAL_EXIT = {"verified": errors.EXIT_OK, "packaged": errors.EXIT_OK, "claims-pending": errors.EXIT_CLAIMS_PENDING,
              "incomplete": errors.EXIT_INCOMPLETE, "degraded": errors.EXIT_DEGRADED, "failed": errors.EXIT_GATE}


def advance(current, target):
    if target not in TRANSITIONS.get(current, set()):
        raise errors.IllegalTransition(f"illegal build transition {current} -> {target}", current=current,
                                       target=target)
    return target


class Lesson:
    def __init__(self, path, data):
        self.path = Path(path).resolve()
        self.dir = self.path.parent
        self.data = data

    @property
    def id(self):
        return self.data["id"]

    def sha256(self):
        return hashlib.sha256(canonical(self.data).encode()).hexdigest()

    def by_id(self, section):
        return {x["id"]: x for x in self.data.get(section, [])}

    def fact(self, fid):
        return self.by_id("facts")[fid]

    def claim(self, cid):
        return self.by_id("claims")[cid]

    def state(self, sid):
        return self.by_id("trace")[sid]

    def program(self, pid):
        return self.by_id("programs")[pid]

    def program_source(self, pid):
        return (self.dir / self.program(pid)["path"]).read_text()

    def build_dir(self):
        d = self.dir / "build"
        d.mkdir(exist_ok=True)
        return d

    def save(self):
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load(path):
    p = Path(path)
    if p.is_dir():
        p = p / "lesson.json"
    if not p.exists():
        raise errors.ModelSchemaError(f"no lesson.json at {p}", pointer="")
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise errors.ModelSchemaError(f"lesson.json is not JSON: {e}", pointer="", line=e.lineno)
    return Lesson(p, data)


def _pointer(path_items):
    return "/" + "/".join(str(x).replace("~", "~0").replace("/", "~1") for x in path_items)


def schema_errors(data):
    import jsonschema
    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text()))
    return [{"pointer": _pointer(e.absolute_path), "message": e.message}
            for e in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))]


def reference_errors(data, base_dir=None):
    """Dangling ids: fact->program, claim->fact, misconception->claim, trace->fact/program,
    storyboard->state/claim/fact, figure->program/state/claim; duplicate ids; missing program files."""
    errs = []
    ids = {}
    for section in ("programs", "facts", "claims", "misconceptions", "trace", "storyboard"):
        seen = {}
        for i, item in enumerate(data.get(section, [])):
            if item.get("id") in seen:
                errs.append({"pointer": f"/{section}/{i}/id", "message": f"duplicate id {item['id']!r}"})
            seen[item.get("id")] = i
        ids[section] = seen

    def need(kind, ref, pointer):
        if ref not in ids[kind]:
            errs.append({"pointer": pointer, "message": f"unknown {kind[:-1]} {ref!r}"})

    for i, p in enumerate(data.get("programs", [])):
        if base_dir and not (Path(base_dir) / p["path"]).exists():
            errs.append({"pointer": f"/programs/{i}/path", "message": f"program file {p['path']} missing"})
    from .expect import FUNCTIONS
    for i, f in enumerate(data.get("facts", [])):
        need("programs", f["program"], f"/facts/{i}/program")
        fn = f.get("expect", {}).get("fn")
        if fn is not None and fn not in FUNCTIONS:
            errs.append({"pointer": f"/facts/{i}/expect/fn", "message": f"unknown expect function {fn!r}"})
    for i, c in enumerate(data.get("claims", [])):
        for j, fid in enumerate(c.get("facts", [])):
            need("facts", fid, f"/claims/{i}/facts/{j}")
    for i, m in enumerate(data.get("misconceptions", [])):
        need("claims", m["correction"], f"/misconceptions/{i}/correction")
    for i, s in enumerate(data.get("trace", [])):
        need("programs", s["state"]["program"], f"/trace/{i}/state/program")
        for j, fid in enumerate(s["state"].get("output", [])):
            need("facts", fid, f"/trace/{i}/state/output/{j}")
        for j, fid in enumerate(s.get("reveals", [])):
            need("facts", fid, f"/trace/{i}/reveals/{j}")
    for i, sc in enumerate(data.get("storyboard", [])):
        need("trace", sc["state"], f"/storyboard/{i}/state")
        for j, n in enumerate(sc["narration"]):
            for k, cid in enumerate(n["claims"]):
                need("claims", cid, f"/storyboard/{i}/narration/{j}/claims/{k}")
        if "question" in sc:
            need("facts", sc["question"]["answer_fact"], f"/storyboard/{i}/question/answer_fact")
    fig = data.get("figure")
    if fig:
        need("programs", fig["program"], "/figure/program")
        for j, sid in enumerate(fig.get("states", [])):
            need("trace", sid, f"/figure/states/{j}")
        for j, n in enumerate(fig.get("notes", [])):
            need("claims", n["claim"], f"/figure/notes/{j}/claim")
        for j, cid in enumerate(fig.get("caption_claims", [])):
            need("claims", cid, f"/figure/caption_claims/{j}")
        if fig.get("title_claim"):
            need("claims", fig["title_claim"], "/figure/title_claim")
        if "compare" in fig:
            need("programs", fig["compare"]["program"], "/figure/compare/program")
            need("trace", fig["compare"]["state"], "/figure/compare/state")
            need("claims", fig["compare"]["claim"], "/figure/compare/claim")
    return errs


def captured_errors(data):
    errs = []
    if not data.get("platform", {}).get("captured"):
        errs.append({"pointer": "/platform/captured", "message": "platform facts not captured"})
    for i, f in enumerate(data.get("facts", [])):
        if "value" not in f or "source" not in f:
            errs.append({"pointer": f"/facts/{i}", "message": f"fact {f['id']!r} has no captured value/source"})
    return errs


def validate(lesson, stage="draft"):
    data = lesson.data if isinstance(lesson, Lesson) else lesson
    base = lesson.dir if isinstance(lesson, Lesson) else None
    errs = schema_errors(data)
    if errs:
        raise errors.ModelSchemaError(f"{len(errs)} schema error(s); first at {errs[0]['pointer']}: "
                                      f"{errs[0]['message']}", errors=errs)
    errs = reference_errors(data, base)
    if errs:
        raise errors.ModelReferenceError(f"{len(errs)} reference error(s); first at {errs[0]['pointer']}: "
                                         f"{errs[0]['message']}", errors=errs)
    if stage == "captured":
        errs = captured_errors(data)
        if errs:
            raise errors.ModelReferenceError(f"lesson not captured; first at {errs[0]['pointer']}", errors=errs)
    return True
