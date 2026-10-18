r"""Flash card projector (WP4: AC-4.4, AC-4.5, D4.5, E23): Markdown plus an Anki .apkg.

    storyboard question (with answer_fact)  ─▶ predict card   front: prompt + program
                                                               back:  the answer fact's captured lines
    every other program with stdout facts    ─▶ output card    front: "What does <file> print?" + program
                                                               back:  its stdout-line facts, in order
    every misconception                      ─▶ wrong-on-purpose card
                                                               front: "True or false? <statement>"
                                                               back:  "False." + its correction claim
    each back also gives the claims that cite the answer's facts ("Why")

Answers are the facts' captured text (text.display), never retyped. Each note's GUID is
genanki.guid_for(lesson id, card id), and the model and deck ids come from the lesson id, so a
rebuild produces the same GUIDs and Anki updates notes in place instead of adding duplicates.
"""
import hashlib
import html
import json

from .. import errors, fonts, text

FIELDS = ("Front", "Back", "CardId", "Facts")


def _stable_id(*parts):
    return int(hashlib.sha256("/".join(parts).encode()).hexdigest()[:8], 16) | (1 << 30)


def _stdout_facts(lesson, pid):
    lines = sorted((f for f in lesson.data["facts"] if f["program"] == pid and f["kind"] == "stdout-line"),
                   key=lambda f: f["select"]["line"])
    return lines


def _why(lesson, fact_ids):
    fs = set(fact_ids)
    return [{"id": c["id"], "text": c["text"]} for c in lesson.data["claims"] if fs & set(c.get("facts", []))]


def build_cards(lesson):
    facts = lesson.by_id("facts")
    cards, covered = [], set()
    for sc in lesson.data["storyboard"]:
        q = sc.get("question")
        if not q:
            continue
        st = lesson.state(sc["state"])["state"]
        f = facts[q["answer_fact"]]
        lines = _stdout_facts(lesson, f["program"])
        cards.append({"id": f"q:{sc['id']}", "kind": "predict", "front": q["prompt"], "front_source": f"question:{sc['id']}",
                      "program": st["program"], "answer": text.display(f).split("\n"), "facts": [f["id"]],
                      "why": _why(lesson, [f["id"]] + [x["id"] for x in lines])})
        covered.add(f["program"])
    for p in lesson.data["programs"]:
        lines = _stdout_facts(lesson, p["id"])
        if p["id"] in covered or not lines:
            continue
        cards.append({"id": f"out:{p['id']}", "kind": "output",
                      "front": text.ui("card_print", file=p["path"].split("/")[-1]), "front_source": "chrome:card_print",
                      "program": p["id"], "answer": [text.display(x) for x in lines], "facts": [x["id"] for x in lines],
                      "why": _why(lesson, [x["id"] for x in lines])})
    for m in lesson.data["misconceptions"]:
        c = lesson.claim(m["correction"])
        cards.append({"id": f"m:{m['id']}", "kind": "misconception", "misconception": m["id"],
                      "front": text.ui("card_true_false", statement=m["statement"]), "front_source": "chrome:card_true_false",
                      "answer": [text.ui("card_false")], "facts": [], "why": [{"id": c["id"], "text": c["text"]}]})
    if not cards:
        raise errors.ModelReferenceError("no question, output or misconception to make cards from", pointer="/storyboard")
    return cards


# ---------------------------------------------------------------- Markdown

def markdown(lesson, cards):
    out = [f"# {lesson.data['title']}", "", text.ui("card_md_intro", count=len(cards), title=lesson.data["title"]), ""]
    for i, c in enumerate(cards, 1):
        out += [f"## {i}. {c['front']}", "", f"<!-- card {c['id']} -->", ""]
        if c.get("program"):
            p = lesson.program(c["program"])
            out += [f"`{p['path'].split('/')[-1]}`", "", "```c", lesson.program_source(c["program"]).rstrip("\n"), "```", ""]
        out += [f"**{text.ui('answer_label')}**", ""]
        out += (["```text", *c["answer"], "```"] if c["facts"] else c["answer"]) + [""]
        if c["why"]:
            out += [f"**{text.ui('card_why')}**", ""] + [x for w in c["why"] for x in (w["text"], "")]
    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------- Anki

