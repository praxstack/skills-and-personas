"""Claims mutation suite with controls (D17.5, E22, AC-7.5).

Each lesson gets up to 12 planted errors. Every mutation job is paired with a control job:
an unchanged copy of the lesson job. The reviewer can't tell them apart (job ids are hashes).

    lesson.json + artifact texts
        │
        ├─ authored mutations   lessons/<id>/mutations.json   (false mechanism, overbroad,
        │                                                     dropped caveat, wrong citation, ...)
        ├─ automatic value swaps                              (a captured value in a sentence
        │                                                     replaced by a different one)
        ▼
    select ≤ 12 ──▶ apply(body, mutation) ──▶ mutation job  +  control job (same body as the lesson)

Rates (E22): value mutations caught must be 100%, claim mutations ≥ 90%, controls accepted ≥ 95%.
A review that fails the schema is a schema rejection, counted apart from catches and misses.
"""
import copy
import json
import re

from .. import errors, text

MAX_MUTATIONS = 12
VALUE_KINDS = {"value-swap"}
CLAIM_KINDS = {"false-mechanism", "overbroad", "dropped-caveat", "wrong-citation", "false-framing",
               "ub-dishonest", "false-narration"}
KINDS = VALUE_KINDS | CLAIM_KINDS
AUTO_VALUE_SWAPS = 4
THRESHOLDS = {"value": 1.0, "claim": 0.90, "control": 0.95}


def family(kind):
    return "value" if kind in VALUE_KINDS else "claim"


# ---------------------------------------------------------------- authored mutations

def load_authored(lesson):
    p = lesson.dir / "mutations.json"
    if not p.exists():
        return []
    out = []
    for i, m in enumerate(json.loads(p.read_text())["mutations"]):
        if m.get("kind") not in KINDS:
            raise errors.ModelSchemaError(f"mutation kind {m.get('kind')!r} is not one of {sorted(KINDS)}",
                                          pointer=f"mutations.json#/mutations/{i}/kind")
        if "target" not in m or not m.get("id"):
            raise errors.ModelSchemaError("a mutation needs an id and a target", pointer=f"mutations.json#/mutations/{i}")
        out.append(dict(m, origin="authored"))
    return out


# ---------------------------------------------------------------- automatic value swaps

def _word_re(v):
    return re.compile(r"(?<![\w.])" + re.escape(v) + r"(?![\w]|\.\w)")


def _other_value(v, pool):
    """A different, plausible value: a number nudged by one, or another fact value of the same shape."""
    m = re.fullmatch(r"(-?)(\d+)((?:\.\d+)?)", v)
    if m:
        return f"{m.group(1)}{int(m.group(2)) + 1}{m.group(3)}"
    if re.fullmatch(r"[0-9a-fA-F]{2,}", v) and not v.isalpha():
        last = v[-1]
        return v[:-1] + ("0" if last != "0" else "1")
    return next((p for p in pool if p != v and p.isalpha() == v.isalpha()), None)


def auto_value_swaps(lesson, limit=AUTO_VALUE_SWAPS):
    """One swap per claim that states a captured value (claims[].facts), in claim order."""
    facts = lesson.by_id("facts")
    pool = [text.display(f) for f in lesson.data["facts"] if "\n" not in text.display(f)]
    out = []
    for c in lesson.data["claims"]:
        for fid in c.get("facts", []):
            v = text.display(facts[fid]) if fid in facts else ""
            if not v or "\n" in v or not _word_re(v).search(c["text"]):
                continue
            new = _other_value(v, [p for p in pool if not _word_re(p).search(c["text"])])
            if not new:
                continue
            out.append({"id": f"auto.value.{c['id']}.{fid}", "kind": "value-swap", "target": c["id"],
                        "find": v, "replace": new, "whole_word": True, "origin": "automatic",
                        "why_false": f"fact {fid} was captured as {v!r}, the text now says {new!r}"})
            break
        if len(out) >= limit:
            break
    return out


def select(lesson):
    """Authored mutations first (they cover the claim families), then automatic value swaps, ≤ 12."""
    authored = load_authored(lesson)
    auto = auto_value_swaps(lesson)
    n_auto = min(len(auto), max(MAX_MUTATIONS - len(authored), min(len(auto), 2)))
    picked = authored[:MAX_MUTATIONS - n_auto] + auto[:n_auto]
    return picked[:MAX_MUTATIONS]


