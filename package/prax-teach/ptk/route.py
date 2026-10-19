"""`ptk route`: tell the host agent the intent, mode, media and first turn for a request (AC-1.1..1.5).

Everything that decides a route is data in route_rules.json; this module only applies it.

0. Views: the request is read in several views (`views`). `positive` drops every negated span
   (a negation cue plus the rest of its clause), so "I don't want a video" names no medium and
   "dont ask me questions" asks for no quiz. `media` also drops medium words used as the topic
   ("video codecs", "a deck of cards"). Each rule says which view (`scope`) it reads.
1. Intent: the ordered `intent_rules` (first match wins) split ordinary tasks and rebuilds of an
   existing lesson from teaching. A task gets no mode, no media and no teaching, whatever the
   workspace says; `explain_after` says the learner also asked why.
2. Media: every `medium_rules` entry that matches adds its medium. Each match is removed from
   the text before the next rule, so "interactive video" is the IVE and not also an explorer.
3. Mode: each precedence stage proposes at most one mode, and the first stage in `precedence`
   with a proposal wins: explicit answer-now override > a practice mode the learner asked for >
   other explicit mode > named medium > request shape > default (explain).
   A quick or explain route that also names media becomes a lesson build (`with_media`).
   Workspace files are not a stage: they never set the mode (AC-1.3 v1.4). When they ask for a
   style the route does not follow (prediction first), `workspace_conflict` names the file and line.
4. Confidence: `high` when one reading is clear. `low`, with `reasons`, when a medium was negated
   or read as a topic, explicit modes compete, a second intent rides along, or nothing matched.

No function here has more than five branches (AC-1.5, tests/test_route.py).
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from . import errors, workspace

RULES_PATH = Path(__file__).with_name("route_rules.json")
NEVER = r"(?!x)x"


def _expand(pattern, macros):
    for name, body in macros.items():
        pattern = pattern.replace(f"<<{name}>>", body)
    return pattern


def _join(patterns, macros):
    return re.compile("|".join(f"(?:{_expand(p, macros)})" for p in patterns))


def _compile(rule, macros):
    return {**rule, "any": _join(rule["any"], macros), "unless": _join(rule.get("unless", [NEVER]), macros),
            "all": [_join([p], macros) for p in rule.get("all", [])], "scope": rule.get("scope", "full")}


@lru_cache(maxsize=1)
def rules():
    raw = json.loads(RULES_PATH.read_text())
    m = raw["macros"]
    out = dict(raw)
    for key in ("intent_rules", "medium_rules", "also_rules"):
        out[key] = [_compile(r, m) for r in raw[key]]
    out["mode_rules"] = {stage: [_compile(r, m) for r in rs] for stage, rs in raw["mode_rules"].items()}
    for key in ("negation", "clause", "clean", "strong"):
        out[key] = _join([raw[key]], m)
    out["topic"] = _join(raw["topic_frames"], m)
    out["silent"] = re.compile("|".join(raw["silent"]))
    return out


def normalize(request):
    text = request.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(text.lower().split())


def _tidy(text, R):
    return R["clean"].sub("", " ".join(text.split()))


def views(text, R):
    """The request as each rule scope reads it, plus the negated and topic spans that were dropped."""
    positive = _tidy(R["negation"].sub(" ", text), R)
    clauses = [c for c in (_tidy(c, R) for c in R["clause"].split(positive)) if c]
    return {"full": text, "positive": positive, "media": _tidy(R["topic"].sub(" ", positive), R),
            "clause": clauses, "first": clauses[:1],
            "negated": " | ".join(m.group(0) for m in R["negation"].finditer(text)),
            "topic": " | ".join(m.group(0) for m in R["topic"].finditer(positive))}


def _hit_one(rule, text):
    return bool(rule["any"].search(text)) and not rule["unless"].search(text) \
        and all(p.search(text) for p in rule["all"])


def _hit(rule, V):
    texts = V[rule["scope"]]
    return any(_hit_one(rule, t) for t in ([texts] if isinstance(texts, str) else texts))


def first_match(rule_list, V):
    return next((r for r in rule_list if _hit(r, V)), None)


def detect_media(text, R):
    """Return (media in canonical order, matched rule ids)."""
    found, ids, rest = set(), [], text
    for rule in R["medium_rules"]:
        if _hit_one(rule, rest):
            found.add(rule["medium"])
            ids.append(rule["id"])
            rest = rule["any"].sub(" ", rest)
    return [m for m in R["media_order"] if m in found], ids


def _stage(R, stage, V):
    rule = first_match(R["mode_rules"].get(stage, []), V)
    return (rule["mode"], rule["id"]) if rule else None


def proposals(V, media, R):
    """Each precedence stage's (mode, rule id), or None when the stage has nothing to say."""
    out = {stage: _stage(R, stage, V) for stage in R["mode_rules"]}
    out["media"] = ("lesson", "named-medium") if media else None
    out["default"] = (R["default_mode"], "default")
    return out