def _card_css():
    tk = fonts.tokens()["themes"]
    L, D = tk["light"], tk["dark"]
    return (f".card{{font-family:-apple-system,'Helvetica Neue',sans-serif;font-size:19px;line-height:1.5;text-align:left;"
            f"color:{L['ink']};background:{L['ground']};padding:6px}}"
            f".nightMode.card,.night_mode .card{{color:{D['ink']};background:{D['ground']}}}"
            f".q{{font-size:21px;font-weight:700;margin:0 0 12px}}"
            f"pre{{font-family:ui-monospace,Menlo,monospace;font-size:15px;background:{L['surface']};border:1px solid {L['rule']};"
            f"border-radius:8px;padding:10px 12px;white-space:pre-wrap}}"
            f".nightMode pre,.night_mode pre{{background:{D['surface']};border-color:{D['rule']}}}"
            f".file{{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:{L['label']}}}"
            f".ans{{font-family:ui-monospace,Menlo,monospace;font-size:22px;font-weight:700;color:{L['note']}}}"
            f".nightMode .ans,.night_mode .ans{{color:{D['value']}}}"
            f".false{{font-size:22px;font-weight:700;color:{L['correction']}}}"
            f".nightMode .false,.night_mode .false{{color:{D['correction']}}}"
            f".why{{color:{L['ink_soft']}}}.nightMode .why,.night_mode .why{{color:{D['ink_soft']}}}"
            f".lbl{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:{L['label']}}}"
            f".nightMode .lbl,.night_mode .lbl{{color:{D['label']}}}")


def anki_fields(lesson, c):
    e = html.escape
    front = f'<p class="q">{e(c["front"])}</p>'
    if c.get("program"):
        p = lesson.program(c["program"])
        front += (f'<p class="file">{e(p["path"].split("/")[-1])}</p>'
                  f'<pre><code>{e(lesson.program_source(c["program"]).rstrip())}</code></pre>')
    if c["facts"]:
        back = '<p class="ans">' + "<br>".join(f'<span class="v">{e(a)}</span>' for a in c["answer"]) + "</p>"
    else:
        back = f'<p class="false">{e(c["answer"][0])}</p>'
    if c["why"]:
        back += f'<p class="lbl">{e(text.ui("card_why"))}</p>' + "".join(f'<p class="why">{e(w["text"])}</p>' for w in c["why"])
    return [front, back, c["id"], ",".join(c["facts"])]


def write_apkg(lesson, cards, path):
    import genanki
    model = genanki.Model(_stable_id(lesson.id, "model"), f"prax-teach {lesson.id}",
                          fields=[{"name": f} for f in FIELDS],
                          templates=[{"name": "Card 1", "qfmt": "{{Front}}", "afmt": '{{FrontSide}}<hr id="answer">{{Back}}'}],
                          css=_card_css())
    deck = genanki.Deck(_stable_id(lesson.id, "deck"), f"C::{lesson.data['title']}")
    for c in cards:
        deck.add_note(genanki.Note(model=model, fields=anki_fields(lesson, c), guid=genanki.guid_for(lesson.id, c["id"]),
                                   tags=["prax-teach", lesson.id, c["kind"]]))
    genanki.Package(deck).write_to_file(str(path), timestamp=float(_stable_id(lesson.id, "ts")))


def project(lesson, out):
    out.mkdir(parents=True, exist_ok=True)
    cards = build_cards(lesson)
    md = out / f"{lesson.id}.md"
    md.write_text(markdown(lesson, cards))
    apkg = out / f"{lesson.id}.apkg"
    write_apkg(lesson, cards, apkg)
    (out / "cards.json").write_text(json.dumps(cards, indent=1, ensure_ascii=False))
    (out / "texts.json").write_text(json.dumps(_texts(lesson, cards), indent=1, ensure_ascii=False))
    return {"md": md, "apkg": apkg, "cards": cards}


