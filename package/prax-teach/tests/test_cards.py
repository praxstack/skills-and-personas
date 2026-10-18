"""WP4 flash cards: AC-4.4 (Markdown + .apkg, answers equal facts, stable GUIDs, re-import without
duplicates) and AC-4.5 (misconception cards). E23: the .apkg is opened as zip + SQLite; the real
Anki import runs only when an Anki CLI or the `anki` package exists, else it is not-run."""
import copy
import html
import importlib.util
import shutil
from pathlib import Path

from _util import SLICE
from ptk import host, model, text
from ptk.project import cards
from selftest_support import NotRun


def _build():
    lesson = model.load(SLICE)
    return lesson, cards.project(lesson, host.make_tmp("t-cards-") / "cards")


def test_apkg_contents():
    lesson, r = _build()
    probs = cards.check_apkg(lesson, r["apkg"])
    assert not probs, probs
    got = cards.read_apkg(r["apkg"])
    assert len(got["notes"]) == len(r["cards"]) == got["cards"], got["cards"]
    facts = lesson.by_id("facts")
    md = r["md"].read_text()
    for c in r["cards"]:
        for f in c["facts"]:
            for line in text.display(facts[f]).split("\n"):
                assert line in c["answer"], (c["id"], line)
        if c["facts"]:
            assert "\n".join(["```text", *c["answer"], "```"]) in md, c["id"]
    assert cards.gate(lesson, r)["status"] == "passed"
    # negative: one answer line changed in the deck must fail
    bad_cards = copy.deepcopy(r["cards"])
    bad_cards[0]["answer"] = ["two", "done"]
    bad = host.make_tmp("t-cards-bad-") / "bad.apkg"
    cards.write_apkg(lesson, bad_cards, bad)
    assert any("is not the captured facts" in p for p in cards.check_apkg(lesson, bad)), "a wrong answer passed"
    return {"notes": len(got["notes"]), "md_bytes": len(md)}


def test_stable_guids():
    lesson, r1 = _build()
    _l, r2 = _build()
    g1 = [n["guid"] for n in cards.read_apkg(r1["apkg"])["notes"]]
    g2 = [n["guid"] for n in cards.read_apkg(r2["apkg"])["notes"]]
    m1 = {n["mid"] for n in cards.read_apkg(r1["apkg"])["notes"]}
    m2 = {n["mid"] for n in cards.read_apkg(r2["apkg"])["notes"]}
    assert g1 == g2 and len(set(g1)) == len(g1), (g1, g2)
    assert m1 == m2, (m1, m2)
    assert r1["md"].read_text() == r2["md"].read_text()
    import genanki
    assert sorted(g1) == sorted(genanki.guid_for(lesson.id, c["id"]) for c in r1["cards"])
    return {"guids": len(g1)}


def test_misconception_cards():
    lesson, r = _build()
    mis = lesson.data["misconceptions"]
    mc = [c for c in r["cards"] if c["kind"] == "misconception"]
    assert sorted(c["misconception"] for c in mc) == sorted(m["id"] for m in mis), mc
    notes = {n["fields"][2]: n["fields"] for n in cards.read_apkg(r["apkg"])["notes"]}
    for m in mis:
        front, back, _cid, _f = notes[f"m:{m['id']}"]
        assert html.escape(m["statement"]) in front, front
        assert html.escape(text.ui("card_false")) in back
        assert html.escape(lesson.claim(m["correction"])["text"]) in back, back
    return {"misconception_cards": len(mc)}


def _anki_available():
    if importlib.util.find_spec("anki") is not None:
        return "anki package"
    for p in ("/Applications/Anki.app", str(Path.home() / "Applications" / "Anki.app")):
        if Path(p).exists():
            return p
    return None


def test_anki_import():
    """E23: import into an isolated profile twice; the second import must not add notes."""
    where = _anki_available()
    if where != "anki package":
        raise NotRun("no `anki` Python package in the ptk venv" + (f" (found {where}, which has no scripting CLI)"
                                                                  if where else "; no Anki app either"))
    from anki.collection import Collection, ImportAnkiPackageRequest
    lesson, r = _build()
    tmp = host.make_tmp("t-anki-")
    try:
        col = Collection(str(tmp / "collection.anki2"))
        counts = []
        for _ in range(2):
            col.import_anki_package(ImportAnkiPackageRequest(package_path=str(r["apkg"])))
            counts.append(col.note_count())
        col.close()
        assert counts[0] == len(r["cards"]) and counts[1] == counts[0], counts
        return {"notes_after_each_import": counts}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
