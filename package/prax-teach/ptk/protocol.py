"""The teaching protocols of references/TEACHING.md, as checks a transcript must pass (AC-1.6..1.8).

Two parts:
- `reveal_plan(lesson)`: for each open storyboard question, which trace states and facts would give
  the answer away and must stay hidden until the learner attempts (AC-1.7, T3).
- `check_transcript(transcript, lesson=None)`: every protocol rule that can be checked from a
  structured transcript. It returns a list of violations; an empty list means the transcript
  follows the protocol for its mode.

Transcript shape (written by a tutor agent, or scripted in tests):
    {"mode": "predict-first|socratic|quiz|exam-drill|qa-expand",
     "turns": [{"role": "tutor", "acts": ["question"|"feedback"|"artifact"|"consent"|"answer"|"layer"|"close"],
                "text": "...", "classification": "correct|partial|misconception:<id>|skipped|timeout",
                "feedback_items": 1, "artifacts": [...], "states_shown": [...], ...mode fields},
               {"role": "learner", "kind": "attempt|consent-yes|consent-no|expand|satisfied|stop|other",
                "text": "..."}],
     "events": [{"kind": "evidence", "after_turn": 3, "item": "...", "result": "...", "gap": "...",
                 "next_action": "...", "consent": true}]}
"""
import re

CLASSES = re.compile(r"^(?:correct|partial|skipped|timeout|misconception:[\w.\-]+)$")
EXAM_FORMATS = {"mcq", "msq", "nat"}
CODE = re.compile(r"```.*?```", re.S)


# ---------------------------------------------------------------- reveal plan (AC-1.7)

def _lines(value):
    return [ln.strip() for ln in str(value).splitlines() if ln.strip()]


def _related(facts, answer_id):
    answer = set(_lines(facts[answer_id].get("value", "")))
    return {fid for fid, f in facts.items() if fid == answer_id or set(_lines(f.get("value", ""))) & answer}


def _hidden_states(trace, related, program):
    hidden, closed = [], set()
    for st in trace:
        prog = st.get("state", {}).get("program")
        touches = set(st.get("reveals", [])) | set(st.get("state", {}).get("output", []))
        if touches & related or prog in closed:
            hidden.append(st["id"])
            closed |= {prog} & {program}
    return hidden


def reveal_plan(lesson):
    """For each storyboard question: the answer, and the trace states to hide until the attempt."""
    facts = {f["id"]: f for f in lesson.get("facts", [])}
    trace = lesson.get("trace", [])
    plans = []
    for scene in (s for s in lesson.get("storyboard", []) if s.get("question")):
        q = scene["question"]
        related = _related(facts, q["answer_fact"])
        hidden = _hidden_states(trace, related, facts[q["answer_fact"]].get("program"))
        plans.append({"scene": scene["id"], "prompt": q["prompt"], "answer_fact": q["answer_fact"],
                      "answer_lines": _lines(facts[q["answer_fact"]].get("value", "")),
                      "related_facts": sorted(related), "hidden_states": hidden,
                      "visible_states": [s["id"] for s in trace if s["id"] not in hidden],
                      "problems": [f"question scene {scene['id']} opens on state {scene['state']}, which reveals the answer"]
                      if scene.get("state") in hidden else []})
    return plans


def leaks(text, answer_lines):
    """True when the prose states the answer: at least two of its lines in order (or the only line).
    Fenced code blocks (the program itself) are skipped; inline code is not."""
    need = min(2, len(answer_lines))
    prose = CODE.sub(" ", str(text))  # showing the program is not stating its output
    low = " ".join(prose.lower().split())
    pos = hits = 0
    for line in answer_lines:
        m = re.compile(r"(?<!\w)" + re.escape(line.lower()) + r"(?!\w)").search(low, pos)
        hits, pos = (hits + 1, m.end()) if m else (hits, pos)
    return need > 0 and hits >= need


# ---------------------------------------------------------------- transcript checks

def _tutor(t):
    return [(i, x) for i, x in enumerate(t["turns"]) if x["role"] == "tutor"]


def _learner(t, kind):
    return [i for i, x in enumerate(t["turns"]) if x["role"] == "learner" and x.get("kind") == kind]


