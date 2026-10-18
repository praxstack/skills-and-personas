"""The teaching protocols of references/TEACHING.md, as checks a transcript must pass (AC-1.6..1.8).

Two parts:
- `reveal_plan(lesson)`: for each open storyboard question, which trace states and facts would give
  the answer away and must stay hidden until the learner attempts (AC-1.7, T3).
- `check_transcript(transcript, lesson=None)`: every protocol rule that can be checked from a
  structured transcript. It returns a list of violations; an empty list means the transcript
  follows the protocol for its mode.

The checker does not take the tutor's word for the two judgement items of AC-1.6:
- classification is graded against ground truth: the scripted learner turn's `expect_class`
  (or the `truth` list the harness keeps out of the tutor's sight), else the question's
  `answer_key`. An attempt with neither fails: there is nothing to grade it against.
- "one hint" is counted from the text: the single item sits in the turn's `feedback` field (one
  sentence, at most 40 words, copied verbatim into `text`), and nothing else in the text may be
  another explanation. Only a short verdict, an artifact pointer, a logistics line or a question
  may sit beside it.
The opening question may hold neither a hint marker nor a correction claim from the lesson.

Transcript shape (written by a tutor agent, or scripted in tests):
    {"mode": "predict-first|socratic|quiz|exam-drill|qa-expand",
     "turns": [{"role": "tutor", "acts": ["question"|"feedback"|"artifact"|"consent"|"answer"|"layer"|"close"],
                "text": "...", "classification": "correct|partial|misconception:<id>|skipped|timeout",
                "feedback": "the one hint or correction", "artifacts": [...], "states_shown": [...], ...mode fields},
               {"role": "learner", "kind": "attempt|consent-yes|consent-no|expand|satisfied|stop|other",
                "text": "...", "expect_class": "correct|partial|misconception:<id>|misconception:*"}],
     "events": [{"kind": "evidence", "after_turn": 3, "item": "...", "result": "...", "gap": "...",
                 "next_action": "...", "consent": true}]}
"""
import re

CLASSES = re.compile(r"^(?:correct|partial|skipped|timeout|misconception:[\w.\-]+)$")
EXAM_FORMATS = {"mcq", "msq", "nat"}
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
FENCED = re.compile(r"```.*?```", re.S)
IMPERATIVE = re.compile(r"(?:^|[.:]\s+)(?:predict|trace|work out|write down|say what|give the output)\b", re.I)
HINT = re.compile(r"\b(?:hints?|clue|tip|notice|look (?:at|for)|remember (?:that)?|note that|keep in mind|careful)\b", re.I)
VERDICT = re.compile(r"^(?:here(?:'s| is| are)|noted|next|score|total|stopped|done|time|you took|q?\d+[:.)])", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+")
WORD = re.compile(r"[a-z']{4,}")
STOP = {"that", "this", "with", "from", "into", "what", "does", "only", "which", "there", "their", "your"}


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


def _option_lines(text):
    return {w.strip() for w in re.split(r"[,\n]", str(text)) if w.strip()}


def _giveaways(q, facts):
    """Answer lines that some wrong option leaves out: saying one rules that option out, so it gives
    the answer away (P2-4). Lines every option shares (the setup) are safe."""
    wrong = [_option_lines(o.get("text", "")) for o in q.get("options", []) if not o.get("correct")]
    shared = set.intersection(*wrong) if wrong else set()
    return [ln for ln in _lines(facts[q["answer_fact"]].get("value", "")) if wrong and ln not in shared]


def _corrections(lesson):
    """The text of every misconception's correction claim: none of it may appear before the attempt."""
    claims = {c["id"]: c.get("text", "") for c in lesson.get("claims", [])}
    return [claims.get(m.get("correction"), "") for m in lesson.get("misconceptions", []) if claims.get(m.get("correction"))]


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
                      "giveaway_lines": _giveaways(q, facts),
                      "correction_claims": _corrections(lesson),
                      "related_facts": sorted(related), "hidden_states": hidden,
                      "visible_states": [s["id"] for s in trace if s["id"] not in hidden],
                      "problems": [f"question scene {scene['id']} opens on state {scene['state']}, which reveals the answer"]
                      if scene.get("state") in hidden else []})
    return plans


