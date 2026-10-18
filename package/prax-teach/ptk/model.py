"""Lesson model: load, schema + reference validation (JSON pointers), and the build state machine.

Build state machine (spec §5.3, D18.1):

    draft ─validate─▶ valid ─capture─▶ captured ─project─▶ projected ─verify─▶ claims-pending
                                                                                   │
                                                              claims check ────────┤
                                                                                   ▼
                                                                               verified ─package─▶ packaged
                                                       (--canary builds stop at canary-verified, exit 6, D22.1)
      any failure ─────────────▶ failed      (exit 1 gate / 2 host / 3 model)
      a gate not-run ──────────▶ incomplete  (exit 5)   never "verified"
      a fallback used ─────────▶ degraded    (exit 6)   e.g. `say` TTS; never "verified"

    Invalid: projected → packaged without verify; verified with any not-run gate.
"""
import hashlib
import json
from pathlib import Path

from . import errors, host
from .capture import guard

SCHEMA = host.PKG / "schemas" / "lesson.schema.json"

TRANSITIONS = {
    "draft": {"valid", "failed"},
    "valid": {"captured", "failed"},
    "captured": {"projected", "failed"},
    "projected": {"claims-pending", "incomplete", "degraded", "failed"},
    "claims-pending": {"verified", "canary-verified", "incomplete", "degraded", "failed", "claims-pending"},
    "canary-verified": {"claims-pending", "canary-verified", "failed", "incomplete", "degraded"},
    "verified": {"packaged", "claims-pending"},
    "incomplete": {"claims-pending", "failed", "incomplete", "verified", "canary-verified", "degraded"},
    "degraded": {"claims-pending", "failed", "degraded"},
    "failed": {"draft"},
    "packaged": set(),
}
FINAL_EXIT = {"verified": errors.EXIT_OK, "packaged": errors.EXIT_OK, "claims-pending": errors.EXIT_CLAIMS_PENDING,
              "canary-verified": errors.EXIT_DEGRADED,
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
        """The program text, read with no symlink followed (review WP2 P1-2)."""
        i = next(i for i, p in enumerate(self.data["programs"]) if p["id"] == pid)
        return guard.read_program(self.dir, self.program(pid)["path"], f"/programs/{i}/path").decode("utf-8")

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
    """RFC 6901 JSON pointer; the whole document is the empty string."""
    items = list(path_items)
    return "/" + "/".join(str(x).replace("~", "~0").replace("/", "~1") for x in items) if items else ""


def schema_errors(data):
    import jsonschema
    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text()))
    return [{"pointer": _pointer(e.absolute_path), "message": e.message}
            for e in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))]


# Elements each figure kind always draws (data-key in the artifacts). Storyboard key_nodes may
# name these or the figure's own `elements`.
FIGURE_ELEMENTS = {"code-trace": ("code", "output", "question", "note", "compare")}


def figure_elements(fig):
    """The element ids a figure draws: its kind's fixed set, `panel` when it has one, and its own `elements`."""
    if not fig:
        return set()
    return set(FIGURE_ELEMENTS.get(fig["kind"], ())) | ({"panel"} if fig.get("panel") else set()) \
        | set(fig.get("elements", []))


PLATFORM_KEYS = ("captured", "os", "arch", "sizeof", "char_signed", "endianness", "libc", "compilers", "sandbox")
# The full shape of `platform` as the capture probe writes it (ptk/capture/c_runner.py PLATFORM_C).
# A select key must name one leaf: a scalar key, or sizeof.<type>, or compilers.<name> (review WP2 P2-4).
PLATFORM_LEAVES = {"sizeof": ("char", "short", "int", "long", "long long", "float", "double", "void*"),
                   "compilers": ("clang", "gcc-16")}


def platform_key_problem(key):
    """Why `key` names no single platform value, or None."""
    parts = key.split(".", 1)
    if parts[0] not in PLATFORM_KEYS:
        return f"unknown platform key {key!r}; starts with one of {list(PLATFORM_KEYS)}"
    leaves = PLATFORM_LEAVES.get(parts[0])
    if leaves is None:
        return None if len(parts) == 1 else f"platform key {parts[0]!r} is a single value; drop {'.' + parts[1]!r}"
    if len(parts) == 1 or parts[1] not in leaves:
        return f"platform key {key!r} must be {parts[0]}.<one of {list(leaves)}>"
    return None