# ---------------------------------------------------------------- apply

def _replace(s, m):
    if m.get("whole_word"):
        return _word_re(m["find"]).sub(m["replace"], s)
    return s.replace(m["find"], m["replace"])


def _contains(s, m):
    return bool(_word_re(m["find"]).search(s)) if m.get("whole_word") else m["find"] in s


def apply(body, m):
    """Return (mutated body, ids of the texts that changed). Raises ValueError if nothing changed,
    so a mutation whose anchor text disappeared (the lesson was edited) is reported, never silently
    counted as a catch."""
    b = copy.deepcopy(body)
    changed_texts, changed = [], False
    target = m["target"]
    claims = {c["id"]: c for c in b["claims"]}
    if target in claims:
        c = claims[target]
        if "find" in m and _contains(c["text"], m):
            c["text"] = _replace(c["text"], m)
            changed = True
        for fld, key in (("sources", "sources"), ("justification", "justification"), ("kind", "claim_kind")):
            if key in m:
                c[fld] = copy.deepcopy(m[key])
                changed = True
        if "find" in m and m.get("whole_word") and _contains(c.get("justification", ""), m):
            c["justification"] = _replace(c["justification"], m)
        for t in b["teaching_texts"]:
            if target in t["maps_to"] and "find" in m and _contains(t["text"], m):
                t["text"] = _replace(t["text"], m)
                changed_texts.append(t["id"])
    else:
        kind, _, ref = target.partition(":")
        src = {"narration": "narration", "trace": "trace", "question": "question"}.get(kind)
        for t in b["teaching_texts"]:
            if src and t["source"] == src and t["ref"] == ref and _contains(t["text"], m):
                t["text"] = _replace(t["text"], m)
                changed_texts.append(t["id"])
    if not changed and not changed_texts:
        raise ValueError(f"mutation {m['id']} changes nothing: anchor {m.get('find')!r} not found in {target}")
    return b, changed_texts


def misconception_overlap(m_text, lesson):
    """Largest word-set Jaccard overlap between a mutated sentence and any misconception statement
    (review P2-2: a planted error that restates a listed misconception is too easy)."""
    a = set(text.norm_words(m_text))
    best = 0.0
    for mc in lesson.data.get("misconceptions", []):
        b = set(text.norm_words(mc["statement"]))
        if a and b:
            best = max(best, len(a & b) / len(a | b))
    return best


# ---------------------------------------------------------------- rates

def caught(row):
    """A mutation is caught when the review rejects overall and rejects the planted claim
    or one of the texts the mutation changed."""
    if row.get("overall") != "reject":
        return False
    rej_c = {c["id"] for c in row.get("rejected_claims", [])}
    rej_t = {t["id"] for t in row.get("rejected_texts", [])}
    return row.get("planted_claim") in rej_c or bool(rej_t & set(row.get("changed_texts", [])))


def rates(rows):
    """rows: one per reviewed mutation or control job, with role, family, overall, rejected ids,
    and schema_invalid. Schema rejections are counted separately and never as catches."""
    out = {}
    for fam in ("value", "claim"):
        rs = [r for r in rows if r["role"] == "mutation" and r["family"] == fam]
        valid = [r for r in rs if not r.get("schema_invalid")]
        n_caught = sum(1 for r in valid if caught(r))
        out[fam] = {"n": len(rs), "caught": n_caught, "schema_rejections": len(rs) - len(valid),
                    "rate": round(n_caught / len(rs), 4) if rs else None}
    cs = [r for r in rows if r["role"] == "control"]
    cvalid = [r for r in cs if not r.get("schema_invalid")]
    acc = sum(1 for r in cvalid if r["overall"] == "accept")
    out["control"] = {"n": len(cs), "accepted": acc, "schema_rejections": len(cs) - len(cvalid),
                      "rate": round(acc / len(cs), 4) if cs else None}
    out["meets_thresholds"] = all(out[k]["rate"] is None or out[k]["rate"] >= THRESHOLDS[k] for k in THRESHOLDS) \
        and any(out[k]["n"] for k in ("value", "claim"))
    out["thresholds"] = THRESHOLDS
    return out
