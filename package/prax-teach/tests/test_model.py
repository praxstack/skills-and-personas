"""WP2 lesson model: AC-2.1 (validation with JSON pointers, exit 3), AC-2.7 (ExpectationMismatch), ptk new.

Each broken lesson starts from the switch-fallthrough slice (which must stay valid) and breaks one
thing, so each case names exactly the pointer it expects.
"""
import copy
import json
import shutil

from _util import SLICE, ptk_cmd
from ptk import errors, host, model
from ptk.verify import values


def _slice():
    return json.loads((SLICE / "lesson.json").read_text())


def _idx(data, section, item_id):
    return next(i for i, x in enumerate(data[section]) if x["id"] == item_id)


def _pointers(data, base_dir=SLICE):
    """The pointers model.validate reports for data, and the error class."""
    try:
        model.validate(model.Lesson(base_dir / "lesson.json", data))
    except errors.ModelError as e:
        assert e.exit_code == errors.EXIT_MODEL
        return type(e).__name__, [x["pointer"] for x in e.detail["errors"]]
    return None, []


def _broken_cases():
    """(name, mutate(data) -> expected pointer, expected error class)."""
    def schema_kind(d):
        d["claims"][0]["kind"] = "opinion"
        return "/claims/0/kind"

    def schema_missing_title(d):
        del d["title"]
        return ""

    def claim_to_fact(d):
        i = _idx(d, "claims", "c.recap")
        d["claims"][i]["facts"] = ["f.nope"]
        return f"/claims/{i}/facts/0"

    def storyboard_to_state(d):
        d["storyboard"][0]["state"] = "s.nope"
        return "/storyboard/0/state"

    def narration_to_claim(d):
        d["storyboard"][0]["narration"][0]["claims"] = ["c.nope"]
        return "/storyboard/0/narration/0/claims/0"

    def misconception_to_claim(d):
        d["misconceptions"][0]["correction"] = "c.nope"
        return "/misconceptions/0/correction"

    def key_node_to_figure(d):
        d["storyboard"][0]["key_nodes"] = ["code", "gauge"]
        return "/storyboard/0/key_nodes/1"

    def unknown_expect_fn(d):
        d["facts"][0]["expect"] = {"fn": "no_such_fn", "args": []}
        return "/facts/0/expect/fn"

    def expect_args_do_not_fit(d):
        d["facts"][0]["expect"] = {"fn": "printf_d", "args": [1, 2, 3]}
        return "/facts/0/expect/args"

    def duplicate_id(d):
        d["claims"].append(copy.deepcopy(d["claims"][0]))
        return f"/claims/{len(d['claims']) - 1}/id"

    def ub_without_claim(d):
        d["programs"][1].update(ub=True, run=False)
        for f in d["facts"]:
            f["program"] = "p1"
        return "/programs/1/ub"

    def stdout_of_compile_only_program(d):
        d["programs"][1]["run"] = False
        return f"/facts/{next(i for i, f in enumerate(d['facts']) if f['program'] == 'p2')}/select/stream"

    def summary_without_mechanism(d):
        d["storyboard"][-1]["view"] = "summary"
        return f"/storyboard/{len(d['storyboard']) - 1}"

    def summary_mechanism_never_shown(d):
        d["storyboard"][0].update(view="summary", mechanism="s4")
        return "/storyboard/0/mechanism"

    def question_scene_reveals_answer(d):
        i = next(i for i, sc in enumerate(d["storyboard"]) if "question" in sc)
        d["storyboard"][i]["question"]["answer_fact"] = d["trace"][1]["reveals"][0]
        d["storyboard"][i]["state"] = d["trace"][1]["id"]
        return f"/storyboard/{i}/question/answer_fact"

    def wrong_option_without_misconception(d):
        i = next(i for i, sc in enumerate(d["storyboard"]) if "question" in sc)
        d["storyboard"][i]["question"]["options"] = [{"text": "two three done", "correct": True},
                                                     {"text": "two done", "correct": False}]
        return f"/storyboard/{i}/question/options/1"

    def placeholder_left(d):
        d["claims"][0]["text"] = "TODO: write this sentence."
        return "/claims/0/text"

    def bad_platform_key(d):
        d["facts"][0]["select"] = {"stream": "platform", "key": "cpu.cores"}
        return "/facts/0/select/key"

    return [schema_kind, schema_missing_title, claim_to_fact, storyboard_to_state, narration_to_claim,
            misconception_to_claim, key_node_to_figure, unknown_expect_fn, expect_args_do_not_fit, duplicate_id,
            ub_without_claim, stdout_of_compile_only_program, summary_without_mechanism,
            summary_mechanism_never_shown, question_scene_reveals_answer, wrong_option_without_misconception,
            placeholder_left, bad_platform_key]