PLACEHOLDER = "TODO:"
SECTIONS = ("programs", "facts", "claims", "misconceptions", "trace", "storyboard")


def _expect_problem(exp):
    """Why an {fn, args} expectation cannot be evaluated, or None. Platform-dependent fns are
    checked for arity only, because the platform is unknown before capture."""
    import inspect
    from . import expect
    fn = expect.FUNCTIONS.get(exp["fn"])
    if fn is None:
        return f"unknown expect function {exp['fn']!r}; known: {sorted(expect.FUNCTIONS)}"
    args = list(exp["args"])
    if exp["fn"] in expect.PLATFORM_FUNCTIONS:
        args = [{}, *args]
    try:
        inspect.signature(fn).bind(*args)
    except TypeError as e:
        return f"expect {exp['fn']}{tuple(exp['args'])!r} does not fit {exp['fn']}{inspect.signature(fn)}: {e}"
    if exp["fn"] in expect.PLATFORM_FUNCTIONS:
        return None
    try:
        fn(*args)
    except (TypeError, ValueError, KeyError, IndexError, AttributeError) as e:
        return f"expect {exp['fn']} fails on its args: {type(e).__name__}: {e}"
    return None


def _placeholders(obj, path, errs):
    if isinstance(obj, str):
        if PLACEHOLDER in obj:
            errs.append({"pointer": _pointer(path), "message": f"placeholder {PLACEHOLDER!r} left in; write the real text"})
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _placeholders(v, [*path, k], errs)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _placeholders(v, [*path, i], errs)


