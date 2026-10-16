"""The film's clock, read from timing.json (written by voice.py --emit source/timing.json).

Scene code never hard-codes seconds. It keys everything to narration lines:

    from kit import L, TIMING
    self.beat("p3")                        # wait until the voice starts line p3 (its caption appears by itself)
    self.until(L["p3"].voiceAt + 0.4)      # a moment into the line
    self.until(L["p3"].said("seven hundred"))   # the moment a phrase is spoken (estimated from its position)
    self.play_until(L["p4"].voiceEnd, *anims)   # an animation that lands exactly when the sentence ends

Line fields: id, chapter, scene, start, voiceAt, voiceDur, voiceEnd, think, end, dur, cap, say.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TIMING_PATH = os.path.join(os.path.dirname(HERE), "timing.json")


class Line:
    def __init__(self, d):
        self.__dict__.update(d)
        self.voiceEnd = round(self.voiceAt + self.voiceDur, 3)

    def at(self, frac):
        """A time `frac` of the way through the spoken part (0 = voice starts, 1 = voice ends)."""
        return self.voiceAt + self.voiceDur * frac

    def said(self, phrase, after=0.0):
        """Estimated time the voice reaches `phrase` (searched in `say`, case-insensitive)."""
        s = self.say.lower()
        i = s.find(phrase.lower())
        if i < 0:
            raise KeyError(f"'{phrase}' is not in the spoken text of {self.id}: {self.say!r}")
        return self.voiceAt + self.voiceDur * i / max(1, len(s)) + after

    @property
    def thinkAt(self):
        """When the think pause starts (right after the voice, plus a small breath)."""
        return self.voiceEnd + 0.15

    def __repr__(self):
        return f"<Line {self.id} {self.start:.2f}-{self.end:.2f} voice {self.voiceAt:.2f}+{self.voiceDur:.2f}>"


def load(path=TIMING_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


TIMING = load()
LINES = [Line(d) for d in TIMING["lines"]]
L = {ln.id: ln for ln in LINES}
FPS = TIMING.get("fps", 30)
TOTAL = TIMING["total"]
CHAPTERS = TIMING["chapters"]          # [{"n", "name", "start", "end"}]
CHAPTER_NAMES = {c["n"]: c["name"] for c in CHAPTERS}


def lines_in(chapter):
    return [ln for ln in LINES if ln.chapter == chapter]


def bounds(first_id, last_id):
    """Film time span of a segment that holds lines first..last.

    A segment starts where the previous line ends (so a chapter gap belongs to the chapter it opens) and ends
    where its last line ends (the last line of the film ends at TOTAL). Consecutive segments tile [0, TOTAL]
    with no gap and no overlap, which is what makes the concatenated film match the voice to the frame."""
    ids = [ln.id for ln in LINES]
    i, j = ids.index(first_id), ids.index(last_id)
    if j < i:
        raise ValueError(f"segment {first_id}..{last_id} is backwards")
    t0 = 0.0 if i == 0 else LINES[i - 1].end
    t1 = TOTAL if j == len(LINES) - 1 else LINES[j].end
    return t0, t1


def chapter_bounds(chapters):
    """Span of whole chapters, e.g. chapter_bounds([1]) or chapter_bounds([3, 4])."""
    lns = [ln for ln in LINES if ln.chapter in set(chapters)]
    if not lns:
        raise ValueError(f"no lines in chapters {chapters}; check script.json")
    return bounds(lns[0].id, lns[-1].id), lns[0].id, lns[-1].id