def _texts(lesson, cards):
    items = [{"text": lesson.data["title"], "claims": [], "source": "label:title", "where": "cards"},
             {"text": text.ui("card_md_intro", count=len(cards), title=lesson.data["title"]), "claims": [],
              "source": "chrome:card_md_intro", "where": "cards .md"}]
    for key in ("answer_label", "card_why"):
        items.append({"text": text.ui(key), "claims": [], "source": f"chrome:{key}", "where": "cards"})
    for c in cards:
        w = f"cards {c['id']}"
        items.append({"text": c["front"], "claims": [], "source": c["front_source"], "where": w,
                      **({"misconception": c["misconception"]} if c.get("misconception") else {})})
        if c["facts"]:
            items.append({"text": "\n".join(c["answer"]), "claims": [], "source": "facts:" + ",".join(c["facts"]), "where": w})
        else:
            items.append({"text": c["answer"][0], "claims": [], "source": "chrome:card_false", "where": w})
        for x in c["why"]:
            items.append({"text": x["text"], "claims": [x["id"]], "source": f"claim:{x['id']}", "where": w})
    return items


def teaching_texts(build_dir):
    """Every sentence on every card: [{"text", "claims", "where", "source"}]."""
    p = build_dir / "cards" / "texts.json"
    return json.loads(p.read_text()) if p.exists() else []


# ---------------------------------------------------------------- checks (build gate and tests)

def read_apkg(path):
    """Notes in an .apkg (zip + SQLite): [{"guid", "fields": [...], "tags"}], plus the model ids."""
    import sqlite3
    import tempfile
    import zipfile
    from pathlib import Path
    with zipfile.ZipFile(path) as z, tempfile.TemporaryDirectory() as d:
        name = next(n for n in z.namelist() if n.startswith("collection.anki2"))
        z.extract(name, d)
        con = sqlite3.connect(Path(d) / name)
        try:
            notes = [{"guid": g, "fields": f.split("\x1f"), "tags": t.split(), "mid": mid}
                     for g, f, t, mid in con.execute("select guid, flds, tags, mid from notes order by id")]
            ncards = con.execute("select count(*) from cards").fetchone()[0]
        finally:
            con.close()
    return {"notes": notes, "cards": ncards}


def check_apkg(lesson, path):
    """AC-4.4: every note's answer equals its facts' captured text; GUIDs are the stable ones."""
    import re
    import genanki
    probs = []
    got = read_apkg(path)
    facts = lesson.by_id("facts")
    want = {genanki.guid_for(lesson.id, c["id"]): c for c in build_cards(lesson)}
    if sorted(n["guid"] for n in got["notes"]) != sorted(want):
        probs.append(f"GUIDs {[n['guid'] for n in got['notes']]} differ from the stable set {sorted(want)}")
    if got["cards"] != len(got["notes"]):
        probs.append(f"{got['cards']} cards for {len(got['notes'])} notes")
    for n in got["notes"]:
        c = want.get(n["guid"])
        if not c:
            continue
        front, back, cid, fids = n["fields"]
        if cid != c["id"]:
            probs.append(f"{n['guid']}: card id {cid} expected {c['id']}")
        if c["facts"]:
            shown = [html.unescape(v) for v in re.findall(r'<span class="v">(.*?)</span>', back)]
            truth = [ln for f in fids.split(",") for ln in text.display(facts[f]).split("\n")]
            if shown != truth:
                probs.append(f"{c['id']}: answer {shown} is not the captured facts {truth}")
        elif c["kind"] == "misconception":
            m = lesson.by_id("misconceptions")[c["misconception"]]
            if html.escape(m["statement"]) not in front or html.escape(lesson.claim(m["correction"])["text"]) not in back:
                probs.append(f"{c['id']}: misconception card lacks its statement or correction claim")
    return probs


def gate(lesson, res):
    probs = check_apkg(lesson, res["apkg"])
    md = res["md"].read_text()
    for c in res["cards"]:
        if c["facts"] and "\n".join(["```text", *c["answer"], "```"]) not in md:
            probs.append(f"{c['id']}: Markdown answer is not the captured facts")
    return {"id": "values.cards", "medium": "cards", "status": "failed" if probs else "passed",
            "measured": {"cards": len(res["cards"]), "misconception_cards": sum(c["kind"] == "misconception" for c in res["cards"]),
                         "apkg": res["apkg"].name, "problems": probs[:30],
                         "anki_import": "tests/test_cards.py::test_anki_import (not part of the build)"},
            "reason": "; ".join(probs[:3])[:500]}
