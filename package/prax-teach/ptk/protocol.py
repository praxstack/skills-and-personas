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
  may sit beside it. Quiz and exam-drill turns may also hold what their own protocol requires
  (the next question block; score, weakest item, one next action, another-round offer; marks,
  time and the attempted question's key), each in a form too small to carry a second correction.
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
MARK = re.compile(r"[+\-\u2212]?\d+(?:\.\d+)?(?:/[1-9]\d*)?")
QHEAD = re.compile(r"^(?:(?:the\s+)?next\s+question\b|(?:here(?:'s|\s+is)\s+)?(?:question|q)\s*\d+\b|\d+\s*[:.)])", re.I)
REVEAL = re.compile(r"(?i:\b(?:correct\s+)?(?:answer|key)\s*(?:is|was|:)\s*)\(?([A-D])\b"
                    r"|(?<![\w-])([A-D])\)?\s+(?i:is\s+(?:the\s+)?(?:correct|right|answer|key))\b")
WEAK = re.compile(r"\bweak(?:est|ness|\s+spot|\s+point)?\b", re.I)
NEXT = re.compile(r"^(?:(?:your|one|the)\s+)?next(?:\s+(?:step|action|time|move|check))?\b", re.I)
ROUND = re.compile(r"\banother\s+(?:round|quiz|drill|set|question)\b", re.I)
TOKEN = re.compile(r"[+\-\u2212]?\d+(?:\.\d+)?(?:/\d+)?|[a-z']+", re.I)
DATA_WORDS = set("""mark marks s sec secs second seconds min mins minute minutes of your the a an limit you took under over
    against each on and out total correct right wrong incorrect accuracy time per question questions q score final so far
    drill result results for this round stays is was that's got both in used taken left earned awarded net plus minus
    lost deducted it at all with from overall now answers answer key option items item attempt attempts to within spent
    clock timer""".split())
FILLER = set("only just it prints print printed output outputs is would will first then finally and the we get you see "
             "lines line shows should be program".split())
SEP = re.compile(r"\s*(?:\n|,|;|->|\u2192|\bthen\b|\band\b|\bfollowed by\b)\s*", re.I)
NEW_NAME = 32  # longest new misconception name, in characters
CAP = {"weakest item": 18, "next action": 25, "another-round offer": 15}


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
    v += _feedback_turns(t)
    # TEACHING: an id from the lesson's misconceptions, or a short new name if none fits. Whether one
    # fits is graded against the attempt's ground truth (check_classification), not guessed here.
    known = {m["id"] for m in (lesson or {}).get("misconceptions", [])}
    v += [f"turn {i}: unknown misconception {x['classification']!r} is not a short new name (lesson has {sorted(known)})"
          for i, x in _tutor(t) if lesson and str(x.get("classification", "")).startswith("misconception:")
          and x["classification"].split(":", 1)[1] not in known and len(x["classification"].split(":", 1)[1]) > NEW_NAME]
    return v + check_classification(t, truth) + check_evidence(t) + check_stop(t)


def _feedback_turns(t):
    v, prev = [], None
    for i, x in _tutor(t):
        v += [f"turn {i}: {p}" for p in feedback_unit(x, t.get("mode"), prev)] if "feedback" in x.get("acts", []) else []
        prev = x if "question" in x.get("acts", []) else prev
    return v


def feedback_unit(x, mode=None, prev=None):
    """Problems with a feedback turn's single hint: it must be one marked sentence, and the rest of the
    text may not add a second correction or explanation (only a verdict, logistics or a question).
    In quiz and exam-drill the rest may also hold what that mode's protocol requires (`_mode_extra`);
    `prev` is the question turn this feedback answers."""
    unit, text = str(x.get("feedback") or "").strip(), _prose(x.get("text", ""))
    if not unit:
        return ["feedback turn has no `feedback` field holding its one hint or correction"]
    v = [] if len(SENTENCE.split(unit)) == 1 and len(unit.split()) <= 40 else ["the feedback item must be one sentence of at most 40 words"]
    v += [] if _prose(unit) in text else ["the feedback item must appear verbatim in the text"]
    if mode in ("quiz", "exam-drill"):
        return v + _mode_extras(x, mode, prev)
    rest = [s for s in SENTENCE.split(text.replace(_prose(unit), " ", 1).strip()) if s.strip()]
    extra = [s for s in rest if not s.rstrip().endswith("?") and len(s.split()) > 4 and not VERDICT.match(s.strip())]
    return v + [f"a second correction or explanation besides the one feedback item: {s[:60]!r}" for s in extra]


def _sentences(text):
    """Sentences, also split at line breaks so a list's lines stay separate; bullet marks dropped."""
    out = []
    for line in str(text).splitlines():
        out += [re.sub(r"^[-*\u2022]\s+", "", s) for s in SENTENCE.split(" ".join(line.split())) if s.strip()]
    return out


def _split_turn(x):
    """A quiz or exam feedback turn as (sentences before the next question, the next-question block).
    Fenced code is dropped, inline code kept. The block starts at the first question header
    ("Question 2", "Q2", "2:", "Next question") after the feedback item, else at the sentence holding
    the '?'; it runs to the end of the text. A turn without the question act has no block."""
    text = re.sub(r"[ \t]+", " ", FENCED.sub(" ", str(x.get("text", ""))))
    unit = " ".join(FENCED.sub(" ", str(x.get("feedback") or "")).split())
    flat = " ".join(text.split())
    anchored = bool(unit) and (unit in text or unit in flat)
    if anchored:
        before, _, after = (text if unit in text else flat).partition(unit)
    else:  # no item to anchor on: the block is the last header or question in the text
        before, after = "", text
    pre, post = _sentences(before), _sentences(after)
    if "question" not in x.get("acts", []):
        return pre + post, []
    heads = [k for k, s in enumerate(post) if QHEAD.match(s)]
    asks = [k for k, s in enumerate(post) if "?" in _prose(s)]
    start = (heads[0] if anchored else heads[-1]) if heads else (asks[-1] if asks else None)
    return (pre + post, []) if start is None else (pre + post[:start], post[start:])


def _option_letters(q):
    """The answer key of a question as a set of option letters, or None when it is not an option key."""
    key = (q or {}).get("answer_key")
    if isinstance(key, dict):
        key = key.get("option")
    elif not (q or {}).get("options"):
        return None
    items = key if isinstance(key, (list, tuple)) else re.split(r"[\s,;/&]+|\band\b", str(key or "").strip(" .()"))
    letters = {str(k).strip(" .()").upper() for k in items if str(k).strip(" .()")}
    return letters if letters and all(re.fullmatch(r"[A-D]", k) for k in letters) else None


def _option_text(q, letter):
    for k, opt in enumerate((q or {}).get("options", [])):
        m = re.match(r"\s*\(?([A-D])[.):]?\s+", str(opt))
        if (m and m.group(1) == letter) or (not m and k == "ABCD".find(letter)):
            return str(opt)[m.end():] if m else str(opt)
    key = (q or {}).get("answer_key")
    return str(key.get("value", "")) if isinstance(key, dict) else ""


def _is_data(s):
    """A marks, time, score or accuracy line: numbers and their units, at most two other words."""
    toks = TOKEN.findall(s)
    nums = [t for t in toks if MARK.fullmatch(t)]
    return bool(nums) and sum(t.lower() not in DATA_WORDS and not MARK.fullmatch(t) for t in toks) <= 2


def _reveal(s, prev):
    """'key' when s reveals the attempted question's option key and nothing else, 'other' when it names
    another letter as the key, None when it reveals no option key."""
    m = REVEAL.search(s)
    if not m:
        return None
    letter, letters = m.group(1) or m.group(2), _option_letters(prev) or set()
    if letter not in letters:
        return "other"
    allowed = {t.lower() for t in TOKEN.findall(_option_text(prev, letter))} | {"the", "answer", "key", "is", "was", "correct", "option"}
    rest = [t.lower() for t in TOKEN.findall(s[:m.start()] + " " + s[m.end():])]
    return "key" if all(t in allowed for t in rest) else None


def _mode_extra(s, mode, asks, prev):
    """What kind of allowed sentence s is beside a quiz or exam-drill feedback item, or None."""
    words = s.split()
    if mode == "exam-drill" and (kind := _reveal(s, prev)):
        return "attempted key" if kind == "key" else "other key"
    if s.rstrip().endswith("?"):
        return "question"
    if len(words) <= 4:
        return "verdict"
    if _is_data(s):
        return "data"
    summary = "next action" if NEXT.match(s) else "weakest item" if WEAK.search(s) else \
        "another-round offer" if ROUND.search(s) else None
    if summary:  # the after-last-answer items: only on a turn with no next question, each one short
        return summary if not asks and len(words) <= CAP[summary] else None
    return "verdict" if VERDICT.match(s.strip()) else None


def _mode_extras(x, mode, prev):
    body, block = _split_turn(x)
    asks = "question" in x.get("acts", [])
    v = ["the next question must come after the feedback item in the same turn"] if asks and not block else []
    v += [f"a hint inside the next question: {s[:60]!r}" for s in block if HINT.search(_prose(s))]
    kinds = []
    for s in body:
        kind = _mode_extra(_prose(s), mode, asks, prev)
        kinds.append(kind)
        if kind is None:
            v.append(f"a second correction or explanation besides the one feedback item: {s[:60]!r}")
        elif kind == "other key":
            v.append(f"reveals a key other than the attempted question's: {s[:60]!r}")
    return v + [f"more than one {k} in one turn" for k in ("next action", "weakest item") if kinds.count(k) > 1]


def _question_text(x):
    """The text of a question turn that asks the new question: the whole text, or a feedback turn's block."""
    if "feedback" not in x.get("acts", []):
        return str(x.get("text", ""))
    block = _split_turn(x)[1]
    return " ".join(block) if block else str(x.get("text", ""))


def _seq(text):
    """Output lines named in an answer, in order: split on newlines, commas, 'and', 'then'; filler dropped."""
    out = []
    for seg in SEP.split(str(text)):
        words = [w.strip("\"'`.!?:()[]") for w in seg.split()]
        words = [w.lower() for w in words if w]
        core = list(words)
        while core and core[0] in FILLER:
            core.pop(0)
        while core and core[-1] in FILLER:
            core.pop()
        out += [" ".join(core or words)] if words else []
    return out


def answer_matches(attempt, key, options=()):
    """True when the attempt gives the answer key. Option keys ({"option": "B"}, or a letter when the
    question has options) match by letter set; output keys (text with a newline) match by the
    sequence of lines, nothing missing, nothing extra; other keys by their words."""
    q = {"answer_key": key, "options": list(options)}
    letters = _option_letters(q)
    toks = re.findall(r"[A-Za-z]+", str(attempt))
    said = {t.upper() for t in toks if t.lower() not in {"option", "options", "answer", "and", "is", "my", "the", "i", "pick"}}
    said = said if toks and said and all(re.fullmatch(r"[A-D]", t) for t in said) else None
    if letters is not None:
        return said == letters
    if isinstance(key, dict):
        key = key.get("value", "")
    if said is not None and len(said) == 1 and options:
        return answer_matches(_option_text(q, next(iter(said))), key)
    key = "\n".join(map(str, key)) + "\n" if isinstance(key, (list, tuple)) else str(key)
    if "\n" in key and not any(SEP.search(ln) for ln in _lines(key)):
        want, got = _seq(key), _seq(attempt)
        return got == want or (len(got) == 1 and got[0] == " ".join(want))
    said_w, key_w = " ".join(re.findall(r"[\w.+-]+", str(attempt).lower())), " ".join(re.findall(r"[\w.+-]+", key.lower()))
    return said_w == key_w or re.search(rf"(?<![\w.+-]){re.escape(key_w)}(?![\w.+-])", said_w) is not None


def is_mark(value):
    """A GATE mark: an int, a float, or a fraction string such as "-1/3" or "2/3"."""
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float)) or (isinstance(value, str) and MARK.fullmatch(value.strip()) is not None)