def reference_errors(data, base_dir=None):
    """Everything the schema cannot say. Each error is {pointer, message}.

    Dangling ids: fact->program, claim->fact/program, misconception->claim, trace->program/fact,
    storyboard->state/claim/fact/misconception, key node->figure element, figure->program/state/claim.
    Also: duplicate ids, missing program files, unusable expectations, stdout facts of programs that
    never run, ub programs without a covering undefined-behaviour claim, a question whose own scene
    already reveals the answer, summary scenes whose mechanism is never shown (D20.5), placeholders.
    """
    errs = []
    ids = {}
    for section in SECTIONS:
        seen = {}
        for i, item in enumerate(data.get(section, [])):
            if item.get("id") in seen:
                errs.append({"pointer": f"/{section}/{i}/id", "message": f"duplicate id {item['id']!r}"})
            seen[item.get("id")] = i
        ids[section] = seen

    def need(kind, ref, pointer):
        if ref not in ids[kind]:
            errs.append({"pointer": pointer, "message": f"unknown {kind[:-1]} {ref!r}"})
            return False
        return True

    programs = data.get("programs", [])
    for i, p in enumerate(programs):
        if base_dir:  # read with no symlink followed, then the source guard (review WP2 P1-1, P1-2)
            ptr = f"/programs/{i}/path"
            try:
                text = guard.read_program(base_dir, p["path"], ptr).decode("utf-8", "replace")
            except errors.ModelReferenceError as e:
                errs.append({"pointer": ptr, "message": e.message})
            else:
                bad = guard.refusal(guard.scan_source(text), guard.allowed_constructs(data, p), p["path"], ptr, "source")
                if bad:
                    errs.append({"pointer": ptr, "message": bad.message})
        if p["ub"] and p["run"]:
            errs.append({"pointer": f"/programs/{i}/run", "message": "a ub:true program never runs; set run:false"})
        if p["ub"] and not any(c["kind"] == "undefined-behaviour" and p["id"] in c.get("programs", [])
                               for c in data.get("claims", [])):
            errs.append({"pointer": f"/programs/{i}/ub", "message": f"program {p['id']!r} is ub:true but no claim of "
                         "kind undefined-behaviour lists it in `programs`"})
    for i, f in enumerate(data.get("facts", [])):
        if need("programs", f["program"], f"/facts/{i}/program"):
            prog = programs[ids["programs"][f["program"]]]
            if f["select"]["stream"] == "stdout" and (prog["ub"] or not prog["run"]):
                errs.append({"pointer": f"/facts/{i}/select/stream", "message": f"fact reads the stdout of "
                             f"{f['program']!r}, which never runs"})
        why = f["select"]["stream"] == "platform" and platform_key_problem(f["select"]["key"])
        if why:
            errs.append({"pointer": f"/facts/{i}/select/key", "message": why})
        if "fn" in f["expect"]:
            why = _expect_problem(f["expect"])
            if why:
                ptr = "fn" if why.startswith("unknown expect function") else "args"
                errs.append({"pointer": f"/facts/{i}/expect/{ptr}", "message": why})
    for i, c in enumerate(data.get("claims", [])):
        for j, fid in enumerate(c.get("facts", [])):
            need("facts", fid, f"/claims/{i}/facts/{j}")
        for j, pid in enumerate(c.get("programs", [])):
            need("programs", pid, f"/claims/{i}/programs/{j}")
        if c.get("overrides"):
            if not c.get("programs"):
                errs.append({"pointer": f"/claims/{i}/overrides", "message": "a claim with `overrides` lists the "
                             "programs they apply to in `programs`"})
            for pid in c.get("programs", []):
                prog = programs[ids["programs"][pid]] if pid in ids["programs"] else None
                if prog and prog["run"] and not prog["ub"]:
                    errs.append({"pointer": f"/claims/{i}/overrides", "message": f"program {pid!r} runs; a running "
                                 "program never switches its guard off (overrides need ub:true or run:false)"})
    for i, m in enumerate(data.get("misconceptions", [])):
        need("claims", m["correction"], f"/misconceptions/{i}/correction")
    trace = data.get("trace", [])
    for i, s in enumerate(trace):
        need("programs", s["state"]["program"], f"/trace/{i}/state/program")
        for j, fr in enumerate(s["state"].get("frames", [])):
            for k in ("call", "ret", "got"):
                if k in fr:
                    need("facts", fr[k], f"/trace/{i}/state/frames/{j}/{k}")
        for j, fid in enumerate(s["state"].get("output", [])):
            need("facts", fid, f"/trace/{i}/state/output/{j}")
        for j, fid in enumerate(s.get("reveals", [])):
            need("facts", fid, f"/trace/{i}/reveals/{j}")
    errs += _storyboard_errors(data, ids, need)
    errs += _figure_errors(data, need)
    from .project import seal  # question-aware titles (round 18); seal imports nothing from ptk
    errs += seal.problems(data)
    _placeholders(data, [], errs)
    return errs


def _shown_facts(state):
    return set(state["state"].get("output", [])) | set(state.get("reveals", []))


