"""Shared setup for the agent-mediated claims tests (AC-7.5, AC-7.6). Not a test module.

Jobs go to $PTK_STATE/agent-tests/claims/<name>/claims-jobs, reviews to .../claims-review.
`ensure_jobs` rewrites the jobs from the current inputs; reviews for unchanged job ids are kept
(a job id is its manifest hash), so a finished run stays finished until an input changes.
"""
import copy
import json

from _util import SLICE
from ptk import host, model
from ptk.verify import claims

FIXTURES = host.PKG / "tests" / "fixtures" / "claims"
F_CAST = FIXTURES / "f-cast"
SAME_BITS = "printf never changes the bits; the format string only decides how to read them."


class FixtureLesson(model.Lesson):
    """A fixture is never captured, so its program text is read directly. (Something on this host
    hard-links freshly written files, and the capture guard rightly refuses a linked program.)"""

    def program_source(self, pid):
        return (self.dir / self.program(pid)["path"]).read_text()


def _fixture(path):
    base = model.load(path)
    return FixtureLesson(base.path, base.data)


def staging(name):
    """Per rubric version (v2.2 A3), so a rubric bump writes fresh jobs beside an older run's reviews instead of
    deleting them: those reviews stay as evidence of what the older rubric produced."""
    d = host.state_path("agent-tests", "claims", f"rubric-v{claims.RUBRIC_VERSION}", name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def slice_lesson():
    """(lesson, items) for the switch slice from its current build artifacts, or None."""
    if not (SLICE / "build" / "still").is_dir():
        return None
    lesson = model.load(SLICE)
    return lesson, claims.collect_texts(lesson, SLICE / "build")


def slice_snapshot():
    """A frozen copy of the switch slice (lesson.json, programs, mutations.json, sources) for the rates suite, so
    the measurement doesn't move while other packages edit the slice. Texts come from the model.
    Delete the snapshot folder to re-measure against the current slice."""
    snap = staging("snapshots/switch-fallthrough")
    if not (snap / "lesson.json").exists():
        (snap / "programs").mkdir(exist_ok=True)
        for p in (SLICE / "programs").glob("*.c"):
            (snap / "programs" / p.name).write_text(p.read_text())
        (snap / "mutations.json").write_text((SLICE / "mutations.json").read_text())
        (snap / "sources").mkdir(exist_ok=True)
        for p in (SLICE / "sources").glob("*.txt"):
            (snap / "sources" / p.name).write_text(p.read_text())
        (snap / "lesson.json").write_text((SLICE / "lesson.json").read_text())
    lesson = _fixture(snap)
    return lesson, claims.texts_from_model(lesson)


def fcast_lesson():
    lesson = _fixture(F_CAST)
    return lesson, claims.texts_from_model(lesson)


def same_bits_lesson():
    """The f-cast lesson as an author who believes the 'same bits' story would write it: c.cast says
    the format string only reads the bits, with a matching justification and citation."""
    base = _fixture(F_CAST)
    data = copy.deepcopy(base.data)
    for c in data["claims"]:
        if c["id"] == "c.cast":
            c["text"] = SAME_BITS
            c["justification"] = ("printf reads each argument according to its conversion specification; "
                                  "%f interprets the argument's bits as a double, so 66.000000 is printed.")
            c["sources"] = [{"title": "ISO/IEC 9899:2018 (C17), working draft N2176",
                             "url": "https://www.open-std.org/jtc1/sc22/wg14/www/docs/n2176.pdf",
                             "clause": "§7.21.6.1 ¶8",
                             "quote": "f,F A double argument representing a floating-point number is converted to "
                                      "decimal notation in the style [−]ddd.ddd",
                             "excerpts": ["sources/n2310-7.21.6.1p8-f.txt"]}]
    for sc in data["storyboard"]:
        sc["narration"] = [dict(n, text=SAME_BITS) if n["claims"] == ["c.cast"] else n for n in sc["narration"]]
    lesson = FixtureLesson(base.path, data)
    return lesson, claims.texts_from_model(lesson)


def ensure_jobs(name, lesson, items, mutations=None, canary=False):
    build = staging(name)
    claims.mapping_gate(lesson, items)
    claims.write_jobs(lesson, items, build, mutations=mutations, canary=canary)
    return build


def run_check(lesson, items, build):
    gates = {g["id"]: g for g in claims.check(lesson, build, items)}
    priv = claims.load_private(build)
    jobs = sorted(str(build / "claims-jobs" / f"{j}.json") for j in priv["jobs"]
                  if not (build / "claims-review" / f"{j}.json").exists())
    return gates, priv, jobs


def review_of(build, job_id):
    p = build / "claims-review" / f"{job_id}.json"
    return json.loads(p.read_text()) if p.exists() else None