def _grade(cls, expected, attempt_text, q):
    """None when the tutor's class agrees with the ground truth, else the problem."""
    if expected is not None:
        options = expected if isinstance(expected, list) else [expected]
        ok = any(cls == e or (e == "misconception:*" and str(cls).startswith("misconception:")) for e in options)
        return None if ok else f"classified {cls!r}, ground truth is {' or '.join(options)}"
    if (q or {}).get("answer_key") is None:
        return "no ground truth to grade the classification (no expect_class on the attempt, no answer_key)"
    right = answer_matches(attempt_text, q["answer_key"], q.get("options") or [])
    return None if (cls == "correct") == right else \
        f"classified {cls!r}, but the attempt {'matches' if right else 'does not match'} the answer key"


def check_classification(t, truth=None):
    """Grade each attempt's classification against ground truth, never against the tutor's own label."""
    turns, v, q = t["turns"], [], None
    attempts = iter(truth or [])
    for i, x in enumerate(turns):
        q = x if x["role"] == "tutor" and "question" in x.get("acts", []) else q
        if x["role"] != "learner" or x.get("kind") != "attempt":
            continue
        expected = next(attempts, None) if truth is not None else x.get("expect_class")
        reply = turns[i + 1] if i + 1 < len(turns) else {}
        miss = _grade(reply.get("classification"), expected, x.get("text", ""), q) if "feedback" in reply.get("acts", []) else None
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