def leaks(text, answer_lines):
    """True when the prose states the answer: at least two of its lines in order (or the only line).
    Fenced code blocks (the program itself) are skipped; inline code is not."""
    need = min(2, len(answer_lines))
    prose = FENCED.sub(" ", str(text))  # showing the program is not stating its output
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


def _prose(text):
    return " ".join(CODE.sub(" ", str(text)).split())


def _one_question(text):
    marks = _prose(text).count("?")
    return marks == 1 or (marks == 0 and bool(IMPERATIVE.search(_prose(text))))


def check_common(t, lesson=None, truth=None):
    v = []
    turns = t["turns"]
    if not turns or turns[0]["role"] != "tutor":
        v.append("the transcript must open with the tutor's first turn")
    v += [f"turn {i}: two tutor turns in a row (the turn did not end)"
          for i in range(1, len(turns)) if turns[i]["role"] == turns[i - 1]["role"] == "tutor"]
    v += [f"turn {i}: a question turn must hold exactly one question (one '?' outside code, or an imperative prompt)"
          for i, x in _tutor(t) if "question" in x.get("acts", []) and not _one_question(x.get("text", ""))]
    v += [f"turn {i}: feedback needs a classification (correct, partial or misconception:<id>)"
          for i, x in _tutor(t) if "feedback" in x.get("acts", []) and not CLASSES.match(str(x.get("classification")))]
    v += [f"turn {i}: {p}" for i, x in _tutor(t) if "feedback" in x.get("acts", []) for p in feedback_unit(x)]
    known = {m["id"] for m in (lesson or {}).get("misconceptions", [])}
    v += [f"turn {i}: unknown misconception {x['classification']!r} (lesson has {sorted(known)})"
          for i, x in _tutor(t) if lesson and str(x.get("classification", "")).startswith("misconception:")
          and x["classification"].split(":", 1)[1] not in known]
    return v + check_classification(t, truth) + check_evidence(t) + check_stop(t)


def feedback_unit(x):
    """Problems with a feedback turn's single hint: it must be one marked sentence, and the rest of the
    text may not add a second correction or explanation (only a verdict, logistics or a question)."""
    unit, text = str(x.get("feedback") or "").strip(), _prose(x.get("text", ""))
    if not unit:
        return ["feedback turn has no `feedback` field holding its one hint or correction"]
    v = [] if len(SENTENCE.split(unit)) == 1 and len(unit.split()) <= 40 else ["the feedback item must be one sentence of at most 40 words"]
    v += [] if _prose(unit) in text else ["the feedback item must appear verbatim in the text"]
    rest = [s for s in SENTENCE.split(text.replace(_prose(unit), " ", 1).strip()) if s.strip()]
    extra = [s for s in rest if not s.rstrip().endswith("?") and len(s.split()) > 4 and not VERDICT.match(s.strip())]
    return v + [f"a second correction or explanation besides the one feedback item: {s[:60]!r}" for s in extra]


def _grade(cls, expected, attempt_text, key):
    """None when the tutor's class agrees with the ground truth, else the problem."""
    if expected is not None:
        options = expected if isinstance(expected, list) else [expected]
        ok = any(cls == e or (e == "misconception:*" and str(cls).startswith("misconception:")) for e in options)
        return None if ok else f"classified {cls!r}, ground truth is {' or '.join(options)}"
    if key is None:
        return "no ground truth to grade the classification (no expect_class on the attempt, no answer_key)"
    said, key = " ".join(re.findall(r"[\w.+-]+", str(attempt_text).lower())), " ".join(re.findall(r"[\w.+-]+", str(key).lower()))
    right = said == key or re.search(rf"(?<![\w.+-]){re.escape(key)}(?![\w.+-])", said) is not None
    return None if (cls == "correct") == right else \
        f"classified {cls!r}, but the attempt {'matches' if right else 'does not match'} the answer key"