def _storyboard_errors(data, ids, need):
    errs = []
    fig = data.get("figure")
    elements = figure_elements(fig)
    trace = data.get("trace", [])
    shown_states = set()
    for i, sc in enumerate(data.get("storyboard", [])):
        has_state = need("trace", sc["state"], f"/storyboard/{i}/state")
        if has_state:
            shown_states.add(sc["state"])
        for j, n in enumerate(sc["narration"]):
            for k, cid in enumerate(n["claims"]):
                need("claims", cid, f"/storyboard/{i}/narration/{j}/claims/{k}")
            if "spoken" in n:
                errs.append({"pointer": f"/storyboard/{i}/narration/{j}/spoken", "message": "a lesson never authors a "
                             "spoken form: the voice reads lexicon/c.json applied to `text`, so captions and audio say "
                             "the same thing; add a lexicon token or pattern instead"})
        for j, key in enumerate(sc.get("key_nodes", [])):
            if key not in elements:
                errs.append({"pointer": f"/storyboard/{i}/key_nodes/{j}", "message": f"unknown figure element {key!r}"
                             + (f"; the figure has {sorted(elements)}" if fig else "; the lesson has no figure")})
        if sc.get("view") == "summary" and need("trace", sc["mechanism"], f"/storyboard/{i}/mechanism") \
                and sc["mechanism"] not in shown_states:
            errs.append({"pointer": f"/storyboard/{i}/mechanism", "message": f"summary scene {sc['id']!r} pairs with "
                         f"state {sc['mechanism']!r}, which no earlier or same scene shows (D20.5)"})
        q = sc.get("question")
        if not q:
            continue
        if need("facts", q["answer_fact"], f"/storyboard/{i}/question/answer_fact") and has_state \
                and q["answer_fact"] in _shown_facts(trace[ids["trace"][sc["state"]]]):
            errs.append({"pointer": f"/storyboard/{i}/question/answer_fact", "message": f"the scene's own state "
                         f"{sc['state']!r} already shows the answer {q['answer_fact']!r}"})
        opts = q.get("options", [])
        if opts and sum(o["correct"] for o in opts) != 1:
            errs.append({"pointer": f"/storyboard/{i}/question/options", "message": "exactly one option must be correct"})
        for j, o in enumerate(opts):
            if not o["correct"] and "misconception" not in o:
                errs.append({"pointer": f"/storyboard/{i}/question/options/{j}", "message": "a wrong option must name "
                             "the misconception it reveals"})
            elif "misconception" in o:
                need("misconceptions", o["misconception"], f"/storyboard/{i}/question/options/{j}/misconception")
    return errs


def _figure_errors(data, need):
    fig = data.get("figure")
    if not fig:
        return []
    need("programs", fig["program"], "/figure/program")
    for j, sid in enumerate(fig.get("states", [])):
        need("trace", sid, f"/figure/states/{j}")
    for j, n in enumerate(fig.get("notes", [])):
        need("claims", n["claim"], f"/figure/notes/{j}/claim")
    for j, cid in enumerate(fig.get("caption_claims", [])):
        need("claims", cid, f"/figure/caption_claims/{j}")
    if fig.get("title_claim"):
        need("claims", fig["title_claim"], "/figure/title_claim")
    if fig.get("misconception"):
        need("misconceptions", fig["misconception"], "/figure/misconception")
    for k, ref in panel_refs(fig.get("panel") or {}):
        need(*ref, f"/figure/panel/{k}")
    ex = fig.get("explore") or {}
    for i, v in enumerate(ex.get("values", [])):
        need("programs", v["program"], f"/figure/explore/values/{i}/program")
        for role, fid in v["facts"].items():
            need("facts", fid, f"/figure/explore/values/{i}/facts/{role}")
        for j, cid in enumerate(v.get("claims", [])):
            need("claims", cid, f"/figure/explore/values/{i}/claims/{j}")
    for j, cid in enumerate(ex.get("claims", [])):
        need("claims", cid, f"/figure/explore/claims/{j}")
    for i, c in enumerate(ex.get("checks", [])):
        need("programs", c["program"], f"/figure/explore/checks/{i}/program")
        for role, fid in c["facts"].items():
            need("facts", fid, f"/figure/explore/checks/{i}/facts/{role}")
    if "compare" in fig:
        need("programs", fig["compare"]["program"], "/figure/compare/program")
        need("trace", fig["compare"]["state"], "/figure/compare/state")
        need("claims", fig["compare"]["claim"], "/figure/compare/claim")
    return []


