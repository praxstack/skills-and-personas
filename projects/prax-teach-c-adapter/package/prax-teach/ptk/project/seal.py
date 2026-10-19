r"""Question-aware titles (round 18, review X2 / AC-5.7).

A scene title is a sentence the learner reads before the scene plays: in the IVE chapter list and the Q&A
layer list it is on screen from the moment the page opens. So a title can give away a prediction that is
still open ("Six digits after the point" answers "what does %f print?").

Every scene after a question tags its title with the claims the title states or implies (`title_claims`,
[] for a neutral title). From the tags:

    question at scene q, answer fact F
    answer claims A(q) = claims whose `facts` include F or a part of it (a line of a whole-stdout answer,
                         a token of a line answer)
                       ∪ claims narrated in the answer scene (the first scene after q whose state shows F)
    scene j < q or j == q   title_claims ∩ A(q) must be empty   (the title is on screen while q is open)
    scene j > q             title_claims ∩ A(q) non-empty  →  sealed by q: the IVE and the Q&A show a neutral
                                                              placeholder until q is answered (or the film
                                                              has passed q's answer cue)

The lesson title is on every page, so it may not cite an answer claim either (top-level `title_claims`).
"""


def _shown(state):
    return set(state["state"].get("output", [])) | set(state.get("reveals", []))


def questions(data):
    """[(scene index, scene)] for every scene with a question, in order."""
    return [(i, sc) for i, sc in enumerate(data.get("storyboard", [])) if sc.get("question")]


def answer_scene(data, qi):
    """Index of the first scene after qi whose state shows the question's answer fact, or None."""
    sb = data.get("storyboard", [])
    fid = sb[qi]["question"]["answer_fact"]
    trace = {s["id"]: s for s in data.get("trace", [])}
    for j in range(qi + 1, len(sb)):
        st = trace.get(sb[j]["state"])
        if st and fid in _shown(st):
            return j
    return None


def answer_facts(data, qi):
    """The answer fact and every fact that is part of it: a whole-stdout answer contains each stdout line (and
    each token of a line) of its program; a line answer contains the tokens read from that line."""
    fid = data["storyboard"][qi]["question"]["answer_fact"]
    facts = {f["id"]: f for f in data.get("facts", [])}
    a = facts.get(fid)
    out = {fid}
    if not a or a["select"].get("stream") != "stdout":
        return out
    for f in data.get("facts", []):
        sel = f["select"]
        if f["program"] != a["program"] or sel.get("stream") != "stdout":
            continue
        if "line" not in a["select"] or (sel.get("line") == a["select"]["line"]):
            out.add(f["id"])
    return out


def answer_claims(data, qi):
    parts = answer_facts(data, qi)
    out = {c["id"] for c in data.get("claims", []) if parts & set(c.get("facts", []))}
    j = answer_scene(data, qi)
    if j is not None:
        out |= {cid for n in data["storyboard"][j]["narration"] for cid in n["claims"]}
    return out


def sealed(data):
    """{scene id: question scene id}: the scenes whose titles stay hidden until that question is answered."""
    out = {}
    sb = data.get("storyboard", [])
    for qi, q in questions(data):
        a = answer_claims(data, qi)
        for j in range(qi + 1, len(sb)):
            if sb[j]["id"] not in out and set(sb[j].get("title_claims") or []) & a:
                out[sb[j]["id"]] = q["id"]
    return out


def problems(data):
    """Model errors [{pointer, message}] for untagged or answer-stating titles."""
    errs = []
    sb = data.get("storyboard", [])
    claims = {c["id"] for c in data.get("claims", [])}
    for i, sc in enumerate(sb):
        for k, cid in enumerate(sc.get("title_claims") or []):
            if cid not in claims:
                errs.append({"pointer": f"/storyboard/{i}/title_claims/{k}", "message": f"unknown claim {cid!r}"})
    for k, cid in enumerate(data.get("title_claims") or []):
        if cid not in claims:
            errs.append({"pointer": f"/title_claims/{k}", "message": f"unknown claim {cid!r}"})
    qs = questions(data)
    if not qs:
        return errs
    first_q = qs[0][0]
    for j in range(first_q + 1, len(sb)):
        if "title_claims" not in sb[j]:
            errs.append({"pointer": f"/storyboard/{j}/title_claims", "message": f"scene {sb[j]['id']!r} comes after a "
                         "question, so its title is on screen while the question is open: tag it with the claims it "
                         "states or implies ([] for a neutral title)"})
    for qi, q in qs:
        a = answer_claims(data, qi)
        for j in range(0, qi + 1):
            hit = sorted(set(sb[j].get("title_claims") or []) & a)
            if hit:
                errs.append({"pointer": f"/storyboard/{j}/title_claims", "message": f"the title of {sb[j]['id']!r} "
                             f"states {hit}, the answer to the question in {q['id']!r}, and it is on screen before "
                             "the question is asked"})
        hit = sorted(set(data.get("title_claims") or []) & a)
        if hit:
            errs.append({"pointer": "/title_claims", "message": f"the lesson title states {hit}, the answer to the "
                         f"question in {q['id']!r}; every page shows it while the question is open"})
    return errs
