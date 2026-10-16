#!/usr/bin/env python3
"""captions.py: write captions.srt from timing.json, and optionally burn styled captions into a video.

Most templates draw captions inside the scene (better typography, synced by construction). Use --burn
only when a tool cannot draw text well; it renders an ASS subtitle track with libass.

Usage:
  python3 captions.py --project . [--out captions.srt]
  python3 captions.py --project . --burn build/silent.mp4 --burn-out build/silent-captioned.mp4 [--font Inter]
"""
import argparse
import json
import os
import re
import subprocess
import sys

# a kit whose captions take rich text (*mark*, `code`) says "rich_captions": true in its tool.json; its subtitles
# drop those delimiters and keep a lone * (data/*.csv, 3 * 4), as its rendered caption does. Other kits draw a
# caption's characters as written, so their subtitles keep them too.
MARK = re.compile(r"\*([^*\s](?:[^*]*[^*\s])?)\*|`([^`]+)`")


def rich_captions():
    here = os.path.dirname(os.path.abspath(__file__))
    # the kit's tool.json: next to scripts/ in the skill, or in pipeline/ itself in a delivered package (package.py)
    for p in (os.path.join(os.path.dirname(here), "tool.json"), os.path.join(here, "tool.json")):
        try:
            with open(p, encoding="utf-8") as f:
                return bool(json.load(f).get("rich_captions"))
        except (OSError, ValueError):
            continue
    return False


def split(cap, limit=84):
    if len(cap) <= limit:
        return [cap]
    mid, best, bd = len(cap) / 2, -1, 1e9
    for m in re.finditer(r"[.:;,?!] |… | — ", cap):
        i = m.start() + 1
        if abs(i - mid) < bd:
            bd, best = abs(i - mid), i
    if best < 0 or bd > len(cap) * 0.28:
        spaces = [i for i, c in enumerate(cap) if c == " "]
        # a caption with no space at all (a long identifier, a URL) is cut in the middle rather than crashing
        best = min(spaces, key=lambda i: abs(i - mid)) if spaces else int(mid)
    # each half is split again until every cue fits (a very long caption, or a break far from the middle)
    return [x for half in (cap[:best].strip(), cap[best:].strip()) if half for x in split(half, limit)]


def ts(x, sep=","):
    s, ms = divmod(int(round(max(0.0, x) * 1000)), 1000)  # round once, then carry (1.9996 s is 00:00:02,000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def cues(tm):
    out, rich = [], rich_captions()
    for ln in tm["lines"]:
        parts = split(MARK.sub(lambda m: m.group(1) or m.group(2), ln["cap"]) if rich else ln["cap"])
        start, end = ln["voiceAt"], ln["voiceAt"] + ln["voiceDur"]
        tot = sum(len(p) for p in parts)
        t = start
        for j, p in enumerate(parts):
            d = (end - start) * len(p) / tot
            e = (ln["end"] - 0.05) if j == len(parts) - 1 else t + d
            out.append((t, e, p))
            t += d
    return out


def write_srt(tm, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, text) in enumerate(cues(tm), 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{text}\n\n")


def ass_text(text):
    """A caption as literal ASS text. libass reads {...} as an override block and \\N, \\h, \\n as controls, so each
    backslash is kept apart from what follows by an invisible word joiner (U+2060) and each brace is escaped; a line
    break in the caption stays a line break."""
    text = re.sub(r"[{}]", lambda m: "\\" + m.group(0), text.replace("\\", "\\\u2060"))
    return re.sub(r"\r?\n", r"\\N", text)


def write_ass(tm, path, font, w, h):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{int(h * 0.034)},&H00F3EFEA,&H00FFFFFF,&H00000000,&H9A0B0B0D,0,0,0,0,100,100,0,0,3,14,0,2,160,160,{int(h * 0.055)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(head)
        for a, b, text in cues(tm):
            f.write(f"Dialogue: 0,{ts(a, '.')[:-1]},{ts(b, '.')[:-1]},Cap,,0,0,0,,{{\\fad(120,120)}}{ass_text(text)}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--out", default="captions.srt")
    ap.add_argument("--burn", default=None)
    ap.add_argument("--burn-out", default=None)
    ap.add_argument("--font", default="Inter")
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    tm = json.load(open(os.path.join(root, "timing.json"), encoding="utf-8"))
    out = a.out if os.path.isabs(a.out) else os.path.join(root, a.out)
    # relative paths are the project's, like --out, wherever this runs from
    inp = a.burn and (a.burn if os.path.isabs(a.burn) else os.path.join(root, a.burn))
    if inp and not os.path.isfile(inp):
        sys.exit(f"--burn {a.burn}: no such video ({inp})")
    if inp:
        base, ext = os.path.splitext(inp)
        if a.burn_out:
            dst = a.burn_out if os.path.isabs(a.burn_out) else os.path.join(root, a.burn_out)
        else:
            dst = f"{base}-captioned{ext or '.mp4'}"   # beside the input, whatever its extension
        if os.path.abspath(dst) == os.path.abspath(inp):
            sys.exit(f"--burn-out {dst} is the input video itself; name another file")
    write_srt(tm, out)
    print("wrote", out)
    if inp:
        ass = os.path.join(root, "build", "captions.ass")
        os.makedirs(os.path.dirname(ass), exist_ok=True)
        write_ass(tm, ass, a.font, tm.get("width", 1920), tm.get("height", 1080))
        # ffmpeg's filter syntax reads ' and : inside the path, so name the file relative to the folder it runs in
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.abspath(inp), "-vf", "ass=captions.ass",
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-an", os.path.abspath(dst)],
                       check=True, cwd=os.path.dirname(ass))
        print("burned captions into", dst)


if __name__ == "__main__":
    main()
