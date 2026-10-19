"""AC-1.6..AC-1.8: the teaching protocols in references/TEACHING.md, driven by fixed learner turns.

- test_no_reveal_before_attempt, test_modes (automatic): the router picks the mode, TEACHING.md has
  its protocol, and ptk/protocol.py accepts a scripted transcript that follows it and rejects each
  scripted break (a reveal, two questions at once, a skipped layer, and so on). Scripted learner
  attempts carry their ground-truth class (`expect_class`); the checker grades the tutor's
  classification against it (or against the question's answer key) instead of trusting the
  tutor's own labels.
- test_explanation_first (automatic): with no practice mode asked for, the checker wants the complete
  explanation first, then optional practice offered in one closing sentence, and no question before it
  (AC-1.6 v1.4). A naming sentence for a misconception beside the one feedback item stays rejected; the
  name goes inside that sentence, as TEACHING.md says.
- test_practice_mode_flow, test_explanation_first_flow, test_modes_live (agent-tests): a real tutor agent, loaded from SKILL.md by
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

FIX = "A case label is only a label, so control runs on into case 3."
PRACTICE_REQUEST = "Let me predict first: how does a switch statement with a missing break fall through? Show me the still after."
EXPLAIN_REQUEST = "Teach me how a switch statement with a missing break falls through, as a still."
PREDICT_GOOD = {"mode": "predict-first", "turns": [
    T(["question"], "Here is the program: n is 2 and case 2 has no break. What does it print?", states_shown=["s0"]),
    S("attempt", "two, then done", expect_class="misconception:m.stops"),
    T(["feedback", "artifact", "consent"],
      f"Not quite. {FIX} Here is the still with every step. Can I note this attempt as evidence?",
      classification="misconception:m.stops", feedback=FIX,
      artifacts=["lessons/switch-fallthrough/build/still/switch-fallthrough-wide-light.png"],
      states_shown=["s0", "s1", "s2", "s3"]),
    S("consent-yes", "yes"),
    T(["summary"], "Noted. Next, try the same switch with n = 1 when you're ready."),
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
    # in a practice mode the learner asked for, the router tells the agent the artifact waits for the attempt;
    # the same topic without a practice request is explanation first, even in a workspace that asks for prediction
    ws = _tmp_ws(PREDICT_WS)
    try:
        r = route.route(PRACTICE_REQUEST, ws)
        plain = route.route(EXPLAIN_REQUEST, ws)
    finally:
        shutil.rmtree(ws)
    assert r["mode"] == "predict-first" and r["first_turn"]["artifact"] == "after-attempt", r
    assert plain["mode"] == "lesson" and plain["first_turn"]["artifact"] == "after-build" and plain["workspace_conflict"], plain
    assert "artifact" in _section("predict-first").lower()
    # the clean transcript passes; each kind of reveal fails
    assert protocol.check_transcript(PREDICT_GOOD, lesson) == []
    nested = _break(QUIZ, lambda t: t["turns"][0].update(quiz={"answer_key": t["turns"][0].pop("answer_key")}))
    assert protocol.check_transcript(nested) == [], "mode fields may sit in a sub-object named after the mode"
    # showing the program in a fenced block is not a reveal; inline prose is
    code = "```c\nputs(\"two\");\nputs(\"three\");\nputs(\"done\");\n```\nWhat does it print?"
    assert protocol.check_transcript(_break(PREDICT_GOOD, lambda t: t["turns"][0].update(text=code)), lesson) == []
    # a ternary in the program and an imperative prediction prompt are good first turns (P2-3)
    ternary = "```c\nint k = n ? 2 : 3;\n```\nWhat does it print?"
    imperative = "Predict the output of the program for n = 2."
    for text in (ternary, imperative):
        assert protocol.check_transcript(_break(PREDICT_GOOD, lambda t: t["turns"][0].update(text=text)), lesson) == [], text
    # ground truth may come from the harness instead of the learner turn, which the tutor never sees
    hidden = _break(PREDICT_GOOD, lambda t: t["turns"][1].pop("expect_class"))
    assert protocol.check_transcript(hidden, lesson, truth=["misconception:m.stops"]) == []
    assert protocol.check_transcript(hidden, lesson, truth=["correct"]), "the harness truth must be enforced"
    breaks = {
        "inline code reveal": lambda t: t["turns"][0].update(text="It prints `two` then `three`. Agree?"),
        "hidden state": lambda t: t["turns"][0].update(states_shown=["s0", "s2"]),
        "states the answer": lambda t: t["turns"][0].update(text="It prints two, three, done. Why do you think?"),
        "artifact before": lambda t: t["turns"][0].update(artifacts=["build/still/x.png"]),
        "first turn": lambda t: t["turns"][0].update(acts=["question", "artifact"]),
        # P1-3 counterexamples from the WP1 review: each passed the old checker
        "three corrections labelled as one": lambda t: t["turns"][2].update(
            feedback_items=1, text=f"Not quite. {FIX} Also, only a break statement ends a case. And the switch "
            "jumped straight to case 2, so case 1 never ran. Here is the still. Can I note this attempt as evidence?"),
        "misconception classified correct": lambda t: t["turns"][2].update(classification="correct"),
        "hint in the opening question": lambda t: t["turns"][0].update(
            text="Hint: a case label does not stop anything, so look for the next break. What does it print?"),
        "correction claim in the opening question": lambda t: t["turns"][0].update(
            text="n is 2, and a case label is only a label. What does the program print?"),
        "partial reveal": lambda t: t["turns"][0].update(
            text="It keeps going into case 3, so three shows up. What is the full output?"),
        "feedback field missing": lambda t: t["turns"][2].pop("feedback"),
        "two-sentence feedback field": lambda t: t["turns"][2].update(
            feedback=f"{FIX} Only break ends a case.", text=f"Not quite. {FIX} Only break ends a case. Can I note it?"),
        "attempt without ground truth": lambda t: t["turns"][1].pop("expect_class"),
    }
    why = {"three corrections labelled as one": "second correction", "misconception classified correct": "ground truth",
           "hint in the opening question": "hint marker", "correction claim in the opening question": "correction claim",
           "partial reveal": "gives away", "feedback field missing": "no `feedback` field",
           "two-sentence feedback field": "one sentence", "attempt without ground truth": "no ground truth"}
    caught = {}
    for name, fn in breaks.items():
        v = protocol.check_transcript(_break(PREDICT_GOOD, fn), lesson)
        assert v, f"the checker missed: {name}"
        assert why.get(name, "") in " | ".join(v), f"{name}: caught for the wrong reason: {v}"
        caught[name] = next((x for x in v if why.get(name, "") in x), v[0])
    return {"hidden": p["hidden_states"], "caught": caught}


# ---------------------------------------------------------------- AC-1.8

QUIZ = {"mode": "quiz", "turns": [
    T(["question"], "Three questions on integer promotion. 1: in char c = 200; on this Mac, what is c?",
      answer_key="-56", question_count=3),
    S("attempt", "-56", expect_class="correct"),
    T(["feedback", "question"], "Right: char is signed here. 2: what type is 'a' + 1 in C?",
      classification="correct", feedback="char is signed here.", answer_key="int"),
    S("attempt", "char", expect_class="partial"),
    T(["feedback", "question"], "Partly: 'a' is already an int in C. 3: what does sizeof('a') give on this Mac?",
      classification="partial", feedback="'a' is already an int in C.", answer_key="4"),
    S("attempt", "4", expect_class="correct"),
    T(["feedback", "consent"], "Right. Can I note these three attempts as evidence?", classification="correct",
      feedback="Right."),
    S("consent-yes", "yes"),
    T(["summary"], "Noted. Score so far 2/3. Weakest: the type of a character constant. Another round?"),
    S("stop", "stop here"),
    T(["close"], "Stopped. Score 2/3. Next: predict sizeof('a') in C++.", reason="learner-stop", score="2/3"),
], "events": [dict(EVIDENCE, after_turn=8, item="integer promotion quiz", result="partial")]}

EXAM = {"mode": "exam-drill", "turns": [
    T(["question"], "GATE drill: 2 MCQs, 1 mark each, 90 s each, -1/3 for a wrong answer. "
      "Q1: which operator has the highest precedence?", format="mcq", marks=1, time_limit_s=90,
      options=["A ++ (postfix)", "B *", "C +", "D ="], answer_key="A"),
    S("attempt", "B", elapsed_s=40, expect_class="misconception:*"),
    T(["feedback", "question"], "Wrong, -1/3: postfix ++ binds tighter than *. Q2: which of these is evaluated first in a = b + c * d?",
      classification="misconception:star-first", feedback="postfix ++ binds tighter than *.", marks_awarded=-0.33,
      elapsed_s=40, format="mcq", options=["A =", "B +", "C *", "D none"], answer_key="C"),
    S("attempt", "C", elapsed_s=25, expect_class="correct"),
    T(["feedback", "consent"], "Right, +1, 25 s of 90. Can I note both attempts as evidence?", classification="correct",
      feedback="Right, +1, 25 s of 90.", marks_awarded=1, elapsed_s=25),
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
        "two hints": lambda t: t["turns"][2].update(
            text="Right: char is signed here. Remember that plain char signedness is implementation-defined. "
                 "2: what type is 'a' + 1 in C?"),
        "partial called correct": lambda t: t["turns"][4].update(classification="correct"),
        "correct answer called wrong (no scripted truth, key decides)": lambda t: (
            t["turns"][1].pop("expect_class"), t["turns"][2].update(classification="partial")),
        "bad score": lambda t: t["turns"][-1].update(score="3/5"),
        "score does not match the classifications": lambda t: t["turns"][-1].update(score="3/3"),
        "closed before the learner stopped": lambda t: t["turns"][8].update(acts=["close"], reason="satisfied"),
    }),
    "exam-drill": ("GATE-style MCQs on operator precedence, timed", EXAM, {
        "no time limit": lambda t: t["turns"][0].pop("time_limit_s"),
        "three options": lambda t: t["turns"][0].update(options=["A", "B", "C"]),
        "no marks in feedback": lambda t: t["turns"][2].pop("marks_awarded"),
        "wrong answer called correct": lambda t: t["turns"][2].update(classification="correct"),
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


PROG = "```c\nswitch (n) {\ncase 1: puts(\"one\");\ncase 2: puts(\"two\");\ncase 3: puts(\"three\"); break;\n}\nputs(\"done\");\n```"
QF1 = "Control enters at case 2, and case 3 is only a label, so it runs on until the break."
QF2 = "The new break ends the switch right after two, so case 3 never runs."
QF3 = "With n = 7 no label matches and there is no default, so only done prints."
# P2-4 counterexamples, shaped like the stored live transcripts: each was rejected by the r16 checker
QUIZ_LIVE = {"mode": "quiz", "turns": [
    T(["question"], f"Three questions on this program.\n\n{PROG}\n\nQuestion 1 of 3: n is 2 and case 2 has no break. "
      "What does it print, line by line?", question_count=3, answer_key="two\nthree\ndone\n"),
    S("attempt", "two, three, done"),
    T(["feedback", "question"], f"Correct. {QF1}\n\nQuestion 2 of 3: now add one line, break; right after puts(\"two\"). "
      "With n still 2, what does the program print?", classification="correct", feedback=QF1, answer_key="two\ndone\n"),
    S("attempt", "only two and done"),
    T(["feedback", "question"], f"Correct. {QF2}\n\nQuestion 3 of 3: go back to the original program and set n to 7. "
      "There is no default label. What does it print now?", classification="correct", feedback=QF2, answer_key="done\n"),
    S("attempt", "two, three, done"),
    T(["feedback", "consent"], f"Not quite. {QF3}\n\nScore: 2/3. Weakest item: a switch with no matching case. "
      "Next step: predict the output for n = 5 before you run it. After that I can run another round if you want one. "
      "Can I note these three attempts as evidence?", classification="misconception:m.nomatch", feedback=QF3),
    S("consent-yes", "yes"),
    T(["summary"], "Noted. Another round?"),
    S("stop", "stop here"),
    T(["close"], "Stopped. Score 2/3.", reason="learner-stop", score="2/3"),
], "events": [dict(EVIDENCE, after_turn=8, item="switch fallthrough quiz", result="misconception:m.nomatch")]}

EF1 = "The fast way: jump to the matching label, then read down to the first break."
EF2 = "The break right after puts(\"two\") ends the switch, so case 3 never runs."
OPTS1 = ["A. two, done", "B. two, three, done", "C. one, two, three, done", "D. two, three, four, done"]
OPTS2 = ["A. two, three, done", "B. one, two, done", "C. two, done", "D. done"]
EXAM_LIVE = {"mode": "exam-drill", "turns": [
    T(["question"], f"GATE drill: 2 MCQs, 1 mark each, 90 s each, -1/3 for a wrong answer.\n\n{PROG}\n\n"
      f"Q1 (1 mark, 90 s): with n = 2, what does it print? {' '.join(OPTS1)}", format="mcq", marks=1,
      time_limit_s=90, options=OPTS1, answer_key={"option": "B", "fact": "f.p1.out", "value": "two\nthree\ndone\n"}),
    S("attempt", "B", elapsed_s=50),
    T(["feedback", "question"], f"Correct, B. +1 mark, 50 s of your 90. {EF1}\n\nQ2 (1 mark, 90 s). Same program, but now "
      f"case 2 has its own break. What does it print? {' '.join(OPTS2)}", classification="correct", feedback=EF1,
      marks_awarded=1, elapsed_s=50, options=OPTS2, answer_key={"option": "C", "value": "two\ndone\n"}),
    S("attempt", "A", elapsed_s=30),
    T(["feedback", "consent"], f"Not quite. The answer is C (two, done). -1/3 mark, 30 s of your 90. {EF2}\n\n"
      "Total: 2/3 of 2 marks, 1 of 2 correct, 50 s and 30 s against 90 s each. Weakest topic: where a break sends control. "
      "Next step: mark the first break below the matching label before you pick. Can I note both attempts as evidence?",
      classification="misconception:ignores-break", feedback=EF2, marks_awarded="-1/3", elapsed_s=30),
    S("consent-yes", "yes"),
    T(["summary"], "Noted. Another question?"),
    S("stop", "done"),
    T(["close"], "Done. Total 2/3 of 2.", reason="learner-stop", total_marks="2/3"),
], "events": [dict(EVIDENCE, after_turn=6, item="switch fallthrough drill", result="misconception:ignores-break")]}


def _set_text(i, text):
    return lambda t: t["turns"][i].update(text=text)


LIVE_BREAKS = {
    "quiz": (QUIZ_LIVE, {
        "two corrections before the next question": (_set_text(2, f"Correct. {QF1} Only a break statement ends a "
            "switch early, never a label.\n\nQuestion 2 of 3: now add break; after puts(\"two\"). What does it print?"),
            "second correction"),
        "a hint inside the next question": (_set_text(2, f"Correct. {QF1}\n\nQuestion 2 of 3: remember that a break "
            "ends the switch at once. With a break after puts(\"two\"), what does it print?"), "hint"),
        "the next question states its own key": (_set_text(2, f"Correct. {QF1}\n\nQuestion 2 of 3: with a break after "
            "puts(\"two\") it prints two and done, right?"), "states its own answer key"),
        "a second correction on the last feedback": (_set_text(6, f"Not quite. {QF3} Also, a switch body is skipped "
            "entirely when no label matches. Score: 2/3. Can I note these three attempts as evidence?"), "second correction"),
        "two next actions": (_set_text(6, f"Not quite. {QF3} Score: 2/3. Next step: predict the output for n = 5. "
            "Next, trace the n = 1 case by hand. Can I note these three attempts as evidence?"), "more than one next action"),
        "a weakest item that re-explains": (_set_text(6, f"Not quite. {QF3} Weakest item: a switch with no matching "
            "case, because with no match and no default the whole body is skipped and only the line after it prints. "
            "Can I note these three attempts as evidence?"), "second correction"),
        "a next action before the last answer": (_set_text(2, f"Correct. {QF1} Next step: predict the output for n = 5 "
            "before you run it.\n\nQuestion 2 of 3: now add break; after puts(\"two\"). What does it print?"),
            "second correction"),
        "a correction on its own line, merged into the consent question": (_set_text(6, f"Not quite. {QF3}\n"
            "Also only a break ends a case early\nCan I note these three attempts as evidence?"), "second correction"),
        "a key line that is not the attempted key": (_set_text(4, f"Correct. {QF2} Key: two, three, done.\n\n"
            "Question 3 of 3: set n to 7. What does it print now?"), "key other than"),
        "a key line carrying an explanation": (_set_text(4, f"Correct. {QF2} The answer is two then done, because "
            "the break ends it.\n\nQuestion 3 of 3: set n to 7. What does it print now?"), "key other than"),
        "an artifact line carrying a reason": (lambda t: t["turns"][6].update(
            acts=["feedback", "artifact", "consent"], artifacts=["build/still/x.png"],
            text=f"Not quite. {QF3} The still shows it, because no label matches. Can I note these three attempts as evidence?"),
            "second correction"),
        "an extra output line called correct": (lambda t: t["turns"][3].update(text="two, three, done"),
            "does not match the answer key"),
        "a missing output line called correct": (lambda t: t["turns"][3].update(text="done"), "does not match the answer key"),
    }),
    "exam-drill": (EXAM_LIVE, {
        "key revealed before the attempt": (_set_text(0, EXAM_LIVE["turns"][0]["text"] + " The answer is B."),
            "states its own answer key"),
        "next question's key revealed in the feedback": (_set_text(2, f"Correct, B. The answer is C. {EF1}\n\nQ2 (1 mark, "
            f"90 s). What does it print? {' '.join(OPTS2)}"), "key other than"),
        "next question's key inside its own block": (_set_text(2, f"Correct, B. {EF1}\n\nQ2 (1 mark, 90 s). C is correct "
            f"here. What does it print? {' '.join(OPTS2)}"), "states its own answer key"),
        "marks line carrying an explanation": (_set_text(2, f"Correct, B. +1 mark, 50 s of your 90, since the label "
            f"never stops anything and the break decides where it ends. {EF1}\n\nQ2 (1 mark, 90 s). What does it print? "
            f"{' '.join(OPTS2)}"), "second correction"),
        "key reveal carrying an explanation": (_set_text(4, f"Not quite. The answer is C (two, done) because the break "
            f"ends the switch at once. {EF2} Can I note both attempts as evidence?"), "second correction"),
        "two corrections in exam feedback": (_set_text(4, f"Not quite. The answer is C (two, done). {EF2} Also, case "
            "labels never stop execution on their own. Can I note both attempts as evidence?"), "second correction"),
        "marks not a number or a fraction": (lambda t: t["turns"][4].update(marks_awarded="2/3 of 2"), "marks_awarded"),
        "two letters for a one-letter key called correct": (lambda t: t["turns"][1].update(text="B and C"),
            "does not match the answer key"),
        "wrong letter called correct": (lambda t: t["turns"][4].update(classification="correct"),
            "does not match the answer key"),
    }),
}


def test_mode_feedback_rules():
    """P2-4: the one-item rule is mode-aware. Quiz and exam-drill turns may hold what their TEACHING.md protocol
    requires (the next question, score, weakest item, one next action, marks, time, the key after the attempt)
    without that counting as a second explanation; each allowance still rejects a smuggled correction.
    Predict-first keeps the strict one-hint rule (AC-1.6)."""
    for mode, (good, breaks) in LIVE_BREAKS.items():
        assert protocol.check_transcript(good) == [], f"{mode}: P2-4 counterexample still rejected: {protocol.check_transcript(good)}"
        for name, (fn, why) in breaks.items():
            v = protocol.check_transcript(_break(good, fn))
            assert v, f"{mode}: the checker missed '{name}'"
            assert why in " | ".join(v), f"{mode}: '{name}' caught for the wrong reason: {v}"
    # the attempted question's key, and a short line introducing the artifact, may sit beside the item
    keyed = _break(QUIZ_LIVE, _set_text(4, f"Correct. {QF2} Key: two, done.\n\nQuestion 3 of 3: go back to the "
        "original program and set n to 7. There is no default label. What does it print now?"))
    assert protocol.check_transcript(keyed) == [], protocol.check_transcript(keyed)
    shown = _break(QUIZ_LIVE, lambda t: t["turns"][6].update(acts=["feedback", "artifact", "consent"],
        artifacts=["build/still/x.png"], text=f"Not quite. {QF3} Score: 2/3. The lesson still shows the same rule on "
        "the first program:\nbuild/still/x.png\nCan I note these three attempts as evidence?"))
    assert protocol.check_transcript(shown) == [], protocol.check_transcript(shown)
    # a summary written as a list passes line by line
    listed = _break(EXAM_LIVE, _set_text(4, f"Not quite. The answer is C (two, done). {EF2}\n\nDrill result:\n"
        "- Marks: 2/3 out of 2 (+1, then -1/3)\n- Accuracy: 1 of 2\n- Time: 50 s on Q1, 30 s on Q2, both under 90 s\n"
        "- Weak spot: where control goes once a break runs\n- Next: trace one switch by hand, untimed\n\n"
        "Can I note both attempts as evidence?"))
    assert protocol.check_transcript(listed) == [], protocol.check_transcript(listed)
    # grading: option keys by letter, output keys by line sequence
    ok = [("B", {"option": "B", "value": "x"}, []), (" (b). ", {"option": "B"}, []), ("Option B", {"option": "B"}, []),
          ("B", "B", ["A x", "B y", "C z", "D w"]), ("A, C", {"option": ["A", "C"]}, []),
          ("only two and done", "two\ndone\n", []), ("two, done", "two\ndone\n", []), ("two then done.", "two\ndone\n", []),
          ("It prints \"two\" and \"done\"", "two\ndone\n", []), ("two\ndone", "two\ndone\n", []), ("-56", "-56", [])]
    bad = [("C", {"option": "B"}, []), ("B and C", {"option": "B"}, []), ("A", {"option": ["A", "C"]}, []),
           ("two, three, done", "two\ndone\n", []), ("done, two", "two\ndone\n", []), ("two", "two\ndone\n", []),
           ("two, done, done", "two\ndone\n", []), ("two, three, done", "done\n", []), ("nope", "B", ["A", "B", "C", "D"])]
    for attempt, key, options in ok:
        assert protocol.answer_matches(attempt, key, options), (attempt, key)
    for attempt, key, options in bad:
        assert not protocol.answer_matches(attempt, key, options), (attempt, key)
    # fractional GATE marks
    for good_mark in (1, 0.5, -0.33, "-1/3", "2/3", "+1", "0"):
        assert protocol.is_mark(good_mark), good_mark
    for bad_mark in ("2/3 of 2", "one", True, None, "1/0"):
        assert not protocol.is_mark(bad_mark), bad_mark
    # a misconception the lesson does not list may get a short new name (TEACHING), never a sentence
    lesson = _lesson()
    renamed = _break(PREDICT_GOOD, lambda t: t["turns"][2].update(classification="misconception:m.default-ignored"))
    assert protocol.check_transcript(renamed, lesson, truth=["misconception:*"]) == []
    assert protocol.check_transcript(renamed, lesson), "the scripted truth names m.stops, so a new name is wrong here"
    long_name = "misconception:thinks-the-next-case-label-stops-the-switch-early"
    v = protocol.check_transcript(_break(PREDICT_GOOD, lambda t: t["turns"][2].update(classification=long_name)),
                                  lesson, truth=["misconception:*"])
    assert any("not a short new name" in x for x in v), v
    # predict-first stays strict: the quiz and exam allowances do not apply to it
    strict = {
        "marks line": f"Not quite. {FIX} +1 mark, 50 s of your 90. Here is the still. Can I note this attempt as evidence?",
        "weakest item": f"Not quite. {FIX} Weakest item: a switch with no matching case. Can I note it?",
    }
    for name, text in strict.items():
        v = protocol.check_transcript(_break(PREDICT_GOOD, _set_text(2, text)), _lesson())
        assert "second correction" in " | ".join(v), f"predict-first accepted a {name}: {v}"
    return {mode: len(breaks) for mode, (_, breaks) in LIVE_BREAKS.items()}


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


STILL = "lessons/switch-fallthrough/build/still/switch-fallthrough-wide-light.png"
OFFER = "Want one practice question on a switch like this?"
EXPLAIN_BODY = ("Here is the program with n = 2. The switch jumps to the label case 2 and prints two. A case label is only "
                "a label, not a stop, so control runs on into case 3 and prints three. The break there ends the switch, "
                "and the line after it prints done. So the output is two, three, done. The still shows each step.")
EXPLAIN_GOOD = {"mode": "lesson", "turns": [
    T(["explanation", "artifact"], f"{EXPLAIN_BODY} {OFFER}", practice_offer=OFFER, artifacts=[STILL],
      states_shown=["s0", "s1", "s2", "s3", "s4"]),
    S("stop", "Thanks, that's clear. That's all for now."),
    T(["close"], "Done. Nothing was practised, so nothing is noted as learned.", reason="learner-stop"),
], "events": []}
PRACTICE_AFTER = {"mode": "lesson", "turns": EXPLAIN_GOOD["turns"][:1] + [
    S("practice-yes", "Sure, one question."),
    T(["question"], "Same program with n = 1. What does it print?", states_shown=["s0"]),
    S("attempt", "one, two, three, done", expect_class="correct"),
    T(["feedback", "consent"], f"Right. {FIX} Can I note this attempt as evidence?", classification="correct", feedback=FIX),
    S("consent-yes", "yes"),
    T(["summary"], "Noted. One attempt observed."),
    S("satisfied", "got it, thanks"),
    T(["close"], "Good. The n = 1 case is observed.", reason="satisfied"),
], "events": [dict(EVIDENCE, after_turn=6, result="correct")]}


def test_explanation_first():
    """AC-1.6 (v1.4): with no practice mode asked for, the complete explanation comes first, then optional practice
    offered in one closing sentence, with no question before the explanation. A question turn comes only after the
    learner takes up the offer. Also: the misconception naming rule in TEACHING.md and the checker agree."""
    lesson = _lesson()
    assert protocol.check_transcript(EXPLAIN_GOOD, lesson) == [], protocol.check_transcript(EXPLAIN_GOOD, lesson)
    assert protocol.check_transcript(PRACTICE_AFTER, lesson) == [], protocol.check_transcript(PRACTICE_AFTER, lesson)
    for mode in ("explain", "full-pack"):
        assert protocol.check_transcript(dict(EXPLAIN_GOOD, mode=mode), lesson) == [], mode
    q = "What do you think the program prints? "
    breaks = {
        "a question first": (lambda t: t["turns"][0].update(acts=["question"], text=q), "first turn must be the explanation"),
        "a question before the explanation": (lambda t: t["turns"][0].update(text=q + t["turns"][0]["text"]),
                                              "question before or inside the explanation"),
        "a prediction prompt before the explanation": (lambda t: t["turns"][0].update(
            text="Predict the output for n = 2 first. " + t["turns"][0]["text"]), "question before or inside the explanation"),
        "no practice offer": (lambda t: (t["turns"][0].pop("practice_offer"),
                                         t["turns"][0].update(text=EXPLAIN_BODY)), "one sentence offering optional practice"),
        "offer not at the close": (lambda t: t["turns"][0].update(text=f"{OFFER} {EXPLAIN_BODY}"), "closing sentence"),
        "two offers": (lambda t: t["turns"][0].update(text=f"{EXPLAIN_BODY} Shall I quiz you? {OFFER}"),
                       "question before or inside the explanation"),
        "an offer that is not about practice": (lambda t: t["turns"][0].update(
            practice_offer="Does that make sense?", text=f"{EXPLAIN_BODY} Does that make sense?"), "offer practice"),
        "an incomplete explanation": (lambda t: t["turns"][0].update(
            text=f"The switch jumps to case 2 and keeps going. The still shows it. {OFFER}"), "never states the answer"),
        "no artifact in a lesson": (lambda t: t["turns"][0].update(acts=["explanation"], artifacts=[]),
                                    "show the built artifact"),
        "a question turn the learner did not ask for": (lambda t: t["turns"].insert(2, T(["question"], "n = 1?")) or
                                                        t["turns"].insert(2, S("other", "ok")), "before the learner asked for practice"),
    }
    caught = {}
    for name, (fn, why) in breaks.items():
        v = protocol.check_transcript(_break(EXPLAIN_GOOD, fn), lesson)
        assert v, f"the checker missed: {name}"
        assert why in " | ".join(v), f"{name}: caught for the wrong reason: {v}"
        caught[name] = next(x for x in v if why in x)
    # the explain section of TEACHING.md says the same thing the checker enforces
    for mode in ("explain", "lesson"):
        sec = _section(mode).lower()
        assert "no question" in sec and "practice" in sec and "one sentence" in sec, mode
    # practice mode: TEACHING.md puts a misconception's name inside the one feedback sentence; the checker rejects
    # a naming sentence of its own (the r18 live failure) and accepts the name inside the item
    named = "You expected the next case label to stop it, but a label is only a label, so control runs on into case 3."
    inside = _break(PREDICT_GOOD, lambda t: t["turns"][2].update(
        feedback=named, text=f"Not quite. {named} Here is the still with every step. Can I note this attempt as evidence?"))
    assert protocol.check_transcript(inside, lesson) == [], protocol.check_transcript(inside, lesson)
    for own in ("You expected the next case label to stop it.", "That's the \"next case label stops it\" idea."):
        apart = _break(PREDICT_GOOD, lambda t: t["turns"][2].update(
            text=f"Not quite. {own} {FIX} Here is the still with every step. Can I note this attempt as evidence?"))
        v = protocol.check_transcript(apart, lesson)
        assert any("second correction" in x and "inside the feedback sentence" in x for x in v), (own, v)
    sec = _section("predict-first").lower() + TEACHING.read_text().lower()
    assert "same sentence" in sec and "never in a sentence of its own" in sec
    return {"breaks_caught": len(caught)}


# ---------------------------------------------------------------- agent-mediated (AC-1.6)

SCENARIOS = {
    "explain-first": {
        "request": EXPLAIN_REQUEST, "workspace": PREDICT_WS, "mode": "lesson", "lesson": True,
        "learner": [S("stop", "Thanks, that's clear. That's all for now.")]},
    "practice-predict": {
        "request": PRACTICE_REQUEST, "workspace": {}, "mode": "predict-first", "lesson": True,
        "learner": [S("attempt", "It prints two and then done. The next case label stops it.",
                      expect_class="misconception:m.stops"),
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

Tutor turn fields (JSON, all at the top level of the turn object):
- role "tutor"; acts: any of "explanation", "question", "feedback", "artifact", "consent", "answer", "layer", "close";
- text: exactly what you say to the learner;
- classification ("correct", "partial", "misconception:<id>", "skipped", "timeout") and feedback (the
  one hint or correction, one sentence of at most 40 words, copied verbatim from text) on any turn with "feedback". The
  rest of a feedback turn's text may hold only a short verdict, the artifact, a consent question or
  the next question, plus the short lines the mode's protocol in TEACHING.md names;
- artifacts (file paths you show) and states_shown (trace state ids you show);
- explanation turn (act "explanation"): practice_offer, the one closing sentence that offers optional
  practice, copied verbatim from the end of text;
- quiz: answer_key (private, never in text; the exact answer: output lines, a value or an option letter) on
  each question, question_count on the first, score "k/n" on close;
- exam-drill: format ("mcq", "msq", "nat"), marks, time_limit_s on the first turn; options (4) and
  answer_key on each question; marks_awarded and elapsed_s on each feedback; total_marks on close (marks
  as a number or a fraction string like "-1/3");
- qa-expand: the first turn has acts exactly ["answer"], layer 1 and layers_offered; each deeper layer opened on
  request has the act "layer", its layer number and layer_name;
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
        # the tutor reads this file, so the learner's ground-truth class stays in the script
        t["turns"].append({k: v for k, v in sc["learner"][said].items() if k != "expect_class"})
        (job / "transcript.json").write_text(json.dumps(t, indent=1))
        return f"learner turn {said} appended; tutor turn needed: {job / 'JOB.md'}"
    assert t["mode"] == sc["mode"], f"{sid}: tutor used mode {t['mode']!r}, route says {sc['mode']!r}"
    truth = [x.get("expect_class") for x in sc["learner"] if x["kind"] == "attempt"]
    v = protocol.check_transcript(t, _lesson() if sc["lesson"] else None, truth=truth)
    assert not v, f"{sid}: protocol violations: {v}"
    return None


def _run_agent(sids):
    pending = {sid: msg for sid in sids if (msg := _step(sid))}
    if pending:
        raise AgentPending(json.dumps(pending))
    return {sid: json.loads((JOBS / sid / "transcript.json").read_text())["turns"].__len__() for sid in sids}


def test_practice_mode_flow():
    """AC-1.6 (v1.4), practice mode the learner asked for: ask one question and end the turn; classify;
    one feedback item; show the artifact; record one evidence event with consent; stop by the stop rule."""
    return _run_agent(["practice-predict"])


test_practice_mode_flow.agent = True


def test_explanation_first_flow():
    """AC-1.6 (v1.4), no practice mode asked for, in a workspace whose AGENTS.md asks for prediction first:
    the complete explanation with the artifact first, then optional practice in one closing sentence."""
    return _run_agent(["explain-first"])


test_explanation_first_flow.agent = True


def test_modes_live():
    """AC-1.8 with a real tutor: quiz, exam-drill and qa-expand transcripts follow their protocols."""
    return _run_agent(["quiz", "exam-drill", "qa-expand"])


test_modes_live.agent = True
