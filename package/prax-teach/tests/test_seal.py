"""Round 18, review X2 (AC-5.7): titles are claim-tagged and question-aware (ptk/project/seal.py).

The known leak: one-byte asks what printf("%f\\n", (double)a) prints, and the IVE chapter list and the Q&A
showed "Six digits after the point" from the moment the page loaded."""
import copy

from _util import V21
from ptk import errors, model
from ptk.project import seal

ONE_BYTE = V21 / "lessons" / "one-byte-four-views"


def _data():
    return copy.deepcopy(model.load(ONE_BYTE).data)


def _scene_citing(d, cid):
    return next(sc for sc in d["storyboard"] if any(cid in n["claims"] for n in sc["narration"]))


def test_the_six_digits_title_is_sealed():
    d = _data()
    sc = _scene_citing(d, "c.fprint")
    q = next(s for s in d["storyboard"] if s.get("question"))
    assert seal.sealed(d).get(sc["id"]) == q["id"], seal.sealed(d)


def test_an_untagged_title_after_a_question_is_a_model_error():
    d = _data()
    sc = _scene_citing(d, "c.fprint")
    del sc["title_claims"]
    i = d["storyboard"].index(sc)
    errs = seal.problems(d)
    assert any(e["pointer"] == f"/storyboard/{i}/title_claims" for e in errs), errs
    try:
        model.validate(d)
    except errors.ModelReferenceError as e:
        assert any(x["pointer"] == f"/storyboard/{i}/title_claims" for x in e.detail["errors"])
    else:
        raise AssertionError("validate accepted an untagged title after a question")


def test_a_title_before_the_question_may_not_state_the_answer():
    d = _data()
    d["storyboard"][0]["title_claims"] = ["c.fprint"]
    errs = seal.problems(d)
    assert any(e["pointer"] == "/storyboard/0/title_claims" and "answer" in e["message"] for e in errs), errs


def test_the_lesson_title_may_not_state_the_answer():
    d = _data()
    d["title_claims"] = ["c.fprint"]
    assert any(e["pointer"] == "/title_claims" for e in seal.problems(d))


def test_a_neutral_title_is_not_sealed():
    d = _data()
    sc = _scene_citing(d, "c.fprint")
    sc["title_claims"] = []
    assert sc["id"] not in seal.sealed(d)


def test_every_lesson_validates():
    for p in sorted((V21 / "lessons").iterdir()):
        if (p / "lesson.json").exists():
            model.validate(model.load(p))
