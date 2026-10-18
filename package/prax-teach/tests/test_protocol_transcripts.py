"""AC-1.6..AC-1.8: the teaching protocols in references/TEACHING.md, driven by fixed learner turns.

- test_no_reveal_before_attempt, test_modes (automatic): the router picks the mode, TEACHING.md has
  its protocol, and ptk/protocol.py accepts a scripted transcript that follows it and rejects each
  scripted break (a reveal, two questions at once, a skipped layer, and so on).
- test_predict_first_flow, test_modes_live (agent-tests): a real tutor agent, loaded from SKILL.md by
  direct path, plays the tutor one turn at a time against fixed learner turns it can't see ahead
  of time. Each run appends the next learner turn and stops at claims-pending (exit 4) until the
  tutor has answered; when the script is used up, the whole transcript must pass the protocol.
"""
import copy
import hashlib
import json
import shutil

from _util import SLICE, ptk_cmd
from selftest_support import AgentPending
from ptk import host, protocol, route

TEACHING = host.PKG / "references" / "TEACHING.md"
JOBS = host.state_path("agent-jobs", "protocol")
PREDICT_WS = {"AGENTS.md": "# C study\n\n## Teaching\n\n- Ask one bounded prediction and wait for the attempt.\n"
                           "- After two unsuccessful attempts, teach directly from a different angle.\n"}


def _lesson():
    return json.loads((SLICE / "lesson.json").read_text())


def _section(mode):
    text = TEACHING.read_text()
    assert f"\n## {mode}\n" in text, f"TEACHING.md has no '## {mode}' protocol"
    return text.split(f"\n## {mode}\n", 1)[1].split("\n## ", 1)[0]


def _tmp_ws(files):
    d = host.make_tmp("proto-ws-")
    for name, text in files.items():
        (d / name).write_text(text)
    return d


def T(acts, text, **kw):
    return {"role": "tutor", "acts": acts, "text": text, **kw}


def S(kind, text, **kw):
    return {"role": "learner", "kind": kind, "text": text, **kw}


EVIDENCE = {"kind": "evidence", "item": "switch fallthrough output", "result": "misconception:m.stops",
            "gap": "treats a case label as a stop", "next_action": "predict the same switch with n = 1",
            "consent": True}

PREDICT_GOOD = {"mode": "predict-first", "turns": [
    T(["question"], "Here is the program: n is 2 and case 2 has no break. What does it print?", states_shown=["s0"]),
    S("attempt", "two, then done"),
    T(["feedback", "artifact", "consent"],
      "Not quite: that's the 'a case label stops execution' idea. A label is only a label, so control runs "
      "on into case 3. Here is the still with every step. Can I note this attempt as evidence?",
      classification="misconception:m.stops", feedback_items=1,
      artifacts=["lessons/switch-fallthrough/build/still/switch-fallthrough-wide-light.png"],
      states_shown=["s0", "s1", "s2", "s3"]),
    S("consent-yes", "yes"),
    T(["feedback"], "Noted. Next, try the same switch with n = 1 when you're ready.", classification="misconception:m.stops",
      feedback_items=1),
    S("satisfied", "got it, that's enough"),
    T(["close"], "Good. One attempt observed; the n = 1 variation is the next check.", reason="satisfied"),
], "events": [dict(EVIDENCE, after_turn=4)]}


def _break(t, fn):
    t = copy.deepcopy(t)
    fn(t)
    return t


# ---------------------------------------------------------------- AC-1.7