def check_common(t, lesson=None):
    v = []
    turns = t["turns"]
    if not turns or turns[0]["role"] != "tutor":
        v.append("the transcript must open with the tutor's first turn")
    v += [f"turn {i}: two tutor turns in a row (the turn did not end)"
          for i in range(1, len(turns)) if turns[i]["role"] == turns[i - 1]["role"] == "tutor"]
    v += [f"turn {i}: a question turn must hold exactly one question mark, found {x.get('text', '').count('?')}"
          for i, x in _tutor(t) if "question" in x.get("acts", []) and x.get("text", "").count("?") != 1]
    v += [f"turn {i}: feedback needs a classification (correct, partial or misconception:<id>)"
          for i, x in _tutor(t) if "feedback" in x.get("acts", []) and not CLASSES.match(str(x.get("classification")))]
    v += [f"turn {i}: exactly one hint or feedback item, found {x.get('feedback_items')}"
          for i, x in _tutor(t) if "feedback" in x.get("acts", []) and x.get("feedback_items") != 1]
    known = {m["id"] for m in (lesson or {}).get("misconceptions", [])}
    v += [f"turn {i}: unknown misconception {x['classification']!r} (lesson has {sorted(known)})"
          for i, x in _tutor(t) if lesson and str(x.get("classification", "")).startswith("misconception:")
          and x["classification"].split(":", 1)[1] not in known]
    return v + check_evidence(t) + check_stop(t)


def check_evidence(t):
    events = [e for e in t.get("events", []) if e.get("kind") == "evidence"]
    asked = [i for i, x in _tutor(t) if "consent" in x.get("acts", [])]
    yes, no = _learner(t, "consent-yes"), _learner(t, "consent-no")
    v = [f"evidence event {e} lacks consent or a field" for e in events
         if e.get("consent") is not True or not all(e.get(k) for k in ("item", "result", "gap", "next_action"))]
    v += ["evidence recorded without asking consent first" for e in events
          if not any(a < e.get("after_turn", -1) for a in asked)]
    v += ["evidence recorded before the learner said yes" for e in events
          if not any(y <= e.get("after_turn", -1) for y in yes)]
    v += ["evidence recorded after the learner declined" for _ in events[:1] if no and not yes]
    v += ["the learner consented but no evidence event was recorded" for _ in yes[:1] if not events]
    return v


def check_stop(t):
    """Stop rule: every close needs, before it, satisfaction plus an observed attempt, or an explicit stop;
    and the session ends on a close."""
    learner = lambda kind, before: any(i < before for i in _learner(t, kind))
    ok = {"satisfied": lambda i: learner("satisfied", i) and learner("attempt", i),
          "learner-stop": lambda i: learner("stop", i)}
    closes = [(i, x.get("reason")) for i, x in _tutor(t) if "close" in x.get("acts", [])]
    v = [f"turn {i}: stop rule: closed with reason {r!r} without satisfaction plus an observed attempt, "
         "or an explicit stop, before it" for i, r in closes if not ok.get(r, lambda _: False)(i)]
    last = t["turns"][-1] if t["turns"] else {}
    return v + ([] if "close" in last.get("acts", []) else ["the session must end on the tutor's close turn"])


def _before_first_attempt(t):
    first = (_learner(t, "attempt") or [len(t["turns"])])[0]
    return [(i, x) for i, x in _tutor(t) if i < first], first


def check_predict_first(t, lesson=None):
    plans = reveal_plan(lesson) if lesson else []
    plan = plans[0] if plans else {}
    hidden, answer = set(plan.get("hidden_states", [])), plan.get("answer_lines", [])
    before, first = _before_first_attempt(t)
    t0 = t["turns"][0] if t["turns"] else {}
    v = [] if t0.get("acts") == ["question"] else [f"first turn must be one question only, got acts {t0.get('acts')}"]
    v += [f"turn {i}: an artifact before the attempt: {x['artifacts']}" for i, x in before if x.get("artifacts")]
    v += [f"turn {i}: shows hidden states {sorted(set(x.get('states_shown', [])) & hidden)} before the attempt"
          for i, x in before if set(x.get("states_shown", [])) & hidden]
    v += [f"turn {i}: states the answer before the attempt" for i, x in before if leaks(x.get("text", ""), answer)]
    after = [(i, x) for i, x in _tutor(t) if i > first]
    v += [] if after and "feedback" in after[0][1].get("acts", []) else ["the turn after the attempt must give feedback"]
    v += [] if any(x.get("artifacts") for _, x in after) else ["no artifact was shown after the attempt"]
    return v