def _key_lines(key):
    key = key.get("value", "") if isinstance(key, dict) else key
    return _lines(key) if "\n" in str(key) else [str(key)]


def check_quiz(t, lesson=None):
    qs = [(i, x) for i, x in _tutor(t) if "question" in x.get("acts", [])]
    v = [f"turn {i}: question states its own answer key" for i, x in qs
         if x.get("answer_key") is None or leaks(_question_text(x), _key_lines(x.get("answer_key")))]
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
          if x.get("format", t0.get("format")) == "nat" and leaks(_question_text(x), _key_lines(x.get("answer_key")))]
    v += [f"turn {i}: question states its own answer key before the attempt" for i, x in qs
          if any((m := REVEAL.search(_prose(s))) and (m.group(1) or m.group(2)) in (_option_letters(x) or set())
                 for s in _sentences(FENCED.sub(" ", _question_text(x))))]
    fbs = [x for _, x in _tutor(t) if "feedback" in x.get("acts", [])]
    v += ["exam feedback must give marks_awarded (a number or a fraction like -1/3) and elapsed_s" for x in fbs
          if not is_mark(x.get("marks_awarded")) or not isinstance(x.get("elapsed_s"), (int, float))
          or isinstance(x.get("elapsed_s"), bool)]
    v += _answered_each(t, qs)
    close = [x for _, x in _tutor(t) if "close" in x.get("acts", [])]
    v += [] if close and is_mark(close[-1].get("total_marks")) else ["close must give total_marks (a number or a fraction)"]
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