def panel_refs(panel):
    """[(json pointer tail, (section, id))] for every id a panel names."""
    out = []
    v = panel.get("value") or {}
    out += [(f"value/{k}", ("facts", v[k])) for k in ("bits", "hex") if k in v]
    for i, ln in enumerate(panel.get("lanes", [])):
        out += [(f"lanes/{i}/{k}", ("facts" if k != "claim" else "claims", ln[k])) for k in ("fact", "via", "claim") if k in ln]
    ub = panel.get("ub")
    if ub:
        out += [("ub/program", ("programs", ub["program"])), ("ub/claim", ("claims", ub["claim"])),
                ("ub/after", ("trace", ub["after"]))]
    for i, t in enumerate(panel.get("terms", [])):
        out += [(f"terms/{i}/{k}", ("facts", t[k])) for k in ("x", "w", "t")]
    out += [(k, ("facts", panel[k])) for k in ("bias", "sum", "out") if k in panel]
    out += [(f"claims/{i}", ("claims", c)) for i, c in enumerate(panel.get("claims", []))]
    return out


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
        raise errors.ModelReferenceError(f"{len(errs)} model error(s); first at {errs[0]['pointer']}: "
                                         f"{errs[0]['message']}", errors=errs)
    if stage == "captured":
        errs = captured_errors(data)
        if errs:
            raise errors.ModelReferenceError(f"lesson not captured; first at {errs[0]['pointer']}", errors=errs)
    return True


# ---------------------------------------------------------------- ptk new

SCAFFOLD_PROGRAM = """#include <stdio.h>

int main(void) {
    puts("hello");
    return 0;
}
"""


def scaffold_data(slug):
    """A schema-valid lesson whose prose is all `TODO:` placeholders. `ptk validate` lists each
    placeholder by JSON pointer until the author replaces it (references/LESSON-MODEL.md)."""
    todo = PLACEHOLDER
    return {
        "schema": "prax-teach/lesson@1", "id": slug, "title": f"{todo} lesson title", "topic": f"{todo} topic",
        "language": "c", "request": f"{todo} the learner's request, verbatim",
        "programs": [{"id": "p1", "path": "programs/main.c", "std": "c17", "ub": False, "run": True}],
        "facts": [{"id": "f.p1.l1", "program": "p1", "kind": "stdout-line", "select": {"stream": "stdout", "line": 1},
                   "expect": {"value": "hello", "reviewed": True}}],
        "claims": [{"id": "c.one", "text": f"{todo} one teaching sentence.", "kind": "mechanism",
                    "justification": f"{todo} why this sentence is true, citing the clause or the run.",
                    "sources": [{"title": "ISO/IEC 9899:2018 (C17), working draft N2176",
                                 "url": "https://www.open-std.org/jtc1/sc22/wg14/www/docs/n2176.pdf",
                                 "clause": f"{todo} clause"}],
                    "facts": ["f.p1.l1"]}],
        "misconceptions": [],
        "trace": [{"id": "s0", "label": f"{todo} what this state shows",
                   "state": {"program": "p1", "line": 4, "path": [4], "output": ["f.p1.l1"], "vars": {}},
                   "reveals": ["f.p1.l1"]}],
        "storyboard": [{"id": "sc1", "title": f"{todo} scene title", "state": "s0", "key_nodes": ["code", "output"],
                        "narration": [{"text": f"{todo} one teaching sentence.", "claims": ["c.one"]}]}],
        "figure": {"kind": "code-trace", "program": "p1", "states": ["s0"]},
        "requested_media": ["still"],
    }


def scaffold(slug, parent):
    """`ptk new <slug> [--dir lessons]`: write <parent>/<slug>/lesson.json and programs/main.c."""
    import re
    if not re.fullmatch(json.loads(SCHEMA.read_text())["$defs"]["slug"]["pattern"], slug):
        raise errors.ModelSchemaError(f"bad lesson slug {slug!r}: lower-case letters, digits, '.' and '-'",
                                      pointer="/id")
    root = Path(parent).resolve() / slug
    if root.exists():
        raise errors.ModelSchemaError(f"{root} already exists; ptk new never overwrites a lesson", pointer="",
                                      path=str(root))
    (root / "programs").mkdir(parents=True)
    (root / "programs" / "main.c").write_text(SCAFFOLD_PROGRAM)
    lesson = Lesson(root / "lesson.json", scaffold_data(slug))
    lesson.save()
    todo = []
    _placeholders(lesson.data, [], todo)
    return {"created": str(root), "files": [str(lesson.path), str(root / "programs" / "main.c")],
            "placeholders": [e["pointer"] for e in todo],
            "next": "replace every TODO: (see references/LESSON-MODEL.md), then `ptk validate " + str(root) + "`"}
