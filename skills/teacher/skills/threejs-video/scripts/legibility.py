#!/usr/bin/env python3
"""legibility.py: measure every piece of text in the review stills (size and contrast) against the quality bar.

It reads the text with an offline OCR model (RapidOCR, whose models ship inside the pip wheel), then measures
each text box itself, so the numbers do not depend on what the OCR thinks the words are:
  size      the cap height of the glyphs (the tallest glyph standing on the baseline), converted to a font size at 1080p
            (on the frame's short side, so a 1080x1920 Short is measured like a 1920x1080 film)
            (Inter and JetBrains Mono caps are 0.727 em; measured to within 1 px from 12 to 36 px on 1080p
            frames; a 480p draft still is about 2.3x coarser, so check close calls on a full-size still). A text with
            no tall glyph at all ("src =") is measured by its x-height instead (0.56 em)
  contrast  WCAG ratio between the text (90th percentile of the ink, toward the extreme) and the background (the
            median of the box's padded border)

Rules (shared/references/quality-bar.md): nothing under 26 px; contrast at least 4.5:1 for every text, large
or small, dimmed or not. A text fails as soon as it measures under a rule (no tolerance); a text within 4% above
a rule is listed as a close call, because the measurement itself is good to about 4%, so look at it on the
full-size still. Single characters (node digits, line numbers) are measured when the OCR is sure of them.

Usage:
  python3 legibility.py --project .                 checks every still in the stills folder, writes
                                                    <stills>/legibility.json and marked copies in <stills>/legibility/
  python3 legibility.py a.png b.jpg ...             checks these images only (prints, writes nothing)
  python3 legibility.py --video out/x.mp4 --every 5 samples the finished film
  python3 legibility.py --video out/x.mp4 --fps 4    follows text through the moving film: a text under the bar
                                                    for --dwell seconds (0.5) or longer fails; shorter dips are motion
                    [--footage footage-map.json]    (a film with recorded footage: see below)

Recorded footage (a product demo's screen recordings): the product's own interface is shown as it was recorded,
so its text is not the film's to resize. When the page reports where footage is (window.FOOTAGE, written beside
each still as <still>.footage.json by capture.mjs, or a --footage map over time), a text whose centre lies on the
footage is listed apart ("on footage", grey boxes) and does not count as a failure. Everything the film draws is
still held to the rules, including notes drawn over the footage (the map's "keep" boxes). Show what a line is
about by pushing the camera in on it and saying it in the film's own text; do not lean on the recording's.
Exit status 1 when any text breaks a rule. Open the marked copies: red boxes are failures, with the measurement.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pydeps  # noqa: E402  (pydeps.py ships next to this file)
import vstate  # noqa: E402

CAP_EM = 0.727
# A text made only of short letters ("src =", "a, c") has no glyph as tall as a capital, so its tallest glyph is
# the x-height. JetBrains Mono's x-height measures 0.56 em on our 1080p stills (the same code line read 30.3 px
# whole and 23.4 px when the OCR split off "src ="); Inter's is 0.546 em, so 0.56 errs small for Inter too.
XH_EM = 0.56
SHORT = set("acemnorsuvwxz")
TOL = 0.04


def need(mod, pip_name=None):
    """Import, installing once if missing (pydeps.py: the pipeline's own environment where pip refuses)."""
    return pydeps.need(mod, pip_name)


def lum(np, rgb):
    c = rgb / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def glyph_px(np, hs, txt, scale):
    """Font size at 1080p from the heights of the glyphs standing on the baseline. The tallest is a capital, digit or
    ascender (CAP_EM), except when the OCR read only short letters AND the glyphs measure one height (so none of
    them is a misread capital): then the tallest is the x-height (XH_EM)."""
    alnum = [ch for ch in txt if ch.isalnum()]
    short = bool(alnum) and all(ch in SHORT for ch in alnum) and hs.max() <= 1.15 * np.median(hs)
    return float(hs.max()) / (XH_EM if short else CAP_EM) * scale


def _read(np, cv2, P, bg, box_h, scale, txt):
    """(contrast, font px) of the text in patch P measured against background luminance bg, or None."""
    c = np.log((P + 0.05) / (bg + 0.05))
    lo_c, hi_c = np.percentile(c, 1), np.percentile(c, 99)
    sign = 1.0 if hi_c >= -lo_c else -1.0
    peak = max(hi_c, -lo_c)
    ink = c * sign > 0.5 * peak
    text = float(np.percentile(P[ink], 90 if sign > 0 else 10)) if ink.any() else bg
    contrast = (max(text, bg) + 0.05) / (min(text, bg) + 0.05)
    n, _, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    top, h = st[1:, cv2.CC_STAT_TOP].astype(float), st[1:, cv2.CC_STAT_HEIGHT].astype(float)
    big = h >= max(3, 0.25 * (box_h - 6))  # grain, dots and commas are not glyphs
    if big.sum() == 0:
        return None
    top, h = top[big], h[big]
    # Cap height = the tallest glyph that sits on the baseline. Letters, digits and capitals sit on it; brackets,
    # descenders and commas hang below it, so they are left out. (A percentile of all glyph heights read code
    # lines like "vector<int> next = dist;" 35% small.)
    bottom = top + h
    med = np.median(h)
    base = np.median(bottom[h >= 0.5 * med])
    on = np.abs(bottom - base) <= max(1.5, 0.08 * med)
    hs = h[on] if on.any() else h
    hs = hs[hs <= 1.6 * np.median(hs)]  # merged blobs (two touching glyphs, an underline) are not one glyph
    px = glyph_px(np, hs, txt, scale)
    return contrast, px


def _ground(np, cv2, inner):
    """Luminance of the ground the glyphs in `inner` stand on: of the two Otsu halves, the one an erosion keeps best."""
    u8 = np.clip(np.sqrt(inner) * 255, 0, 255).astype(np.uint8)  # sqrt spreads the dark end, where most inks sit
    _, hi = cv2.threshold(u8, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    k = np.ones((5, 5), np.uint8)
    best, keep = None, -1.0
    for m in (hi, 1 - hi):
        n = int(m.sum())
        if n < 20:
            continue
        kept = cv2.erode(m.astype(np.uint8), k).sum() / n
        if kept > keep:
            best, keep = m.astype(bool), kept
    return float(np.median(inner[best])) if best is not None else float(np.median(inner))


def measure(np, cv2, img, L, box, scale, txt=""):
    b = np.array(box, dtype=float)
    x0, y0 = np.floor(b.min(0)).astype(int) - 3
    x1, y1 = np.ceil(b.max(0)).astype(int) + 3
    x0, y0 = max(0, x0), max(0, y0)
    P = L[y0:y1, x0:x1]
    if P.size < 20:
        return None
    # the background is what surrounds the words (the box's padded border); the ink is whatever differs from it
    # by more than half of the strongest difference, measured as a contrast ratio
    edge = np.concatenate([P[:2].ravel(), P[-2:].ravel(), P[:, :2].ravel(), P[:, -2:].ravel()])
    first = _read(np, cv2, P, float(np.median(edge)), y1 - y0, scale, txt)
    # Second look, only for a text that fails: when the OCR box's border runs along a chip's or cell's outline (or a
    # tilted stamp leaves the ground in the box's corners), the border is not the ground the glyphs stand on, and the
    # "ink" found against it is the chip's fill (a dark "dst = 3" on a pale chip with a green outline read 2.84:1 at
    # 60 px). The ground the glyphs stand on is then found inside the box: split its pixels in two (Otsu) and take the
    # half that survives an erosion best (glyph strokes are thin; the ground they stand on is not). When that ground
    # differs from the border by more than 1.25:1, the text is measured against it.
    inner = P[3:-3, 3:-3]
    if first and inner.size >= 20 and (first[0] < 4.5 or first[1] < 26):
        bg2 = _ground(np, cv2, inner)
        bg1 = float(np.median(edge))
        if (max(bg1, bg2) + 0.05) / (min(bg1, bg2) + 0.05) > 1.25:
            second = _read(np, cv2, P, bg2, y1 - y0, scale, txt)
            if second:
                first = second
    if not first:
        return None
    contrast, px = first
    return {"px": round(px, 1), "contrast": round(contrast, 2), "box": [int(x0), int(y0), int(x1), int(y1)]}


def counted(txt, conf, conf_min=0.7, conf_single=0.85):
    """Whether an OCR result is measured. Every text with a letter or digit counts, single characters included,
    when the OCR is sure of it; anything it half-recognised (a shape read as a letter at low confidence) does not."""
    alnum = sum(ch.isalnum() for ch in txt)
    return alnum > 0 and float(conf) >= (conf_min if alnum >= 2 else conf_single)


def judge(px, contrast, min_px=26, min_cr=4.5, min_cr_large=None, large_px=32):
    """(fails, close calls) for one measured text. A miss is a miss: there is no tolerance below a rule. Within TOL
    above a rule the text is a close call, because the measurement is good to about 4%."""
    min_cr_large = min_cr if min_cr_large is None else min_cr_large
    need_cr = min_cr_large if px >= large_px else min_cr
    why, near = [], []
    if px < min_px:
        why.append(f"{px:.0f} px < {min_px:g}")
    elif px < min_px * (1 + TOL):
        near.append(f"{px:.1f} px, just over {min_px:g}")
    if contrast < need_cr:
        why.append(f"contrast {contrast}:1 < {need_cr:g}")
    elif contrast < need_cr * (1 + TOL):
        near.append(f"contrast {contrast}:1, just over {need_cr:g}")
    return why, near


def on_footage(box, fp):
    """Whether a text box ([x0, y0, x1, y1]) is the recording's own text: its centre inside one of the footage rects,
    and not the film's own text drawn over the footage ("keep" rects: a text with three quarters of its box inside
    one is the film's; a recorded label peeking out from under a note is still the recording's). Rects are
    [x, y, w, h], frame px."""
    if not fp:
        return False
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    hit = lambda r: r[0] <= cx <= r[0] + r[2] and r[1] <= cy <= r[1] + r[3]  # noqa: E731
    area = max(1.0, (box[2] - box[0]) * (box[3] - box[1]))

    def inside(r):
        w = min(box[2], r[0] + r[2]) - max(box[0], r[0])
        h = min(box[3], r[1] + r[3]) - max(box[1], r[1])
        return w > 0 and h > 0 and w * h / area >= 0.75
    return any(hit(r) for r in fp.get("rects", [])) and not any(inside(r) for r in fp.get("keep", []))


def sidecar(path):
    """The footage report capture.mjs writes beside a still (<still>.footage.json), or None."""
    side = os.path.splitext(path)[0] + ".footage.json"
    return json.load(open(side)) if os.path.exists(side) else None


def map_at(fmap, t):
    """The footage report nearest to time t in a --footage map (capture.mjs --footage-map)."""
    if not fmap or not fmap.get("frames"):
        return None
    fr = fmap["frames"]
    k = min(len(fr) - 1, max(0, int(round(t / fmap["step"]))))
    return min(fr[max(0, k - 1):k + 2], key=lambda f: abs(f["t"] - t))


def check(paths, min_px, min_cr, min_cr_large=None, large_px=32, conf_min=0.7, conf_single=0.85, footage=None):
    """footage: a list of footage reports, one per path (or None each): texts on footage are listed apart."""
    min_cr_large = min_cr if min_cr_large is None else min_cr_large
    np = need("numpy")
    need("rapidocr_onnxruntime", "rapidocr-onnxruntime==1.2.3")
    cv2 = need("cv2", "opencv-python")
    from rapidocr_onnxruntime import RapidOCR
    eng = RapidOCR()
    out = []
    for i, p in enumerate(paths):
        fp = footage[i] if footage else None
        img = cv2.imread(p)[:, :, ::-1].astype(np.float64)
        L = lum(np, img)
        scale = 1080.0 / min(img.shape[0], img.shape[1])  # the short side: a 9:16 Short is 1080 wide
        res, _ = eng(p)
        items = []
        for box, txt, conf in res or []:
            if not counted(txt, conf, conf_min, conf_single):
                continue
            m = measure(np, cv2, img, L, box, scale, txt)
            if not m:
                continue
            why, near = judge(m["px"], m["contrast"], min_px, min_cr, min_cr_large, large_px)
            if on_footage(m["box"], fp):
                items.append(dict(m, text=txt, conf=round(float(conf), 2), fail=[], near=[], footage=why or ["meets the rules"]))
            else:
                items.append(dict(m, text=txt, conf=round(float(conf), 2), fail=why, near=near))
        out.append({"image": p, "height": img.shape[0], "texts": items, "fails": [t for t in items if t["fail"]],
                    "footage": [t for t in items if t.get("footage")]})
    return out


def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    area = lambda r: max(1, (r[2] - r[0]) * (r[3] - r[1]))
    return inter / float(area(a) + area(b) - inter)


def same_words(a, b):
    """OCR of one text varies a little from frame to frame (a fade drops a letter); two different texts do not
    read alike. A caption swap can read almost alike, though ("Step 1" then "Step 2", "Part A" then "Part B"), so
    texts whose numbers or lone capitals differ, one for one, are two texts; a label OCR dropped is still tolerated."""
    import difflib
    import re
    labels = lambda s: re.findall(r"(?<!\w)(?:\d+(?:[.,:]\d+)*|[A-Z])(?!\w)", str(s))  # noqa: E731
    la, lb = labels(a), labels(b)
    if len(la) == len(lb) and la != lb:
        return False
    norm = lambda s: " ".join(str(s).lower().split())  # noqa: E731
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio() >= 0.6


def dwell(report, times, step, min_dwell):
    """Follow each failing text through consecutive frames (the same text in the same place: boxes overlap by
    IoU >= 0.3 and the words read alike, or the same words within 60 px) and return its runs as {text, start, end, frames, worst}. A text that pops, fades or flies
    is under the bar for a frame or two and that is motion; a run of `min_dwell` seconds or more is a text a viewer
    is asked to read while it is unreadable."""
    runs, open_ = [], []
    for k, r in enumerate(report):
        nxt = []
        for t in r["fails"]:
            hit = None
            for o in open_:
                close = (t["text"] == o["text"] and abs(t["box"][0] - o["box"][0]) < 60 and abs(t["box"][1] - o["box"][1]) < 60)
                # overlap alone is not enough: one caption fading out where the next fades in is two texts
                if o["last"] == k - 1 and ((iou(t["box"], o["box"]) >= 0.3 and same_words(t["text"], o["text"])) or close):
                    hit = o
                    break
            if hit:
                open_.remove(hit)
                hit.update(last=k, box=t["box"], frames=hit["frames"] + 1)
                hit["worst"] = (min(hit["worst"][0], t["px"]), min(hit["worst"][1], t["contrast"]))  # each on its own
                nxt.append(hit)
            else:
                nxt.append({"text": t["text"], "box": t["box"], "first": k, "last": k, "frames": 1,
                            "worst": (t["px"], t["contrast"]), "why": t["fail"]})
        runs += [o for o in open_ if o not in nxt]
        open_ = nxt
    runs += open_
    out = []
    for o in runs:
        span = (o["last"] - o["first"] + 1) * step
        out.append({"text": o["text"], "start": round(times[o["first"]], 2), "end": round(times[o["last"]] + step, 2),
                    "seconds": round(span, 2), "frames": o["frames"], "box": o["box"], "why": o["why"],
                    "worst_px": round(o["worst"][0], 1), "worst_contrast": o["worst"][1], "long": span >= min_dwell - 1e-6})
    return sorted(out, key=lambda o: (-o["seconds"], o["start"]))


def sample(video, fps, outdir, start=None, end=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(start)] if start is not None else []) + ["-i", video]
    if end is not None:
        cmd += ["-t", str(end - (start or 0))]
    # PNG, not JPEG: JPEG's 4:2:0 chroma blurs coloured text into its ground (a 5.16:1 label measured 4.39:1)
    cmd += ["-vf", f"fps={fps}", os.path.join(outdir, "f%05d.png")]
    subprocess.run(cmd, check=True)
    paths = sorted(glob.glob(os.path.join(outdir, "f*.png")))
    t0 = start or 0.0
    return paths, [t0 + (i + 0.5) / fps for i in range(len(paths))]


def mark(cv2, report, outdir):
    os.makedirs(outdir, exist_ok=True)
    for r in report:
        img = cv2.imread(r["image"])
        for fr in (r.get("footage_rects") or []):
            x, y, w, h = [int(round(v)) for v in fr]
            cv2.rectangle(img, (x, y), (x + w, y + h), (160, 160, 160), 1)
        for t in r["texts"]:
            x0, y0, x1, y1 = t["box"]
            if t.get("footage"):  # the recording's own text: grey, not judged
                cv2.rectangle(img, (x0, y0), (x1, y1), (150, 150, 150), 1)
                continue
            col = (40, 40, 235) if t["fail"] else (0, 200, 255) if t.get("near") else (90, 200, 90)
            cv2.rectangle(img, (x0, y0), (x1, y1), col, 2)
            if t["fail"] or t.get("near"):
                lab = f"{t['px']:.0f}px {t['contrast']}:1"
                cv2.putText(img, lab, (x0, max(14, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(img, lab, (x0, max(14, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 80, 255), 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(outdir, os.path.splitext(os.path.basename(r["image"]))[0] + ".jpg"), img,
                    [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="*")
    ap.add_argument("--project")
    ap.add_argument("--video")
    ap.add_argument("--every", type=float, default=5.0)
    ap.add_argument("--min-px", type=float, default=26)
    ap.add_argument("--min-contrast", type=float, default=4.5)
    ap.add_argument("--min-contrast-large", type=float, default=None,
                    help="contrast for text of --large-px and more (default: the same 4.5; the gate accepts nothing lower)")
    ap.add_argument("--large-px", type=float, default=32)
    ap.add_argument("--fps", type=float, default=None,
                    help="with --video: sample this many frames a second and follow each failing text from frame to frame")
    ap.add_argument("--dwell", type=float, default=0.5,
                    help="with --fps: a text under the bar for this long or longer fails (default 0.5 s)")
    ap.add_argument("--footage", default=None,
                    help="with --video --fps: a footage map (capture.mjs --footage-map); texts on recorded footage are listed apart")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    a = ap.parse_args()
    tmp = None
    stills = None
    if a.project:
        root = os.path.abspath(a.project)
        cfg = json.load(open(os.path.join(root, ".video-state.json"))).get("config", {})
        stills = os.path.join(root, cfg.get("stills", "stills"))
        paths = vstate.still_images(stills)  # the same set the visuals gate counts
        pr = vstate.Project(root)
        pr.load()
        # what this check covers, by content: the gate holds it against the stills and the scene source it sees
        covers = {"source_hash": vstate.source_hash(pr), "stills_hash": vstate.files_hash(paths)}
    elif a.video and a.fps:
        tmp = tempfile.mkdtemp(prefix="legib-")
        paths, times = sample(a.video, a.fps, tmp)
        fmap = json.load(open(a.footage)) if a.footage else None
        rep = check(paths, a.min_px, a.min_contrast, a.min_contrast_large, a.large_px,
                    footage=[map_at(fmap, t) for t in times] if fmap else None)
        runs = dwell(rep, times, 1.0 / a.fps, a.dwell)
        long_ = [o for o in runs if o["long"]]
        for o in runs:
            tag = "FAIL" if o["long"] else "motion"
            print(f"  {tag:6s} {o['start']:6.2f}-{o['end']:6.2f}s ({o['seconds']:.2f} s, {o['frames']} frames) "
                  f"worst {o['worst_px']:.0f} px {o['worst_contrast']}:1  \"{o['text'][:50]}\"")
        print(f"\n{len(paths)} frames at {a.fps:g} fps; {len(runs)} texts dip under the bar; "
              f"{len(long_)} stay under it {a.dwell:g} s or longer")
        if a.json:
            print(json.dumps(runs, indent=1))
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(1 if long_ else 0)
    elif a.video:
        tmp = tempfile.mkdtemp(prefix="legib-")
        subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"fps=1/{a.every}",
                        os.path.join(tmp, "t%04d.png")], check=True)   # PNG: see sample()
        paths = sorted(glob.glob(os.path.join(tmp, "*.png")))
    else:
        paths = a.images
    if not paths:
        sys.exit("no images to check")
    fps_ = [sidecar(p) for p in paths] if not a.video else None
    rep = check(paths, a.min_px, a.min_contrast, a.min_contrast_large, a.large_px,
                footage=fps_ if fps_ and any(fps_) else None)
    for r, fp in zip(rep, fps_ or []):
        if fp:
            r["footage_rects"] = fp.get("rects", [])
    nfail = sum(len(r["fails"]) for r in rep)
    nfoot = sum(len(r.get("footage", [])) for r in rep)
    for r in rep:
        name = os.path.basename(r["image"])
        if a.video:
            name = f"t={(int(name[1:5]) - 1) * a.every:.0f}s"
        near = [t for t in r["texts"] if t.get("near") and not t["fail"]]
        print(f"{name}: {len(r['texts'])} texts, {len(r['fails'])} failing, {len(near)} close calls"
              + (f", {len(r['footage'])} on recorded footage" if r.get("footage") else ""))
        for t in r["fails"]:
            print(f"    FAIL {', '.join(t['fail']):34s} \"{t['text'][:60]}\"")
        for t in near:
            print(f"    near {', '.join(t['near']):34s} \"{t['text'][:60]}\"")
    own = sorted(t["px"] for r in rep for t in r["texts"] if not t.get("footage"))
    print(f"\n{sum(len(r['texts']) for r in rep)} texts in {len(rep)} images; {nfail} break a rule"
          + (f"; smallest {own[0]:.0f} px" if own else ""))
    if nfoot:
        under = sum(1 for r in rep for t in r.get("footage", []) if t["footage"] != ["meets the rules"])
        print(f"{nfoot} texts are the product's recorded interface (grey boxes, not counted; {under} of them under the bar "
              f"at this size): make sure each line's point is said in the film's own text or pushed in on")
    if a.json:
        print(json.dumps(rep, indent=1))
    if stills:
        import cv2
        mark(cv2, rep, os.path.join(stills, "legibility"))
        newest = max(os.path.getmtime(p) for p in paths)
        json.dump({"checked_at": time.time(), "newest_still": newest, "images": len(paths), "fails": nfail,
                   "footage_texts": nfoot, **covers,
                   "rules": {"min_px": a.min_px, "min_contrast": a.min_contrast, "large_px": a.large_px,
                             "min_contrast_large": a.min_contrast_large if a.min_contrast_large is not None else a.min_contrast,
                             "tolerance": 0},
                   "report": rep}, open(os.path.join(stills, "legibility.json"), "w"), indent=1)
        print(f"marked copies in {os.path.join(stills, 'legibility')}/ (red = breaks a rule, amber = close call); open them")
    sys.exit(1 if nfail else 0)


if __name__ == "__main__":
    main()