def check_classification(t, truth=None):
    """Grade each attempt's classification against ground truth, never against the tutor's own label."""
    turns, v, key = t["turns"], [], None
    attempts = iter(truth or [])
    for i, x in enumerate(turns):
        key = x.get("answer_key", key) if x["role"] == "tutor" and "question" in x.get("acts", []) else key
        if x["role"] != "learner" or x.get("kind") != "attempt":
            continue
        expected = next(attempts, None) if truth is not None else x.get("expect_class")
        reply = turns[i + 1] if i + 1 < len(turns) else {}
        miss = _grade(reply.get("classification"), expected, x.get("text", ""), key) if "feedback" in reply.get("acts", []) else None
        v += [f"turn {i + 1}: {miss}"] if miss else []
    return v


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
    v += opening_leaks(t0.get("text", ""), plan)
    v += [f"turn {i}: an artifact before the attempt: {x['artifacts']}" for i, x in before if x.get("artifacts")]
    v += [f"turn {i}: shows hidden states {sorted(set(x.get('states_shown', [])) & hidden)} before the attempt"
          for i, x in before if set(x.get("states_shown", [])) & hidden]
    v += [f"turn {i}: states the answer before the attempt" for i, x in before if leaks(x.get("text", ""), answer)]
    after = [(i, x) for i, x in _tutor(t) if i > first]
    v += [] if after and "feedback" in after[0][1].get("acts", []) else ["the turn after the attempt must give feedback"]
    v += [] if any(x.get("artifacts") for _, x in after) else ["no artifact was shown after the attempt"]
    return v


def opening_leaks(text, plan):
    """The opening question may not hint, state a correction claim, or name an answer line that only
    the right answer predicts."""
    prose = FENCED.sub(" ", str(text)).lower()
    words = set(WORD.findall(prose))
    v = ["the opening question contains a hint marker"] if HINT.search(prose) else []
    for claim in plan.get("correction_claims", []):
        for sentence in SENTENCE.split(claim):
            key = set(WORD.findall(sentence.lower())) - STOP
            v += [f"the opening question states a correction claim: {sentence!r}"] \
                if len(key & words) >= 2 and len(key & words) * 3 >= len(key) * 2 else []
    v += [f"the opening question gives away the answer line {ln!r}" for ln in plan.get("giveaway_lines", [])
          if re.search(r"(?<!\w)" + re.escape(ln.lower()) + r"(?!\w)", prose)]
    return v


def check_quiz(t, lesson=None):
    qs = [(i, x) for i, x in _tutor(t) if "question" in x.get("acts", [])]
    v = [f"turn {i}: question states its own answer key" for i, x in qs
         if x.get("answer_key") is None or leaks(x.get("text", ""), [str(x.get("answer_key"))])]
    v += _answered_each(t, qs)
    close = [x for _, x in _tutor(t) if "close" in x.get("acts", [])]
    score = str(close[-1].get("score", "")) if close else ""
    v += [] if re.fullmatch(rf"\d+/{len(qs)}", score) else [f"close must give a score k/{len(qs)}, got {score!r}"]
    right = sum(x.get("classification") == "correct" for _, x in _tutor(t) if "feedback" in x.get("acts", []))
    v += [] if not score[:1].isdigit() or score.split("/")[0] == str(right) else \
        [f"score {score} does not match {right} answers classified correct"]
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


def check_transcript(t, lesson=None, truth=None):
    """All violations of the protocol for t['mode']; [] means it follows the protocol.

    truth: the ground-truth class of each learner attempt, in order, when the harness keeps it out of
    the transcript the tutor reads. Without it, each attempt's own `expect_class` is used."""
    mode_check = MODE_CHECKS.get(t.get("mode"))
    if mode_check is None:
        return [f"no protocol for mode {t.get('mode')!r}"]
    t = flatten(t)
    return mode_check(t, lesson) + check_common(t, lesson, truth)


def flatten(t):
    """Mode fields may sit at the top of a turn or in a sub-object named after the mode
    ({"quiz": {"answer_key": ...}}); the checks read them from the top."""
    mode = t.get("mode")
    turns = [{**x, **(x.get(mode) if isinstance(x.get(mode), dict) else {})} for x in t["turns"]]
    return {**t, "turns": turns}