def check_quiz(t, lesson=None):
    qs = [(i, x) for i, x in _tutor(t) if "question" in x.get("acts", [])]
    v = [f"turn {i}: question states its own answer key" for i, x in qs
         if x.get("answer_key") is None or leaks(x.get("text", ""), [str(x.get("answer_key"))])]
    v += _answered_each(t, qs)
    close = [x for _, x in _tutor(t) if "close" in x.get("acts", [])]
    score = str(close[-1].get("score", "")) if close else ""
    v += [] if re.fullmatch(rf"\d+/{len(qs)}", score) else [f"close must give a score k/{len(qs)}, got {score!r}"]
    return v


def _answered_each(t, qs):
    turns = t["turns"]
    v = []
    for i, _ in qs:
        nxt = turns[i + 1] if i + 1 < len(turns) else {}
        fb = turns[i + 2] if i + 2 < len(turns) else {}
        v += [] if nxt.get("role") == "learner" else [f"turn {i}: the question was not followed by the learner's turn"]
        v += [] if "feedback" in fb.get("acts", []) or nxt.get("kind") == "stop" else [f"turn {i}: no feedback after the answer"]
    return v


def check_exam_drill(t, lesson=None):
    qs = [(i, x) for i, x in _tutor(t) if "question" in x.get("acts", [])]
    t0 = t["turns"][0] if t["turns"] else {}
    v = [] if t0.get("format") in EXAM_FORMATS and (t0.get("time_limit_s") or 0) > 0 and (t0.get("marks") or 0) > 0 \
        else ["first turn must state the format (mcq, msq or nat), the marks and the time limit"]
    v += [f"turn {i}: MCQ/MSQ needs four options A-D" for i, x in qs
          if x.get("format", t0.get("format")) in ("mcq", "msq") and len(x.get("options", [])) != 4]
    v += [f"turn {i}: NAT question states its key" for i, x in qs
          if x.get("format", t0.get("format")) == "nat" and leaks(x.get("text", ""), [str(x.get("answer_key"))])]
    fbs = [x for _, x in _tutor(t) if "feedback" in x.get("acts", [])]
    v += ["exam feedback must give marks_awarded and elapsed_s" for x in fbs
          if not isinstance(x.get("marks_awarded"), (int, float)) or not isinstance(x.get("elapsed_s"), (int, float))]
    v += _answered_each(t, qs)
    close = [x for _, x in _tutor(t) if "close" in x.get("acts", [])]
    v += [] if close and isinstance(close[-1].get("total_marks"), (int, float)) else ["close must give total_marks"]
    return v


def check_qa_expand(t, lesson=None):
    turns = t["turns"]
    t0 = turns[0] if turns else {}
    v = [] if t0.get("acts") == ["answer"] and t0.get("layer") == 1 and t0.get("layers_offered") \
        else ["first turn must be the layer-1 answer with the deeper layers named"]
    offered, layer = list(t0.get("layers_offered", [])), 1
    for i in _learner(t, "expand"):
        reply = turns[i + 1] if i + 1 < len(turns) else {}
        want = turns[i].get("layer_name")
        v += [] if want in offered else [f"turn {i}: asked for a layer that was not offered: {want!r}"]
        v += [] if "layer" in reply.get("acts", []) and reply.get("layer") == layer + 1 \
            and reply.get("layer_name") == want else [f"turn {i + 1}: must open exactly the requested layer next"]
        layer += 1
    opened = sum("layer" in x.get("acts", []) for _, x in _tutor(t))
    v += [] if opened == len(_learner(t, "expand")) else [f"opened {opened} layers for {len(_learner(t, 'expand'))} requests"]
    return v


MODE_CHECKS = {"predict-first": check_predict_first, "socratic": lambda t, lesson=None: [],
               "quiz": check_quiz, "exam-drill": check_exam_drill, "qa-expand": check_qa_expand}


def check_transcript(t, lesson=None):
    """All violations of the protocol for t['mode']; [] means it follows the protocol."""
    mode_check = MODE_CHECKS.get(t.get("mode"))
    if mode_check is None:
        return [f"no protocol for mode {t.get('mode')!r}"]
    t = flatten(t)
    return mode_check(t, lesson) + check_common(t, lesson)


def flatten(t):
    """Mode fields may sit at the top of a turn or in a sub-object named after the mode
    ({"quiz": {"answer_key": ...}}); the checks read them from the top."""
    mode = t.get("mode")
    turns = [{**x, **(x.get(mode) if isinstance(x.get(mode), dict) else {})} for x in t["turns"]]
    return {**t, "turns": turns}
