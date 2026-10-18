"""`ptk route`: tell the host agent the intent, mode, media and first turn for a request (AC-1.1..1.5).

Everything that decides a route is data in route_rules.json; this module only applies it.

1. Intent: the ordered `intent_rules` (first match wins) split ordinary tasks from teaching.
   An ordinary task gets no mode, no media and no teaching, even in a predict-first workspace.
2. Media: every `medium_rules` entry that matches adds its medium. Each match is removed from
   the text before the next rule, so "interactive video" is the IVE and not also an explorer.
3. Mode: each precedence stage proposes at most one mode, and the first stage in `precedence`
   with a proposal wins: explicit answer-now override > explicit attempt-first mode >
   workspace contract > other explicit mode > named medium > request shape > default.
   A quick or explain route that also names media becomes a lesson build (`with_media`).

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


def _compile(rule, macros):
    join = lambda pats: re.compile("|".join(f"(?:{_expand(p, macros)})" for p in pats))
    return {**rule, "any": join(rule["any"]), "unless": join(rule.get("unless", [NEVER]))}


@lru_cache(maxsize=1)
def rules():
    raw = json.loads(RULES_PATH.read_text())
    m = raw["macros"]
    out = dict(raw)
    out["intent_rules"] = [_compile(r, m) for r in raw["intent_rules"]]
    out["medium_rules"] = [_compile(r, m) for r in raw["medium_rules"]]
    out["mode_rules"] = {stage: [_compile(r, m) for r in rs] for stage, rs in raw["mode_rules"].items()}
    out["silent"] = re.compile("|".join(raw["silent"]))
    return out


def normalize(request):
    text = request.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(text.lower().split())


def _hit(rule, text):
    return bool(rule["any"].search(text)) and not rule["unless"].search(text)


def first_match(rule_list, text):
    return next((r for r in rule_list if _hit(r, text)), None)


def detect_media(text, R):
    """Return (media in canonical order, matched rule ids)."""
    found, ids, rest = set(), [], text
    for rule in R["medium_rules"]:
        if _hit(rule, rest):
            found.add(rule["medium"])
            ids.append(rule["id"])
            rest = rule["any"].sub(" ", rest)
    return [m for m in R["media_order"] if m in found], ids


def _stage(R, stage, text):
    rule = first_match(R["mode_rules"].get(stage, []), text)
    return (rule["mode"], rule["id"]) if rule else None


def proposals(text, media, contract_mode, R):
    """Each precedence stage's (mode, rule id), or None when the stage has nothing to say."""
    out = {stage: _stage(R, stage, text) for stage in R["mode_rules"]}
    out["workspace"] = (R["contract_modes"][contract_mode], "workspace-contract") \
        if contract_mode in R["contract_modes"] else None
    out["media"] = ("lesson", "named-medium") if media else None
    out["default"] = (R["default_mode"], "default")
    return out


def resolve_mode(text, media, contract_mode, R):
    """Return (mode, winning stage, rule id): the first stage in `precedence` with a proposal wins."""
    proposals_ = proposals(text, media, contract_mode, R)
    stage = next(s for s in R["precedence"] if proposals_.get(s))
    mode, rule_id = proposals_[stage]
    return (R["with_media"].get(mode, mode) if media else mode), stage, rule_id


def route(request, workspace_dir=None):
    """Route one request. workspace_dir defaults to the current directory."""
    text = normalize(request)
    if not text:
        raise errors.ModelError("route needs a non-empty request")
    R = rules()
    contract = workspace.read_contract(workspace_dir or Path.cwd(), R["workspace_contract"])
    intent_rule = first_match(R["intent_rules"], text)
    if intent_rule["intent"] == "ordinary_task":
        return {"intent": "ordinary_task", "mode": None, "media": [], "narration": False,
                "workspace_contract": contract, "first_turn": R["first_turn"]["ordinary_task"],
                "build_needed": False, "rules": [intent_rule["id"]]}
    media, media_ids = detect_media(text, R)
    mode, stage, mode_id = resolve_mode(text, media, contract["mode"], R)
    media = media or R["mode_media"].get(mode, [])
    narrated = bool(set(media) & set(R["narrated_media"])) and not R["silent"].search(text)
    return {"intent": "teach", "mode": mode, "media": media, "narration": narrated,
            "workspace_contract": contract, "first_turn": R["first_turn"][mode],
            "build_needed": bool(media), "rules": [intent_rule["id"], *media_ids, f"{stage}:{mode_id}"]}