def resolve_mode(props, media, R):
    """Return (mode, winning stage, rule id): the first stage in `precedence` with a proposal wins."""
    stage = next(s for s in R["precedence"] if props.get(s))
    mode, rule_id = props[stage]
    return (R["with_media"].get(mode, mode) if media else mode), stage, rule_id


# ---------------------------------------------------------------- confidence

def _negated(c):
    return [f"negated {m}" for m in detect_media(c["V"]["negated"], c["R"])[0] if m not in c["media"]]


def _topic(c):
    return [f"topic word, not a medium: {m}" for m in detect_media(c["V"]["topic"], c["R"])[0]]


def _competing(c):
    modes = sorted({c["props"][s][0] for s in c["R"]["explicit_stages"] if c["props"].get(s)})
    return [f"competing modes: {', '.join(modes)}"] * (len(modes) > 1)


def _weak(c):
    fired = any(c["props"].get(s) for s in c["R"]["signal_stages"])
    return ["weak match: only the default applied"] * (not fired and not c["R"]["strong"].search(c["V"]["full"]))


REASONS = (_negated, _topic, _competing, _weak)


def assess(ctx, also_rules):
    """(confidence, reasons): low when any reason applies."""
    reasons = [r for fn in REASONS for r in fn(ctx)] + [f"also {r['also']}" for r in also_rules if r.get("low")]
    return ("low" if reasons else "high"), reasons


# ---------------------------------------------------------------- workspace conflict (AC-1.3 v1.4)

def workspace_conflict(contract, R):
    """None, or the note that the workspace files ask for a style the route does not obey, naming
    each file and line. The route itself is the same as in an empty workspace."""
    spec = R["workspace_conflict"]
    if contract["asks"] not in spec["asks"]:
        return None
    where = [f"{e['file']}:{e['line']}" for e in contract["evidence"]]
    first = contract["evidence"][0]
    return {"asks": contract["asks"], "file": first["file"], "line": first["line"], "where": where,
            "note": spec["note"].format(where=", ".join(where))}


# ---------------------------------------------------------------- route

def _narrated(media, V, R):
    return bool(set(media) & set(R["narrated_media"])) and not R["silent"].search(V["full"])


def _task(V, R, contract, intent_rule):
    return {"intent": "ordinary_task", "mode": None, "media": [], "narration": False,
            "explain_after": bool(R["strong"].search(V["positive"])), "workspace_contract": contract,
            "workspace_conflict": None, "first_turn": R["first_turn"]["ordinary_task"], "build_needed": False,
            "confidence": "high", "reasons": [], "also": [], "rules": [intent_rule["id"]]}


def _rebuild(V, R, contract, intent_rule):
    media, media_ids = detect_media(V["positive"], R)
    return {"intent": "rebuild", "mode": None, "media": media, "narration": _narrated(media, V, R),
            "workspace_contract": contract, "workspace_conflict": None,
            "first_turn": R["first_turn"]["rebuild"], "build_needed": True,
            "confidence": "high", "reasons": [], "also": [], "rules": [intent_rule["id"], *media_ids]}


def _teach(V, R, contract, intent_rule):
    media, media_ids = detect_media(V["media"], R)
    props = proposals(V, media, R)
    mode, stage, mode_id = resolve_mode(props, media, R)
    media = media or R["mode_media"].get(mode, [])
    also_rules = [r for r in R["also_rules"] if _hit(r, V) and r["also"] != mode]
    confidence, reasons = assess({"V": V, "R": R, "props": props, "stage": stage, "media": media}, also_rules)
    return {"intent": "teach", "mode": mode, "media": media, "narration": _narrated(media, V, R),
            "workspace_contract": contract, "workspace_conflict": workspace_conflict(contract, R),
            "first_turn": R["first_turn"][mode], "build_needed": bool(media),
            "confidence": confidence, "reasons": reasons, "also": [r["also"] for r in also_rules],
            "rules": [intent_rule["id"], *media_ids, f"{stage}:{mode_id}"]}


BUILDERS = {"ordinary_task": _task, "rebuild": _rebuild, "teach": _teach}


def route(request, workspace_dir=None):
    """Route one request. workspace_dir defaults to the current directory."""
    text = normalize(request)
    if not text:
        raise errors.ModelError("route needs a non-empty request")
    R = rules()
    contract = workspace.read_contract(workspace_dir or Path.cwd(), R["workspace_contract"])
    V = views(text, R)
    intent_rule = first_match(R["intent_rules"], V)
    return BUILDERS[intent_rule["intent"]](V, R, contract, intent_rule)