def test_no_reveal_before_attempt():
    """AC-1.7: states and text that would reveal an open question's answer stay hidden until the attempt."""
    lesson = _lesson()
    plan = protocol.reveal_plan(lesson)
    assert len(plan) == 1 and plan[0]["answer_fact"] == "f.p1.out", plan
    p = plan[0]
    assert p["visible_states"] == ["s0"], p          # the setup state only
    assert set(p["hidden_states"]) == {"s1", "s2", "s3", "s4"}, p
    assert not p["problems"]
    # a lesson whose question opens on an answering state is flagged
    bad = copy.deepcopy(lesson)
    next(s for s in bad["storyboard"] if s.get("question"))["state"] = "s3"
    assert protocol.reveal_plan(bad)[0]["problems"]
    # the router tells the agent the artifact waits for the attempt
    ws = _tmp_ws(PREDICT_WS)
    try:
        r = route.route("Teach me how a switch statement with a missing break falls through, as a still.", ws)
    finally:
        shutil.rmtree(ws)
    assert r["mode"] == "predict-first" and r["first_turn"]["artifact"] == "after-attempt", r
    assert "artifact" in _section("predict-first").lower()
    # the clean transcript passes; each kind of reveal fails
    assert protocol.check_transcript(PREDICT_GOOD, lesson) == []
    breaks = {
        "hidden state": lambda t: t["turns"][0].update(states_shown=["s0", "s2"]),
        "states the answer": lambda t: t["turns"][0].update(text="It prints two, three, done. Why do you think?"),
        "artifact before": lambda t: t["turns"][0].update(artifacts=["build/still/x.png"]),
        "first turn": lambda t: t["turns"][0].update(acts=["question", "artifact"]),
    }
    caught = {}
    for name, fn in breaks.items():
        v = protocol.check_transcript(_break(PREDICT_GOOD, fn), lesson)
        assert v, f"the checker missed: {name}"
        caught[name] = v[0]
    return {"hidden": p["hidden_states"], "caught": caught}


# ---------------------------------------------------------------- AC-1.8

QUIZ = {"mode": "quiz", "turns": [
    T(["question"], "Three questions on integer promotion. 1: in char c = 200; on this Mac, what is c?",
      answer_key="-56", question_count=3),
    S("attempt", "-56"),
    T(["feedback", "question"], "Right: char is signed here. 2: what type is 'a' + 1 in C?",
      classification="correct", feedback_items=1, answer_key="int"),
    S("attempt", "char"),
    T(["feedback", "question"], "Partly: 'a' is already an int in C. 3: what does sizeof('a') give on this Mac?",
      classification="partial", feedback_items=1, answer_key="4"),
    S("attempt", "4"),
    T(["feedback", "consent"], "Right. Can I note these three attempts as evidence?", classification="correct",
      feedback_items=1),
    S("consent-yes", "yes"),
    T(["summary"], "Noted. Score so far 2/3. Weakest: the type of a character constant. Another round?"),
    S("stop", "stop here"),
    T(["close"], "Stopped. Score 2/3. Next: predict sizeof('a') in C++.", reason="learner-stop", score="2/3"),
], "events": [dict(EVIDENCE, after_turn=8, item="integer promotion quiz", result="partial")]}

EXAM = {"mode": "exam-drill", "turns": [
    T(["question"], "GATE drill: 2 MCQs, 1 mark each, 90 s each, -1/3 for a wrong answer. "
      "Q1: which operator has the highest precedence?", format="mcq", marks=1, time_limit_s=90,
      options=["A ++ (postfix)", "B *", "C +", "D ="], answer_key="A"),
    S("attempt", "B", elapsed_s=40),
    T(["feedback", "question"], "Wrong, -1/3: postfix ++ binds tighter than *. Q2: which of these is evaluated first in a = b + c * d?",
      classification="partial", feedback_items=1, marks_awarded=-0.33, elapsed_s=40,
      format="mcq", options=["A =", "B +", "C *", "D none"], answer_key="C"),
    S("attempt", "C", elapsed_s=25),
    T(["feedback", "consent"], "Right, +1, 25 s of 90. Can I note both attempts as evidence?", classification="correct",
      feedback_items=1, marks_awarded=1, elapsed_s=25),
    S("consent-yes", "yes"),
    T(["summary"], "Noted. 0.67 of 2 so far. Weakest: postfix precedence. Another question?"),
    S("stop", "done"),
    T(["close"], "Done. Total 0.67 of 2.", reason="learner-stop", total_marks=0.67),
], "events": [dict(EVIDENCE, after_turn=6, item="operator precedence drill", result="partial")]}

QA = {"mode": "qa-expand", "turns": [
    T(["answer"], "An array name in most expressions converts to a pointer to its first element. "
      "Layers you can open: why, example, edge case, standard.", layer=1,
      layers_offered=["why", "example", "edge case", "standard"]),
    S("expand", "example please", layer_name="example"),
    T(["layer"], "int a[4]; int *p = a; now p points at a[0].", layer=2, layer_name="example"),
    S("expand", "edge case", layer_name="edge case"),
    T(["layer"], "sizeof a is the whole array, because sizeof is one of the exceptions.", layer=3,
      layer_name="edge case"),
    S("stop", "thanks, stop"),
    T(["close"], "Stopped. Still closed: why, standard.", reason="learner-stop"),
], "events": []}

