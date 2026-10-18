"""Visual gate: Playwright screenshots (390/1440 x light/dark), layout, contrast, fonts, alt text,
outbound requests, tesseract OCR plus a lining-figure geometry check of every value and number cell,
and key-node visibility (AC-3.2..3.6; D20.3).

One browser run per call (E12). Any request that is not local is aborted and fails the gate.
"""
import functools
import http.server
import json
import math
import os
import re
import threading
from pathlib import Path

from .. import errors, fonts, host, node
from ..text import esc

ALLOWED_FAMILIES = {"Source Serif 4", "Nunito Sans", "JetBrains Mono", "Caveat"}
WIDTHS = (390, 1440)
SCHEMES = ("light", "dark")


def shoot(jobs, work, lesson_sha=None, timeout=900):
    work.mkdir(parents=True, exist_ok=True)
    jp, rp = work / "jobs.json", work / "results.json"
    jp.write_text(json.dumps(jobs, indent=1))
    node.run_script("shoot.mjs", [jp, rp], timeout=timeout, lesson_sha256=lesson_sha)
    return json.loads(rp.read_text())


# ---------------------------------------------------------------- local server (loopback only)

class _RangeHandler(http.server.SimpleHTTPRequestHandler):
    """Static files with byte ranges, so <video> can seek."""

    def log_message(self, *a):
        return

    def send_head(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        size = os.path.getsize(path)
        start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2) or 0))
        end = int(m.group(2)) if m.group(1) and m.group(2) else size - 1
        end = min(end, size - 1)
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self._range_left = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        left = getattr(self, "_range_left", None)
        if left is None:
            return super().copyfile(source, outputfile)
        while left > 0:
            chunk = source.read(min(65536, left))
            if not chunk:
                break
            outputfile.write(chunk)
            left -= len(chunk)
        self._range_left = None


