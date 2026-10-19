"""Round 18: captions show the written form (%f, factorial(2)); the voice reads lexicon(text). A hand-respelled
spoken form could say something the caption does not, so it is refused, and the sync WER is measured against the
form the voice was given."""
import copy

from _util import V21
from ptk import errors, model, tts
from ptk.project import video
from ptk.verify import media

SLICE = V21 / "lessons" / "switch-fallthrough"


def _cues():
    lesson = model.load(SLICE)
    return [{**s, "start": 0.0, "end": 1.0} for s in video.segments_of(lesson)]


def test_every_cue_speaks_lexicon_of_its_text():
    cues = _cues()
    assert media.derived_speech_problems(cues) == []
    assert all(c["said"] == c["text"] and c["spoken"] == tts.apply_lexicon(c["text"]) for c in cues)


def test_a_hand_edited_said_fails():
    """said edited to 'three' while the caption says 'two' must fail."""
    cues = _cues()
    i = next(k for k, c in enumerate(cues) if " two" in c["text"])
    bad = copy.deepcopy(cues)
    bad[i]["said"] = bad[i]["text"].replace(" two", " three")
    bad[i]["spoken"] = tts.apply_lexicon(bad[i]["said"])
    probs = media.derived_speech_problems(bad)
    assert [p["cue"] for p in probs] == [cues[i]["id"]], probs


def test_audio_that_differs_from_said_fails_the_wer():
    cues = _cues()
    heard = [{"text": w} for c in cues for w in c["spoken"].split()]
    rate, _r, _h = media.speech_wer(cues, heard)
    assert rate == 0.0, rate
    swapped = [{"text": "three" if w["text"].strip(".,").lower() == "two" else w["text"]} for w in heard]
    other = [{"text": w} for w in "the program prints one and then stops".split()] * 3
    assert media.speech_wer(cues, swapped)[0] > 0
    assert media.speech_wer(cues, other)[0] > media.WER_MAX


def test_a_lesson_may_not_author_a_spoken_form():
    data = copy.deepcopy(model.load(SLICE).data)
    data["storyboard"][0]["narration"][0]["spoken"] = "The program sets n to three."
    try:
        model.validate(data)
    except errors.ModelReferenceError as e:
        assert any(x["pointer"] == "/storyboard/0/narration/0/spoken" for x in e.detail["errors"])
    else:
        raise AssertionError("validate accepted an authored spoken form")


def test_lexicon_patterns_read_code_aloud():
    say = tts.apply_lexicon
    assert say("factorial(2) gets 1 and returns 2 × 1 = 2.") == "factorial of 2 gets 1 and returns 2 times 1 equals 2."
    assert say("so it prints 66.000000.") == "so it prints 66 followed by a point and six zeros."
    assert say("0.4 × -1 = -0.4") == "0.4 times minus 1 equals minus 0.4"
    assert say("So ub.c is compiled") == "So U B dot C is compiled"