MODE_CASES = {
    "quiz": ("Quiz me on C integer promotion", QUIZ, {
        "two questions in one turn": lambda t: t["turns"][0].update(text="1: what is c? 2: and what is 'a' + 1?"),
        "answer in the question": lambda t: t["turns"][0].update(text="1: c is -56 here, right?"),
        "no feedback": lambda t: t["turns"][2].update(acts=["question"]),
        "two hints": lambda t: t["turns"][2].update(feedback_items=2),
        "bad score": lambda t: t["turns"][-1].update(score="3/5"),
    }),
    "exam-drill": ("GATE-style MCQs on operator precedence, timed", EXAM, {
        "no time limit": lambda t: t["turns"][0].pop("time_limit_s"),
        "three options": lambda t: t["turns"][0].update(options=["A", "B", "C"]),
        "no marks in feedback": lambda t: t["turns"][2].pop("marks_awarded"),
        "no total": lambda t: t["turns"][-1].pop("total_marks"),
    }),
    "qa-expand": ("Let me ask you questions about arrays and expand the answer layer by layer", QA, {
        "skipped layer": lambda t: t["turns"][2].update(layer=3),
        "wrong layer": lambda t: t["turns"][4].update(layer_name="standard"),
        "unasked layer": lambda t: t["turns"].insert(5, T(["layer"], "Also, the standard says...", layer=4,
                                                          layer_name="standard")),
        "no layers offered": lambda t: t["turns"][0].pop("layers_offered"),
    }),
}


def test_modes():
    """AC-1.8: quiz, exam-drill and qa-expand each have a TEACHING.md protocol and a transcript test."""
    ws = host.make_tmp("proto-modes-")
    out = {}
    try:
        for mode, (request, good, breaks) in MODE_CASES.items():
            assert route.route(request, ws)["mode"] == mode, request
            assert len(_section(mode)) > 200, f"TEACHING.md#{mode} is too thin"
            v = protocol.check_transcript(good)
            assert v == [], f"{mode} scripted transcript should pass: {v}"
            for name, fn in breaks.items():
                assert protocol.check_transcript(_break(good, fn)), f"{mode}: the checker missed '{name}'"
            out[mode] = {"breaks_caught": len(breaks)}
    finally:
        shutil.rmtree(ws)
    for mode in ("predict-first", "socratic", "quick", "explain", "lesson"):
        _section(mode)
    stop = TEACHING.read_text().lower()
    assert "stop rule" in stop and "satisfied" in stop and "evidence" in stop
    return out


# ---------------------------------------------------------------- agent-mediated (AC-1.6)

SCENARIOS = {
    "predict-first": {
        "request": "Teach me how a switch statement with a missing break falls through, as a still.",
        "workspace": PREDICT_WS, "mode": "predict-first", "lesson": True,
        "learner": [S("attempt", "It prints two and then done. The next case label stops it."),
                    S("consent-yes", "Yes, you can note it."),
                    S("satisfied", "Got it, thanks. That's enough for today.")]},
    "quiz": {
        "request": "Quiz me on how a switch with a missing break behaves, three questions.",
        "workspace": {}, "mode": "quiz", "lesson": True,
        "learner": [S("attempt", "two, three, done"), S("attempt", "only two and done"), S("attempt", "the break on line 12"),
                    S("consent-no", "No, don't record anything."), S("stop", "Stop here.")]},
    "exam-drill": {
        "request": "Give me a timed GATE-style drill: 2 MCQs on switch fallthrough.",
        "workspace": {}, "mode": "exam-drill", "lesson": True,
        "learner": [S("attempt", "B", elapsed_s=50), S("attempt", "A", elapsed_s=30),
                    S("consent-yes", "yes"), S("stop", "done")]},
    "qa-expand": {
        "request": "Let me ask you about switch fallthrough and expand the answer layer by layer.",
        "workspace": {}, "mode": "qa-expand", "lesson": True,
        "learner": [S("expand", "Open the example layer.", layer_name="example"), S("stop", "Thanks, stop.")]},
}