class _QuietServer(http.server.ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        return  # the browser drops range connections on seek; that is not an error


class LocalServer:
    def __init__(self, root):
        handler = functools.partial(_RangeHandler, directory=str(root))
        handler.extensions_map = {**_RangeHandler.extensions_map, ".vtt": "text/vtt", ".mp4": "video/mp4",
                                  ".svg": "image/svg+xml", ".mjs": "text/javascript"}
        self.httpd = _QuietServer(("127.0.0.1", 0), handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


# ---------------------------------------------------------------- OCR

def ocr_crops(crops):
    """Tesseract each crop after grayscale (+ negate for dark themes) and a white margin.
    Grouped crops (a column) are read as a block and compared token by token. Crops whose expected
    text holds digits also get the lining-figure geometry check (AC-3.2)."""
    tess = host.which("tesseract")
    ffmpeg = host.which("ffmpeg")
    out = []
    for c in crops:
        exp = c["expected"]
        prep = c["path"].replace(".png", ".prep.png")
        vf = "format=gray" + (",negate" if c.get("dark") else "") + ",eq=contrast=2.2:brightness=0.25,pad=iw+40:ih+40:20:20:white"
        host.run([ffmpeg, "-v", "error", "-y", "-i", c["path"], "-vf", vf, prep], check=True, timeout=60)
        psm = "6" if c.get("multi") else ("10" if len(exp) == 1 else "7")
        got = host.run([tess, prep, "-", "--psm", psm, "-l", "eng"], timeout=60).stdout.strip()
        read_ok = re.findall(r"\S+", got.lower()) == re.findall(r"\S+", exp.lower())
        lining = lining_check(c["path"], exp) if re.search(r"\d", exp) else None
        out.append({"expected": exp.replace("\n", " "), "read": got.replace("\n", " "), "read_ok": read_ok,
                    "lining": lining, "ok": read_ok and (lining is None or lining["ok"]),
                    "crop": "/".join(Path(c["path"]).parts[-2:]), "group": c.get("group")})
    return out


def _gray(png):
    """(width, height, bytes) of a PNG as 8-bit gray, through ffmpeg (no imaging library in the core venv)."""
    raw = png + ".gray"
    host.run([host.which("ffmpeg"), "-v", "error", "-y", "-i", png, "-pix_fmt", "gray", "-f", "rawvideo", raw],
             check=True, timeout=60)
    head = Path(png).read_bytes()[16:24]
    w, h = int.from_bytes(head[:4], "big"), int.from_bytes(head[4:], "big")
    data = Path(raw).read_bytes()
    Path(raw).unlink()
    return w, h, data


def _runs(flags, gap=1):
    """[(start, end)] of True runs, joining gaps of up to `gap` False entries."""
    out, start, last = [], None, None
    for i, f in enumerate(flags):
        if f:
            if start is None:
                start = i
            elif i - last > gap + 1:
                out.append((start, last))
                start = i
            last = i
    if start is not None:
        out.append((start, last))
    return out


def lining_check(png, expected, tol=0.12):
    """Lining figures share one height and one baseline; old-style figures do not (0 1 2 sit at x-height,
    3 4 5 7 9 descend). Segments the crop into rows and glyph columns, maps glyphs to the expected
    characters, then checks every digit's ink height against the tallest digit and every digit's top and
    bottom against the others on its row. A crop that cannot be segmented fails (it is not evidence)."""
    w, h, px = _gray(png)
    border = [px[i] for i in range(w)] + [px[(h - 1) * w + i] for i in range(w)]
    bg = sorted(border)[len(border) // 2]
    spread = max(abs(v - bg) for v in px) or 1
    m = 6  # the crop is padded 8 CSS px (24 px at 3x); ignore its rim, where a card border may show
    ink = [m <= i % w < w - m and m <= i // w < h - m and abs(v - bg) > spread * 0.45 for i, v in enumerate(px)]
    rows_exp = [r.replace(" ", "") for r in expected.split("\n") if r.strip()]
    row_runs = [r for r in _runs([any(ink[y * w:(y + 1) * w]) for y in range(h)], gap=1) if r[1] - r[0] >= 2]
    if len(row_runs) != len(rows_exp):
        return {"ok": False, "why": f"{len(row_runs)} ink rows for {len(rows_exp)} expected rows"}
    glyphs = []
    for (y0, y1), chars in zip(row_runs, rows_exp):
        cols = _runs([any(ink[y * w + x] for y in range(y0, y1 + 1)) for x in range(w)], gap=0)
        cols = [c for c in cols if c[1] - c[0] >= 1]
        if len(cols) != len(chars):
            return {"ok": False, "why": f"{len(cols)} glyphs for {chars!r}"}
        for (x0, x1), ch in zip(cols, chars):
            ys = [y for y in range(y0, y1 + 1) if any(ink[y * w + x] for x in range(x0, x1 + 1))]
            glyphs.append({"ch": ch, "row": y0, "top": ys[0], "bottom": ys[-1], "height": ys[-1] - ys[0] + 1})
    digits = [g for g in glyphs if g["ch"].isdigit()]
    tallest = max(g["height"] for g in digits)
    bad = []
    for g in digits:
        if g["height"] < tallest * (1 - tol):
            bad.append({"digit": g["ch"], "problem": "short", "height": g["height"], "tallest": tallest})
    for row in {g["row"] for g in digits}:
        on = [g for g in digits if g["row"] == row]
        for edge in ("top", "bottom"):
            vals = sorted(g[edge] for g in on)
            ref = vals[len(vals) // 2]
            bad += [{"digit": g["ch"], "problem": f"{edge} off the line", "by_px": g[edge] - ref}
                    for g in on if abs(g[edge] - ref) > tallest * tol]
    return {"ok": not bad, "digits": len(digits), "tallest_px": tallest, "bad": bad[:10]}


# ---------------------------------------------------------------- helpers

def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _lum(hexcol):
    lin = [(v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in _rgb(hexcol)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _lab_l(hexcol):
    y = _lum(hexcol)
    return 116 * y ** (1 / 3) - 16 if y > 216 / 24389 else 24389 / 27 * y


def contrast_ratio(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def token_contrast(tokens=None):
    """The role-pair table for both themes (STYLE.md prints it): WCAG ratios for the declared pairs and
    the L* separations (note vs correction in dark, V12)."""
    tk = tokens or fonts.tokens()
    rows, seps = [], []
    for theme, t in tk["themes"].items():
        for fg, bg, mn in tk["contrast_pairs"]:
            r = contrast_ratio(t[fg], t[bg])
            rows.append({"theme": theme, "fg": fg, "bg": bg, "fg_hex": t[fg], "bg_hex": t[bg], "ratio": round(r, 2),
                         "min": mn, "kind": "text" if mn >= 4.5 else "rule", "ok": r >= mn})
        for a, b, mn in tk.get("separation", {}).get(theme, []):
            d = abs(_lab_l(t[a]) - _lab_l(t[b]))
            seps.append({"theme": theme, "a": a, "b": b, "delta_L": round(d, 1), "min": mn, "ok": d >= mn})
    return rows, seps


def _families(lst):
    fams = set()
    for f in lst:
        for part in f.split(","):
            p = part.strip().strip('"').strip("'")
            if p:
                fams.add(p)
    return fams


def g(gid, medium, ok, measured, reason="", not_run=False):
    status = "not-run" if not_run else ("passed" if ok else "failed")
    return {"id": gid, "medium": medium, "status": status, "measured": measured, "reason": reason}


# ---------------------------------------------------------------- still

MEASURE_JS = host.PKG / "ptk" / "templates" / "svg" / "still-measure.js"
# where the viewer page shows each layout (still_viewer): portrait under 640 px, wide above
STILL_VIEWS = {"portrait": (390, 844), "wide": (1440, 900)}
STILL_DRAWS_NOT = {"question"}  # the still is the settled figure; a prediction question belongs to video / IVE


def still_viewer(out_dir, lesson_id, title):
    """A plain viewer page: portrait under 640 px, theme from prefers-color-scheme, never upscaled."""
    name = lambda lay, th: f"{lesson_id}-{lay}-{th}.svg"
    t = fonts.tokens()["themes"]
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>html,body{{margin:0;background:{t['light']['ground']}}}img{{display:block;width:100%;max-width:1200px;height:auto;margin:0 auto}}
@media (max-width: 640px){{img{{max-width:400px}}}}
@media (prefers-color-scheme: dark){{html,body{{background:{t['dark']['ground']}}}}}</style></head>
<body><picture>
<source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="{name('portrait', 'dark')}">
<source media="(max-width: 640px)" srcset="{name('portrait', 'light')}">
<source media="(prefers-color-scheme: dark)" srcset="{name('wide', 'dark')}">
<img src="{name('wide', 'light')}" alt="{esc(title)}">
</picture></body></html>
"""
    (out_dir / "index.html").write_text(html)
    return out_dir / "index.html"


def make_pngs(out_dir, svgs, lesson_sha):
    """2x PNG of each SVG. A request that leaves the machine fails the build here (AC-3.6)."""
    jobs = [{"id": f"png:{s}", "type": "png", "url": (out_dir / s).resolve().as_uri(),
             "out": str((out_dir / s).with_suffix(".png")), "scale": 2,
             "width": 1200 if "-wide-" in s else 400, "height": 1000} for s in svgs]
    res = shoot(jobs, out_dir.parent / "work" / "still-png", lesson_sha)
    if res["outbound"]:
        raise errors.OutboundRequest("the still tried to reach the network during PNG export",
                                     requests=res["outbound"][:20])
    failed = [r for r in res["results"] if not r["ok"]]
    return [s.replace(".svg", ".png") for s in svgs], failed, res["outbound"]


def required_keys(lesson):
    """Key nodes every still variant must show fully (D20.3): the storyboard's key_nodes and the figure's
    own elements, less what a still never draws."""
    from .. import model
    fig = lesson.data.get("figure") or {}
    keys = {"code", "output"} | ({"note"} if fig.get("notes") else set()) | ({"compare"} if fig.get("compare") else set())
    keys |= set(fig.get("elements", []))
    for sc in lesson.data.get("storyboard", []):
        keys |= set(sc.get("key_nodes", []))
    known = set(model.FIGURE_ELEMENTS.get(fig.get("kind"), ())) | set(fig.get("elements", []))
    return sorted(k for k in keys - STILL_DRAWS_NOT if k in known)


def measure_jobs(out_dir, svgs, keys):
    js = MEASURE_JS.read_text().strip().rstrip(";")
    jobs = []
    for s in svgs:
        w, h = STILL_VIEWS["wide" if "-wide-" in s else "portrait"]
        opts = json.dumps({"minPx": 11, "keys": keys})
        jobs.append({"id": f"measure:{s}", "type": "script", "url": (out_dir / s).resolve().as_uri(), "width": w,
                     "height": h, "steps": [{"eval": f"({js})({opts})", "as": "m"}]})
    return jobs


def measure_svgs(out_dir, svgs, keys, lesson_sha=None):
    """{svg: in-page measurement} at each layout's viewer width, plus the outbound requests seen."""
    res = shoot(measure_jobs(out_dir, svgs, keys), out_dir / "work-measure", lesson_sha)
    R = {r["id"]: r for r in res["results"]}
    return {s: (R[f"measure:{s}"].get("values") or {}).get("m") or {"error": R[f"measure:{s}"].get("error")}
            for s in svgs}, res["outbound"]


def still_gates(lesson, out_dir, svgs):
    sha = lesson.sha256()
    work = out_dir.parent / "work" / "still-visual"
    viewer = still_viewer(out_dir, lesson.id, lesson.data["title"])
    keys = required_keys(lesson)
    jobs = measure_jobs(out_dir, svgs, keys)
    for s in svgs:
        wide = "-wide-" in s
        jobs.append({"id": f"ocr:{s}", "type": "ocr-crops", "url": (out_dir / s).resolve().as_uri(),
                     "width": 1200 if wide else 400, "height": 3000, "scale": 3,
                     "outDir": str(work / "ocr" / s.replace(".svg", ""))})
    for w in WIDTHS:
        for sc in SCHEMES:
            jobs.append({"id": f"shot:{w}:{sc}", "type": "shot", "url": viewer.resolve().as_uri(), "width": w,
                         "height": 900, "scheme": sc, "shot": str(out_dir.parent / "shots" / f"still-{w}-{sc}.png")})
    res = shoot(jobs, work, sha)
    return still_gates_from(lesson, svgs, res, keys)


def still_gates_from(lesson, svgs, res, keys):
    R = {r["id"]: r for r in res["results"]}
    errs = [{"job": r["id"], "error": r.get("error", "")[:400]} for r in res["results"] if not r["ok"]]
    M = {s: (R.get(f"measure:{s}", {}).get("values") or {}).get("m") for s in svgs}
    gates = []

    layout, keyp, numeric, contrast, fams, faces, alt, tones = [], [], [], [], set(), set(), [], {}
    for s, m in M.items():
        if not m:
            layout.append({"svg": s, "kind": "measure-failed"})
            continue
        for p in m["problems"]:
            bucket = keyp if p["kind"].startswith("key-node") else numeric if p["kind"] == "numeric" else layout
            bucket.append({**p, "svg": s})
        contrast += [{**c, "svg": s} for c in m["contrast"]]
        fams |= _families(m["fonts"])
        faces |= set(m["loadedFaces"])
        alt.append({"svg": s, "title": bool(m["title"].strip()), "desc_chars": len(m["desc"].strip()),
                    "source_link": m["source"]})
        tones[s] = m["tones"]
    pages = []
    for w in WIDTHS:
        for sc in SCHEMES:
            r = R.get(f"shot:{w}:{sc}", {})
            pm = r.get("measure", {"problems": [{"kind": "job-failed"}]})
            pages.append({"width": w, "scheme": sc, "problems": pm["problems"], "images_loaded": r.get("imagesLoaded"),
                          "shot": f"shots/still-{w}-{sc}.png"})
    page_bad = [p for p in pages if p["problems"] or not p["images_loaded"]]
    min_px = min((m["minPx"] for m in M.values() if m), default=0)
    gates.append(g("visual.still.layout", "still", not layout and not page_bad and not errs,
                   {"views": {s: {"viewport": m["viewport"], "shown_width": m["shown_width"]} for s, m in M.items() if m},
                    "svg_problems": layout[:30], "pages": pages, "min_text_px_at_display": round(min_px, 2),
                    "job_errors": errs},
                   "" if not layout and not page_bad and not errs else "overflow, overlap or text under 11 px"))
    gates.append(g("visual.still.key-nodes", "still", bool(keys) and not keyp and all(M.values()),
                   {"required": keys, "problems": keyp[:30],
                    "nodes": {s: m["keys"] for s, m in M.items() if m}},
                   "" if not keyp else "a key node is cut off, missing or taller than the screen (D20.3)"))
    low = [c for c in contrast if c["ratio"] < c["min"]]
    table, seps = token_contrast()
    tok_bad = [r for r in table if not r["ok"]] + [s for s in seps if not s["ok"]]
    tone_dl = {s: min(abs(a - b) for a in tn["note"] for b in tn["correction"]) for s, tn in tones.items()
               if tn["note"] and tn["correction"]}
    dark_dl = [d for s, d in tone_dl.items() if "-dark" in s]
    tone_ok = bool(dark_dl) and len(tone_dl) == len(svgs) and min(tone_dl.values()) >= 15
    text_min = min((c["ratio"] for c in contrast if c["kind"] == "text"), default=0)
    rule_min = min((c["ratio"] for c in contrast if c["kind"] == "rule"), default=0)
    gates.append(g("visual.still.contrast", "still", bool(contrast) and not low and not tok_bad and tone_ok,
                   {"pairs_checked": len(contrast), "below_minimum": low[:20], "min_text_ratio": text_min,
                    "min_rule_ratio": rule_min, "dark_note_correction_delta_L": round(min(dark_dl), 1) if dark_dl else None,
                    "note_correction_delta_L": {s: round(d, 1) for s, d in tone_dl.items()},
                    "token_pairs": len(table), "token_failures": tok_bad},
                   "" if not low and not tok_bad and tone_ok else "contrast or note/correction lightness below minimum"))
    crops = []
    for s in svgs:
        crops += [{**c, "svg": s, "dark": "-dark" in s} for c in R.get(f"ocr:{s}", {}).get("crops", [])]
    ocr = ocr_crops(crops) if crops else []
    bad_ocr = [o for o in ocr if not o["ok"]]
    gates.append(g("visual.still.ocr", "still", bool(ocr) and not bad_ocr and not numeric,
                   {"cells": len(ocr), "digit_cells_lining_checked": sum(1 for o in ocr if o["lining"]),
                    "misread_or_not_lining": bad_ocr[:20], "numeric_style_problems": numeric[:10],
                    "engine": host.tool_version("tesseract")},
                   "" if not bad_ocr and not numeric else "OCR misread, or figures are not lining tabular"))
    extra = fams - ALLOWED_FAMILIES
    gates.append(g("visual.still.fonts", "still", not extra and bool(faces) and faces <= ALLOWED_FAMILIES,
                   {"families_used": sorted(fams), "faces_loaded": sorted(faces), "not_bundled": sorted(extra)}))
    alt_ok = all(a["title"] and a["desc_chars"] > 40 and a["source_link"] for a in alt) and len(alt) == len(svgs)
    gates.append(g("visual.still.alt-source", "still", alt_ok, {"svgs": alt}))
    gates.append(g("visual.still.network", "still", not res["outbound"], {"outbound_requests": res["outbound"]},
                   "OutboundRequest" if res["outbound"] else ""))
    return gates


# ---------------------------------------------------------------- IVE (AC-6.1..6.7)

IVE_DRIVE = host.PKG / "ptk" / "templates" / "ive" / "drive.js"
NAV_ACTIONS = {"open", "seek", "chapter", "replay", "reveal", "flip", "explore", "return", "close"}
NAV_KEYS = {"schema_version", "event_type", "event_id", "action", "artifact_id", "session_id", "position", "timestamp"}


def _pause_points(c):
    """Just after the cue starts (1.5 frames), the old WP0 point, and just before it ends."""
    span = c["end"] - c["start"]
    pts = [c["start"] + min(0.05, span / 3), c["start"] + min(0.2, span / 2), c["end"] - min(0.05, span / 3)]
    return sorted({round(t, 3) for t in pts})


def vtt_start(c):
    """A cue start as the browser reads it from the .vtt file (millisecond precision)."""
    return float(f"{c['start']:.3f}")


def resolve(starts, t, fps):
    """The page's clock rule (ive.js windowAt), for expected values: the last window whose start is
    less than one frame after t, in integer microseconds."""
    frame_us, T, k = int(1e6 / fps), round(t * 1e6), -1
    for i, s in enumerate(starts):
        if round(s * 1e6) - T < frame_us:
            k = i
    return k


def boundary_seeks(cue_list, fps):
    """Seek targets around every cue boundary b (D20.6): b - 1 ms, b, b + 1 ms, the browser's
    microsecond-truncated b - 1 us, b floored to the frame grid, and the edges of the one-frame
    tolerance itself (b - 1/fps +- 1 ms), with the window each must resolve to."""
    starts = [vtt_start(c) for c in cue_list]
    frame = 1 / fps
    rows = []
    for i in range(1, len(cue_list)):
        b, lo, hi = starts[i], starts[i - 1], (starts[i + 1] if i + 1 < len(starts) else cue_list[-1]["end"])
        cand = [("b-1ms", b - 0.001), ("b", b), ("b+1ms", b + 0.001), ("b-1us", math.floor(b * 1e6) / 1e6 - 1e-6),
                ("frame-floor", math.floor(b * fps + 1e-9) / fps), ("inside-tolerance", b - frame + 0.001),
                ("outside-tolerance", b - frame - 0.001)]
        for name, t in cand:
            if lo + 0.002 < t < hi - 0.002:
                rows.append({"boundary": cue_list[i]["cue"], "at": name, "t": round(t, 6),
                             "expected": cue_list[resolve(starts, t, fps)]["cue"],
                             "strict_half_open": cue_list[max(k for k, s in enumerate(starts) if s <= t)]["cue"]})
    return rows


def _js(expr):
    return {"eval": f"(async () => {{ const D = window.__iveDrive; {expr} }})()"}


def ive_gates(lesson, ive_dir, cue_list, timing):
    """Every IVE check runs on the page opened from disk (file://, AC-6.7)."""
    sha = lesson.sha256()
    work = ive_dir.parent / "work" / "ive"
    shots = ive_dir.parent / "shots"
    gates = []
    fps = timing["fps"]
    url = (ive_dir / "index.html").resolve().as_uri()
    drive = {"eval": IVE_DRIVE.read_text(), "as": "drive"}
    ready = {"waitFor": "window.__ptkReady && window.__ptkReady()", "timeout": 30000}
    answer_cues = [c for c in cue_list if c["kind"] == "answer"]
    # pause / seek: every cue at three points; then the boundary seeks; then each chapter
    steps = [ready, drive]
    for c in cue_list:
        for t in _pause_points(c):
            steps.append({**_js(f"return D.seek({t:.3f});"), "as": f"seek:{c['cue']}@{t:.3f}"})
    bseeks = boundary_seeks(cue_list, fps)
    for i, b in enumerate(bseeks):
        steps.append({**_js(f"const s = await D.seek({b['t']:.6f}); return {{...s, resolved: window.__ptkIve.resolve(s.t)}};"),
                      "as": f"boundary:{i}"})
    steps.append({**_js("const out = []; for (const b of document.querySelectorAll('#chapters button')) { "
                        "const p = D.once(D.v(), 'seeked'); b.click(); await p; await D.sleep(60); "
                        "out.push({...D.state(), current: b.getAttribute('aria-current')}); } return out;"), "as": "chapters"})
    steps.append({**_js("const v = D.v(); await D.seek(v.duration - 0.05); const n = document.querySelectorAll('#tx li').length; "
                        "const p = D.once(v, 'seeked'); document.querySelector('#tx li button').click(); await p; "
                        "const caps = [...v.textTracks].find((t) => t.kind === 'captions'); const cb = document.getElementById('caps'); "
                        "const m0 = caps.mode; cb.click(); const m1 = caps.mode; cb.click(); const m2 = caps.mode; "
                        "return {transcript_items_at_end: n, seek_after_click: v.currentTime, caption_modes: [m0, m1, m2], "
                        "chapters: document.querySelectorAll('#chapters li').length, readyState: v.readyState, "
                        "error: v.error && v.error.code, nav: window.__ptkNav};"), "as": "controls"})
    jobs = [{"id": "ive-behaviour", "type": "script", "url": url, "width": 1440, "height": 1000, "steps": steps}]
    # the no-answer leak: paused (EXPLORE) 0.1 s before each answer cue
    for c in answer_cues:
        sc = next(s for s in timing["scenes"] if s["id"] == c["answer_for"])
        words = [w.strip().lower() for w in lesson.fact(sc["question"]["answer_fact"])["value"].split("\n") if w.strip()]
        jobs.append({"id": f"ive-leak:{c['cue']}", "type": "script", "url": url, "width": 1440, "height": 1000, "steps": [
            ready, drive, _js(f"await D.seek({c['start'] - 0.1:.3f}); document.getElementById('explore').click(); await D.sleep(80); await D.frame(); return 1;"),
            {**_js(f"return D.leak({json.dumps(words)});"), "as": "leak"},
            {"shot": str(shots / f"ive-before-answer-{c['cue']}.png"), "full": True}]})
    # FILM / EXPLORE / RETURN (AC-6.6), from a moment after every question is answered
    film_cue = next((c for c in cue_list if c["kind"] == "state" and len(c["state"]["output"]) >= 2), cue_list[-1])
    t_film = round(min(film_cue["start"] + 0.5, film_cue["end"] - 0.1), 3)
    flow = [ready, drive,
            {**_js(f"await D.seek({t_film}); return D.state();"), "as": "film"},
            {**_js("const v = D.v(); await v.play(); await D.sleep(400); document.getElementById('explore').click(); "
                   "await D.sleep(80); return {...D.state(), returnTime: window.__ptkIve.returnTime(), "
                   "expected_cue: window.__ptkIve.resolve(window.__ptkIve.returnTime())};"), "as": "explore"},
            {**_js("const r = document.querySelector('#live-n input[value=\"3\"]'); if (r) r.click(); "
                   "const b = document.getElementById('live-brk'); if (b) b.click(); await D.sleep(60); return D.state();"), "as": "edited"},
            {**_js("const v = D.v(); const p = D.once(v, 'playing'); document.getElementById('return').click(); await p; "
                   "await D.sleep(150); const r = window.__ptkNav.filter((e) => e.action === 'return').pop(); "
                   "return {...D.state(), return_position: r && r.position, returnTime: window.__ptkIve.returnTime(), "
                   "film_cue: window.__ptkIve.resolve(v.currentTime), edits_left: document.querySelectorAll('[data-edit], .nval.changed').length};"),
             "as": "returned"},
            {**_js("const v = D.v(); v.pause(); await D.sleep(80); const brk = document.getElementById('live-brk'); "
                   "const n = document.querySelector('#live-n input:checked'); "
                   "return {...D.state(), n_checked: n && n.value, brk_pressed: brk && brk.getAttribute('aria-pressed')};"), "as": "repaused"},
            {**_js("return window.__ptkNav;"), "as": "nav"}]
    jobs.append({"id": "ive-explore", "type": "script", "url": url, "width": 1440, "height": 1000, "steps": flow})
    # file:// (AC-6.7): every track loaded, the MP4 decodes
    jobs.append({"id": "ive-files", "type": "script", "url": url, "width": 1440, "height": 900, "steps": [
        ready, drive, {**_js("const v = D.v(); await D.seek(1.0); await D.frame(); return {protocol: location.protocol, "
                             "tracks: D.tracks(), track_src: [...document.querySelectorAll('track')].map((t) => t.src.split(':')[0]), "
                             "readyState: v.readyState, error: v.error && v.error.code, duration: v.duration, "
                             "h264: v.canPlayType('video/mp4; codecs=\"avc1.640028\"')};"), "as": "files"}]})
    # screenshots and layout: FILM and EXPLORE (with an edit) at each width and scheme
    for w in WIDTHS:
        for scn in SCHEMES:
            jobs.append({"id": f"ive-shot:{w}:{scn}", "type": "script", "url": url, "width": w, "height": 900, "scheme": scn,
                         "steps": [ready, drive, _js(f"await D.seek({t_film}); await D.frame(); return 1;"),
                                   {**_js("return D.layout();"), "as": "film_layout"},
                                   {"shot": str(shots / f"ive-{w}-{scn}.png"), "full": True},
                                   _js("document.getElementById('explore').click(); await D.sleep(60); "
                                       "const r = document.querySelector('#live-n input[value=\"3\"]'); if (r) r.click(); "
                                       "await D.sleep(60); await D.frame(); return 1;"),
                                   {**_js("return D.layout();"), "as": "explore_layout"},
                                   {"shot": str(shots / f"ive-{w}-{scn}-explore.png"), "full": True}]})
            jobs.append({"id": f"ive-measure:{w}:{scn}", "type": "shot", "url": url, "width": w, "height": 900, "scheme": scn})
    # no JavaScript: posters decoded before anything is asserted (the WP5 flake), then the shots
    nojs_check = {"eval": "(async () => { const imgs = [...document.images]; "
                          "await Promise.all(imgs.map((i) => i.decode().then(() => true, () => false))); "
                          "const h = document.getElementById('answers'), tx = document.querySelector('noscript ol.tx'); "
                          "return {images: imgs.map((i) => ({src: i.getAttribute('src'), ok: i.complete && i.naturalWidth > 0})), "
                          "answers_heading_before_transcript: !!(h && tx && (h.compareDocumentPosition(tx) & Node.DOCUMENT_POSITION_FOLLOWING)), "
                          "transcript_items: document.querySelectorAll('ol.tx li').length}; })()", "as": "nojs"}
    for w in WIDTHS:
        jobs.append({"id": f"ive-nojs:{w}", "type": "script", "url": url, "width": w, "height": 900, "js": False,
                     "steps": [nojs_check, {"shot": str(shots / f"ive-nojs-{w}.png"), "full": True}]})
    res = shoot(jobs, work, sha)
    R = {r["id"]: r for r in res["results"]}
    beh = R["ive-behaviour"]
    vals = beh.get("values", {})
    # what the video frame shows at the same instants, derived from the composition (review P1-3)
    from . import frames
    times = [round(t, 3) for c in cue_list for t in _pause_points(c)]
    frame_at, _sc = frames.probe(lesson, ive_dir.parent / "video", timing, times, work_name="frames-ive", lesson_sha=sha)
    explorer = {(c["cue"], t): (vals.get(f"seek:{c['cue']}@{t:.3f}") or {}).get("state")
                for c in cue_list for t in _pause_points(c)}
    seek_rows, bad_seek = frames.compare_pauses(cue_list, frame_at, explorer, _pause_points)
    brows = []
    for i, b in enumerate(bseeks):
        got = vals.get(f"boundary:{i}") or {}
        brows.append({**b, "actual_t": got.get("t"), "shown_cue": got.get("cue"), "resolved": got.get("resolved")})
    bad_b = [r for r in brows if r["shown_cue"] != r["expected"] or r["resolved"] != r["expected"]]
    chap = vals.get("chapters") or []
    starts = [vtt_start(c) for c in cue_list]
    exp_chap = [cue_list[resolve(starts, float(f"{s['start']:.3f}"), fps)]["cue"] for s in timing["scenes"]]
    chap_bad = [{"chapter": i, "expected": e, "shown": (chap[i] if i < len(chap) else {}).get("cue")}
                for i, e in enumerate(exp_chap) if i >= len(chap) or chap[i].get("cue") != e or chap[i].get("current") != "true"]
    gates.append(g("ive.pause-state", "ive", beh.get("ok") and not bad_seek and not chap_bad and not bad_b and bool(brows)
                   and len(seek_rows) == len(times) and len(frame_at) == len(set(times)),
                   {"rule": "explorer == cue state, and explorer == state derived from the frame (a transition or "
                            "answer cue may show a frame in mid-tween of the same program, between its state and the next); "
                            "windows are half-open and a time under one frame before a boundary resolves to the later window",
                    "pauses_checked": len(seek_rows), "mismatches": bad_seek, "chapter_jumps": chap, "chapter_mismatches": chap_bad,
                    "boundary_seeks": len(brows), "boundary_mismatches": bad_b,
                    "boundary_cases_strict_rule_gets_wrong": sum(1 for r in brows if r["strict_half_open"] != r["expected"]),
                    "frame_states": {f"{r['cue']}@{r['t']}": r["frame_state"] for r in seek_rows},
                    "error": beh.get("error", "")[:500]}))
    leaks = {k: (R[k].get("values") or {}).get("leak") or {"error": R[k].get("error", "")[:300]} for k in R if k.startswith("ive-leak:")}
    leak_bad = [{"job": k, **v} for k, v in leaks.items() if v.get("hits") or v.get("error") or v.get("mode") != "explore"]
    nojs = {w: (R[f"ive-nojs:{w}"].get("values") or {}).get("nojs") or {} for w in WIDTHS}
    order_ok = all(n.get("answers_heading_before_transcript") for n in nojs.values())
    gates.append(g("ive.no-answer-leak", "ive", bool(leaks) and not leak_bad and order_ok,
                   {"checked_before": leaks, "leaks": leak_bad, "noscript_answers_heading_first": order_ok,
                    "rule": "paused 0.1 s before each answer cue: no answer word in the DOM (noscript excluded), alt text, "
                            "aria-label, title or the transcript so far; the noscript transcript sits after its "
                            "'contains the answers' heading"},
                   "" if leaks else "no answer cue found"))
    ctl = vals.get("controls") or {}
    nav = (ctl.get("nav") or []) + ((R["ive-explore"].get("values") or {}).get("nav") or [])
    nav_bad = [e for e in nav if e.get("event_type") != "navigation" or e.get("action") not in NAV_ACTIONS
               or set(e) != NAV_KEYS]
    imgs_ok = all(n.get("images") and all(i["ok"] for i in n["images"]) for n in nojs.values())
    ok_ctl = (ctl.get("chapters") == len(timing["scenes"]) and ctl.get("caption_modes") == ["showing", "hidden", "showing"]
              and ctl.get("transcript_items_at_end") == len(timing["cues"]) and ctl.get("seek_after_click") is not None
              and abs(ctl["seek_after_click"] - timing["cues"][0]["start"]) < 0.01 and bool(nav) and not nav_bad)
    gates.append(g("ive.controls", "ive", ok_ctl and imgs_ok and all(R[f"ive-nojs:{w}"].get("ok") for w in WIDTHS),
                   {"controls": {k: v for k, v in ctl.items() if k != "nav"}, "nav_events": len(nav),
                    "nav_actions": sorted({e.get("action") for e in nav}), "nav_not_navigation": nav_bad[:5],
                    "nojs": nojs, "nojs_shots": [f"shots/ive-nojs-{w}.png" for w in WIDTHS]}))
    ex = R["ive-explore"].get("values") or {}
    f0, e1, e2, r3, p4 = (ex.get(k) or {} for k in ("film", "explore", "edited", "returned", "repaused"))
    rt = e1.get("returnTime")
    p4_state = next((c["state"] for c in cue_list if c["cue"] == p4.get("cue")), None)
    alt = ((lesson.data.get("figure") or {}).get("compare") or {}).get("program")
    checks = {
        "film_follows_clock": f0.get("mode") == "film" and f0.get("origin") == "film",
        "explore_on_pause": e1.get("mode") == "explore" and e1.get("paused") is True and e1.get("origin") == "film"
        and e1.get("cue") == e1.get("expected_cue"),
        "edit_marked_yours": e2.get("origin") == "yours" and bool(e2.get("edit")) and e2.get("border") == "dashed"
        and e1.get("border") != "dashed" and e2.get("output") != e1.get("output"),
        "return_resumes_at_pause": r3.get("mode") == "film" and r3.get("paused") is False and rt is not None
        and r3.get("return_position") is not None and abs(r3["return_position"] - rt) < 0.002
        and rt - 0.001 <= r3.get("t", -1) < rt + 1.0,
        "return_shows_film_state": r3.get("origin") == "film" and r3.get("cue") == r3.get("film_cue") and r3.get("edits_left") == 0,
        "no_edit_after_return": p4.get("origin") == "film" and p4.get("edit") is None and p4_state is not None
        and p4.get("n_checked") in (None, p4_state["vars"].get(next(iter(p4_state["vars"]), ""), None))
        and p4.get("brk_pressed") in (None, "true" if p4_state["program"] == alt else "false"),
    }
    gates.append(g("ive.explore-return", "ive", R["ive-explore"].get("ok") and all(checks.values()),
                   {"checks": checks, "film": f0, "explore": e1, "edited": e2, "returned": r3, "repaused": p4,
                    "error": R["ive-explore"].get("error", "")[:500]}))
    fl = (R["ive-files"].get("values") or {}).get("files") or {}
    want = {"captions": len(timing["cues"]), "chapters": len(timing["scenes"]), "metadata": len(cue_list)}
    got_tracks = {t["kind"]: t["cues"] for t in fl.get("tracks", [])}
    file_console = [m for j in R.values() if j.get("type") == "script" and not j["id"].startswith("ive-nojs")
                    for m in j.get("console", []) if m.startswith(("error", "pageerror"))]
    gates.append(g("ive.file-protocol", "ive", fl.get("protocol") == "file:" and got_tracks == want
                   and fl.get("readyState", 0) >= 2 and not fl.get("error") and set(fl.get("track_src", [])) == {"blob"}
                   and not file_console,
                   {"files": fl, "expected_cues": want, "console_errors": file_console[:10]}))
    pages, errs = [], []
    for w in WIDTHS:
        for scn in SCHEMES:
            m = R[f"ive-measure:{w}:{scn}"]
            sv = R[f"ive-shot:{w}:{scn}"].get("values") or {}
            keys = (m.get("measure") or {}).get("keyNodes", [])
            missing = [k for k in ("code", "output") if k not in keys]
            pages.append({"width": w, "scheme": scn, "key_nodes": keys,
                          "problems": (m.get("measure") or {}).get("problems", ["job failed"])
                          + ([{"kind": "key-node-missing", "keys": missing}] if missing else [])
                          + [{**pr, "at": st} for st in ("film_layout", "explore_layout")
                             for pr in (sv.get(st) or {"problems": [{"kind": "not-measured"}]})["problems"]],
                          "console": [c for c in m.get("console", []) if "error" in c.lower() or "violat" in c.lower()],
                          "shots": [f"shots/ive-{w}-{scn}.png", f"shots/ive-{w}-{scn}-explore.png"]})
            if not R[f"ive-shot:{w}:{scn}"].get("ok"):
                errs.append(R[f"ive-shot:{w}:{scn}"].get("error", "")[:300])
    bad_pages = [p for p in pages if p["problems"] or p["console"]]
    gates.append(g("ive.layout", "ive", not bad_pages and not errs, {"pages": pages, "errors": errs}))
    firsts, faces = set(), set()
    for w in WIDTHS:
        for scn in SCHEMES:
            m = R[f"ive-measure:{w}:{scn}"].get("measure") or {}
            firsts |= {f.split(",")[0].strip().strip("'\"") for f in m.get("fonts", []) if f}
            faces |= set(m.get("loadedFaces", []))
    firsts -= {"monospace", "serif", "cursive", "sans-serif"}
    # review P3-10: the first family of every stack must be bundled and actually loaded (no Georgia pass)
    gates.append(g("ive.fonts", "ive", bool(firsts) and firsts <= ALLOWED_FAMILIES and firsts <= faces,
                   {"families_used": sorted(firsts), "faces_loaded": sorted(faces),
                    "not_loaded": sorted(firsts - faces)}))
    gates.append(g("ive.network", "ive", not res["outbound"], {"outbound_requests": res["outbound"]}))
    return gates
