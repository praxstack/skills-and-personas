"""Round 18, review P1 (interaction) and P1 (factorial n and r): the explorer knob and the stack's variables.

The knob's values come from captured runs (one-byte, factorial) or ptk/expect_neuron.py (neuron sliders); the
stack frames show their own n and r, derived from facts and the program source. Each test also shows the
check failing on a planted error."""
import copy

from _util import V21
from selftest_support import NotRun
from ptk import expect, expect_neuron, model
from ptk.project import knob, mech

FACT = V21 / "lessons" / "factorial-stack"
NEURON = V21 / "lessons" / "neuron"
BYTE = V21 / "lessons" / "one-byte-four-views"


def test_call_steps_for_factorial_3():
    got = [(s["printed"][-1], [(f["label"], f["status"], f["n"], f["r"], f["slot"]) for f in s["frames"]])
           for s in knob.expected_calls(3)]
    assert got[1][1] == [("factorial(2)", "running", "2", "r = ?", False), ("factorial(3)", "waiting", "3", "r = 3 *", True),
                         ("main", "waiting", None, "r =", True)]
    assert got[4] == ("factorial(2) = 2", [("factorial(2)", "returning", "2", "r = 2 * 1", False),
                                          ("factorial(3)", "waiting", "3", "r = 3 *", True), ("main", "waiting", None, "r =", True)])
    assert got[6] == ("main got 6", [("main", "running", None, "r = 6", False)])


def test_call_steps_every_n():
    for n in range(1, 6):
        st = knob.expected_calls(n)
        assert len(st) == 2 * n + 1
        assert st[-1]["frames"] == [{"label": "main", "status": "running", "n": None, "r": f"r = {expect.factorial(n)}",
                                     "slot": False, "ret": None}]
        assert max(len(s["frames"]) for s in st) == n + 1


def test_calls_check_catches_a_wrong_frame():
    lesson = model.load(FACT)
    if not all(f.get("value") for f in lesson.data["facts"]):
        raise NotRun("factorial-stack not captured yet")
    rec = {"knob": [{"value": v["value"], "frames": [{"label": f["label"], "status": f["status"],
                                                      "vars": ([f"n = {f['n']}"] if f["n"] is not None else []) + [f["r"]],
                                                      "slot": f["slot"]} for f in s["frames"]], "printed": s["printed"]}
                    for v in lesson.data["figure"]["explore"]["values"] for s in knob.expected_calls(v["value"])]}
    probs, n = knob.check(lesson, rec)
    assert not probs and n == 35, probs[:3]
    bad = copy.deepcopy(rec)
    bad["knob"][5]["frames"][0]["vars"][-1] = "r = 1"
    assert knob.check(lesson, bad)[0]


def test_neuron_grid_matches_c_doubles():
    s = expect_neuron.shown(0.8, 1.5, 0.4, -1.0, -0.2)
    assert (s["t1"], s["t2"], s["z"], s["a"]) == ("+1.2", "-0.4", "0.6", "0.6")
    assert s["num"]["z"] != 0.6  # the double is not exactly 0.6; %g hides it
    z = expect_neuron.shown(0.8, 1.5, 0.4, -1.0, -1.0)
    assert (z["z"], z["a"]) == ("-0.2", "0")
    assert expect_neuron.steps(-1.0, 1.0, 0.1)[3] == -0.7 and len(expect_neuron.steps(-2.0, 2.0, 0.1)) == 41
    assert expect_neuron.lines(0.8, 1.5, 0.4, 0.5, 0.3) == ["0.8 * 1.5 = +1.2", "0.4 * 0.5 = +0.2", "b = +0.3  z = 1.7", "a = 1.7"]


def test_neuron_domain_and_spot_checks():
    lesson = model.load(NEURON)
    if not all(f.get("value") for f in lesson.data["facts"]):
        raise NotRun(f"{lesson.id} not captured yet")
    probs, T = knob.neuron_problems(lesson)
    assert not probs, probs[:3]
    assert len(T["rows"]) == 41 * 21
    tampered = copy.deepcopy(lesson.data)
    lesson2 = model.Lesson(lesson.path, tampered)
    fid = tampered["figure"]["explore"]["checks"][0]["facts"]["z"]
    next(f for f in tampered["facts"] if f["id"] == fid)["value"] = "b = -1  z = -0.3"
    assert any("captured" in p for p in knob.neuron_problems(lesson2)[0])


def test_frames_show_their_own_n_and_r():
    """The stack panel at every factorial state: n from the call fact, r unset, waiting in a slot, or received."""
    lesson = model.load(FACT)
    if not all(f.get("value") for f in lesson.data["facts"]):
        raise NotRun(f"{lesson.id} not captured yet")
    def show(sid):
        st = lesson.state(sid)["state"]
        out = []
        for i in range(len(st["frames"])):
            vs = mech.frame_vars(lesson, sid, i)
            row = []
            for v in vs:
                if v["kind"] == "param":
                    row.append(f"{v['name']} = {v['text']}")
                elif v["kind"] == "unset":
                    row.append(f"{v['name']} = ?")
                elif v["kind"] == "value":
                    row.append(f"{v['name']} = {lesson.fact(v['fact'])['value']}")
                else:
                    got = lesson.fact(v["got"])["value"] if v.get("got") else "▢"
                    row.append(f"{v['name']} = {(v['prefix'] + ' ') if v['prefix'] else ''}{got}")
            out.append(row)
        return out
    assert show("s0") == [["r = ▢"], ["n = 3", "r = ?"]]
    assert show("s1") == [["r = ▢"], ["n = 3", "r = 3 * ▢"], ["n = 2", "r = ?"]]
    assert show("s3") == [["r = ▢"], ["n = 3", "r = 3 * ▢"], ["n = 2", "r = 2 * ▢"], ["n = 1", "r = 1"]]
    assert show("s4") == [["r = ▢"], ["n = 3", "r = 3 * ▢"], ["n = 2", "r = 2 * 1"]]
    assert show("s5") == [["r = ▢"], ["n = 3", "r = 3 * 2"]]
    assert show("s6") == [["r = 6"]]
    # every frame in every state shows r, and every factorial frame shows n
    for st in lesson.data["trace"]:
        for i, fr in enumerate(st["state"]["frames"]):
            names = [v["name"] for v in mech.frame_vars(lesson, st["id"], i)]
            assert "r" in names and (fr["fn"] == "main" or "n" in names), (st["id"], i, names)


def test_values_knob_expected_cells():
    lesson = model.load(BYTE)
    if not all(f.get("value") for f in lesson.data["facts"]):
        raise NotRun(f"{lesson.id} not captured yet")
    exp = knob.expected_values(lesson)
    assert exp["-1"]["facts"]["f.vm1.u"] == "4294967295" and exp["-1"]["facts"]["f.vm1.c"] == "255"
    assert exp["321"]["facts"]["f.v321.c"] == "65" and exp["321"]["facts"]["f.v321.hex"] == "0x41"
    rec = {"knob": [{"value": v, "selected": [v], "row": list(e["facts"].items()), "prose": e["claims"]} for v, e in exp.items()]}
    assert knob.check(lesson, rec)[0] == []
    rec["knob"][2]["row"][3] = ("f.vm1.u", "-1")
    assert knob.check(lesson, rec)[0]