def test_validation_errors():
    """AC-2.1: schema violations and dangling references are rejected with JSON pointers, exit 3."""
    clean_cls, clean = _pointers(_slice())
    assert clean_cls is None, f"the slice itself does not validate: {clean}"
    seen = {}
    for case in _broken_cases():
        data = _slice()
        want = case(data)
        cls, got = _pointers(data)
        assert cls is not None, f"{case.__name__}: validated, expected an error at {want!r}"
        assert want in got, f"{case.__name__}: expected pointer {want!r}, got {got}"
        seen[case.__name__] = {"error": cls, "pointers": got}
    assert seen["schema_kind"]["error"] == "ModelSchemaError"
    assert seen["claim_to_fact"]["error"] == "ModelReferenceError"

    # several dangling references at once: all reported, not just the first
    data = _slice()
    data["storyboard"][0]["state"] = "s.nope"
    data["misconceptions"][0]["correction"] = "c.nope"
    data["storyboard"][0]["narration"][0]["claims"] = ["c.nope"]
    _cls, got = _pointers(data)
    assert {"/storyboard/0/state", "/misconceptions/0/correction", "/storyboard/0/narration/0/claims/0"} <= set(got)

    # through the CLI: exit 3, and the pointers on stdout as JSON
    tmp = host.make_tmp("model-cli-")
    try:
        dst = tmp / "lesson"
        shutil.copytree(SLICE, dst, ignore=shutil.ignore_patterns("build"))
        (dst / "lesson.json").write_text(json.dumps(data, indent=2))
        res = host.run([*ptk_cmd(), "validate", str(dst)], timeout=120)
        assert res.code == errors.EXIT_MODEL, f"ptk validate exited {res.code}: {res.stderr[-400:]}"
        out = json.loads(res.stdout)
        assert out["valid"] is False and "/storyboard/0/state" in [e["pointer"] for e in out["errors"]], out
        (dst / "lesson.json").write_text("{not json")
        res = host.run([*ptk_cmd(), "validate", str(dst)], timeout=120)
        assert res.code == errors.EXIT_MODEL and json.loads(res.stdout)["error"] == "ModelSchemaError", res.stdout
        res = host.run([*ptk_cmd(), "validate", str(SLICE)], timeout=120)
        assert res.code == 0 and json.loads(res.stdout)["valid"] is True, res.stdout + res.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {name: v["pointers"][:3] for name, v in seen.items()}


def test_expectation_mismatch():
    """AC-2.7: when capture differs from the independent expect, the build fails with
    ExpectationMismatch, showing both values."""
    lesson = model.load(SLICE)
    tampered = copy.deepcopy(lesson.data)
    i = _idx(tampered, "facts", "f.p1.l1")
    tampered["facts"][i]["value"] = "one"
    try:
        values.check_expectations(model.Lesson(SLICE / "lesson.json", tampered))
    except errors.ExpectationMismatch as e:
        mm = e.detail["mismatches"]
        assert mm == [{"fact": "f.p1.l1", "captured": "one", "expected": "two"}], mm
    else:
        raise AssertionError("a captured value that differs from expect passed")

    # end to end: change the program so the real run differs from the expectation
    tmp = host.make_tmp("model-mismatch-")
    try:
        dst = tmp / "lesson"
        shutil.copytree(SLICE, dst, ignore=shutil.ignore_patterns("build"))
        src = dst / "programs" / "fallthrough.c"
        assert 'puts("two");' in src.read_text(), "fixture changed: fallthrough.c no longer prints two"
        src.write_text(src.read_text().replace('puts("two");', 'puts("TWO");'))
        res = host.run([*ptk_cmd(), "build", str(dst), "--only", "still"], timeout=600)
        assert res.code == errors.EXIT_GATE, f"build exited {res.code}: {res.stderr[-600:]}"
        err = json.loads(res.stderr[res.stderr.index("{"):])
        assert err["error"] == "ExpectationMismatch", err
        first = next(m for m in err["mismatches"] if m["fact"] == "f.p1.l1")
        assert first["captured"] == "TWO" and first["expected"] == "two", first
        rep = json.loads((dst / "build" / "build-report.json").read_text())
        assert rep["status"] == "failed", rep["status"]
        return {"mismatches": err["mismatches"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_new_scaffold():
    """`ptk new <slug>`: schema-valid scaffold whose prose is TODO: placeholders that validate lists;
    filled in, it validates and captures."""
    tmp = host.make_tmp("model-new-")
    try:
        res = host.run([*ptk_cmd(), "new", "my-lesson", "--dir", str(tmp)], timeout=120)
        assert res.code == 0, res.stderr[-400:]
        made = json.loads(res.stdout)
        root = tmp / "my-lesson"
        assert (root / "lesson.json").is_file() and (root / "programs" / "main.c").is_file()
        assert made["placeholders"], made

        data = json.loads((root / "lesson.json").read_text())
        assert not model.schema_errors(data), model.schema_errors(data)
        res = host.run([*ptk_cmd(), "validate", str(root)], timeout=120)
        assert res.code == errors.EXIT_MODEL, res.stdout
        listed = json.loads(res.stdout)["errors"]
        assert {e["pointer"] for e in listed} == set(made["placeholders"]), listed
        assert all("placeholder" in e["message"] for e in listed), listed

        again = host.run([*ptk_cmd(), "new", "my-lesson", "--dir", str(tmp)], timeout=120)
        assert again.code == errors.EXIT_MODEL, "ptk new overwrote an existing lesson"
        bad = host.run([*ptk_cmd(), "new", "My Lesson", "--dir", str(tmp)], timeout=120)
        assert bad.code == errors.EXIT_MODEL, "ptk new accepted a bad slug"

        filled = json.loads(json.dumps(data).replace("TODO: ", ""))
        (root / "lesson.json").write_text(json.dumps(filled, indent=2))
        res = host.run([*ptk_cmd(), "validate", str(root)], timeout=120)
        assert res.code == 0, res.stdout
        res = host.run([*ptk_cmd(), "capture", str(root)], timeout=300)
        assert res.code == 0, res.stderr[-600:]
        assert json.loads(res.stdout)["facts"] == {"f.p1.l1": "hello"}, res.stdout
        return {"placeholders": len(made["placeholders"])}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