TUTOR_JOB = """# Tutor job: {sid}

You are the tutor in a scripted teaching transcript. Write only inside this job directory.

1. Load the skill by direct path: {skill}. `ptk` is {ptk}. Follow SKILL.md exactly.
2. The learner's workspace is {ws}. The learner's request was:
   "{request}"
3. {lesson_line}
4. Read {transcript}. Append exactly ONE tutor turn: the opening turn if `turns` is empty, otherwise
   your reply to the last learner turn. Never write learner turns. Set `mode` to the mode `ptk route`
   gave you. If the protocol records an evidence event now, append it to `events`
   with `after_turn` = the index your turn will have. Save the file and stop.
5. Learner turns arrive one at a time from a script you cannot see. If a learner `layer_name`, `elapsed_s`
   or `kind` field is present, it is part of what the learner said.

Tutor turn fields (JSON):
- role "tutor"; acts: any of "question", "feedback", "artifact", "consent", "answer", "layer", "close";
- text: exactly what you say to the learner;
- classification ("correct", "partial", "misconception:<id>", "skipped", "timeout") and feedback_items
  (the number of hint or feedback items) on any turn with "feedback";
- artifacts (file paths you show) and states_shown (trace state ids you show);
- quiz: answer_key (private, never in text) on each question, question_count on the first, score "k/n" on close;
- exam-drill: format ("mcq", "msq", "nat"), marks, time_limit_s on the first turn; options (4) and
  answer_key on each question; marks_awarded and elapsed_s on each feedback; total_marks on close;
- qa-expand: layer (1 for the first answer) and layers_offered on the first turn; layer and layer_name on each layer;
- close: reason "satisfied" or "learner-stop".
"""


def _digest():
    h = hashlib.sha256()
    for p in (host.PKG / "SKILL.md", TEACHING, host.PKG / "ptk" / "route_rules.json"):
        h.update(p.read_bytes())
    return h.hexdigest()


def _start(sid, sc, job):
    shutil.rmtree(job, ignore_errors=True)
    ws = job / "workspace"
    ws.mkdir(parents=True)
    for name, text in sc["workspace"].items():
        (ws / name).write_text(text)
    transcript = job / "transcript.json"
    transcript.write_text(json.dumps({"mode": None, "turns": [], "events": []}, indent=1))
    lesson_line = (f"The lesson for this topic is already built at {SLICE}: use its lesson.json (question, "
                   f"facts, misconceptions, trace) and show {SLICE / 'build' / 'still'}/*.png as the artifact. "
                   "Do not rebuild it.") if sc["lesson"] else "No lesson model is needed."
    (job / "JOB.md").write_text(TUTOR_JOB.format(sid=sid, skill=host.PKG / "SKILL.md", ptk=ptk_cmd()[0], ws=ws,
                                                 request=sc["request"], lesson_line=lesson_line,
                                                 transcript=transcript))
    (job / "job.json").write_text(json.dumps({"scenario": sid, "digest": _digest()}))


def _step(sid):
    """Advance one scenario: start it, feed the next learner turn, or validate the finished transcript."""
    sc, job = SCENARIOS[sid], JOBS / sid
    meta = job / "job.json"
    if not meta.exists() or json.loads(meta.read_text())["digest"] != _digest():
        _start(sid, sc, job)
        return f"tutor turn 0 needed: {job / 'JOB.md'}"
    t = json.loads((job / "transcript.json").read_text())
    if not t["turns"] or t["turns"][-1]["role"] != "tutor":
        return f"waiting for the tutor's turn: {job / 'JOB.md'}"
    said = sum(x["role"] == "learner" for x in t["turns"])
    if said < len(sc["learner"]):
        t["turns"].append(sc["learner"][said])
        (job / "transcript.json").write_text(json.dumps(t, indent=1))
        return f"learner turn {said} appended; tutor turn needed: {job / 'JOB.md'}"
    assert t["mode"] == sc["mode"], f"{sid}: tutor used mode {t['mode']!r}, route says {sc['mode']!r}"
    v = protocol.check_transcript(t, _lesson() if sc["lesson"] else None)
    assert not v, f"{sid}: protocol violations: {v}"
    return None


def _run_agent(sids):
    pending = {sid: msg for sid in sids if (msg := _step(sid))}
    if pending:
        raise AgentPending(json.dumps(pending))
    return {sid: json.loads((JOBS / sid / "transcript.json").read_text())["turns"].__len__() for sid in sids}


def test_predict_first_flow():
    """AC-1.6: ask one question and end the turn; classify; one feedback item; show the artifact;
    record one evidence event with consent; stop by the stop rule."""
    return _run_agent(["predict-first"])


test_predict_first_flow.agent = True


def test_modes_live():
    """AC-1.8 with a real tutor: quiz, exam-drill and qa-expand transcripts follow their protocols."""
    return _run_agent(["quiz", "exam-drill", "qa-expand"])


test_modes_live.agent = True
