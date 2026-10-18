"""Visual gate: Playwright screenshots (390/1440 x light/dark), layout, contrast, fonts, alt text,
outbound requests and tesseract OCR of every value and number cell (AC-3.2..3.6 subset for WP0).

One browser run per call (E12). Any request that is not local is aborted and fails the gate.
"""
import functools
import http.server
import json
import os
import re
import threading
from pathlib import Path

from .. import fonts, host, node

ALLOWED_FAMILIES = {"Source Serif 4", "JetBrains Mono", "Caveat"}
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


class LocalServer:
    def __init__(self, root):
        handler = functools.partial(_RangeHandler, directory=str(root))
        handler.extensions_map = {**_RangeHandler.extensions_map, ".vtt": "text/vtt", ".mp4": "video/mp4",
                                  ".svg": "image/svg+xml", ".mjs": "text/javascript"}
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
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
    Grouped crops (a column) are read as a block and compared token by token."""
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
        ok = re.findall(r"\S+", got.lower()) == re.findall(r"\S+", exp.lower())
        out.append({"expected": exp.replace("\n", " "), "read": got.replace("\n", " "), "ok": ok,
                    "crop": "/".join(Path(c["path"]).parts[-2:]), "group": c.get("group")})
    return out


# ---------------------------------------------------------------- helpers

def _lab_l(hexcol):
    h = hexcol.lstrip("#")
    lin = [((int(h[i:i + 2], 16) / 255) / 12.92) if int(h[i:i + 2], 16) / 255 <= 0.04045
           else (((int(h[i:i + 2], 16) / 255) + 0.055) / 1.055) ** 2.4 for i in (0, 2, 4)]
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    return 116 * y ** (1 / 3) - 16 if y > 216 / 24389 else 24389 / 27 * y


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

def still_viewer(out_dir, lesson_id):
    """A plain viewer page: portrait under 640 px, theme from prefers-color-scheme."""
    name = lambda lay, th: f"{lesson_id}-{lay}-{th}.svg"
    t = fonts.tokens()["themes"]
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{lesson_id}</title>
<style>html,body{{margin:0;background:{t['light']['paper']}}}img{{display:block;width:100%;height:auto}}
@media (prefers-color-scheme: dark){{html,body{{background:{t['dark']['paper']}}}}}</style></head>
<body><picture>
<source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="{name('portrait', 'dark')}">
<source media="(max-width: 640px)" srcset="{name('portrait', 'light')}">
<source media="(prefers-color-scheme: dark)" srcset="{name('wide', 'dark')}">
<img src="{name('wide', 'light')}" alt="see the figure's own title and description">
</picture></body></html>
"""
    (out_dir / "index.html").write_text(html)
    return out_dir / "index.html"


def make_pngs(out_dir, svgs, lesson_sha):
    jobs = [{"id": f"png:{s}", "type": "png", "url": (out_dir / s).resolve().as_uri(),
             "out": str((out_dir / s).with_suffix(".png")), "scale": 2,
             "width": 1200 if "-wide-" in s else 400, "height": 1000} for s in svgs]
    res = shoot(jobs, out_dir.parent / "work" / "still-png", lesson_sha)
    failed = [r for r in res["results"] if not r["ok"]]
    return [s.replace(".svg", ".png") for s in svgs], failed, res["outbound"]


def still_gates(lesson, out_dir, svgs):
    sha = lesson.sha256()
    work = out_dir.parent / "work" / "still-visual"
    viewer = still_viewer(out_dir, lesson.id)
    jobs = []
    for s in svgs:
        wide = "-wide-" in s
        jobs.append({"id": f"measure:{s}", "type": "svg-measure", "url": (out_dir / s).resolve().as_uri(),
                     "width": 1200 if wide else 400, "displayWidth": 1440 if wide else 390, "minPx": 11})
        jobs.append({"id": f"ocr:{s}", "type": "ocr-crops", "url": (out_dir / s).resolve().as_uri(),
                     "width": 1200 if wide else 400, "height": 1000, "scale": 3,
                     "outDir": str(work / "ocr" / s.replace(".svg", ""))})
    for w in WIDTHS:
        for sc in SCHEMES:
            jobs.append({"id": f"shot:{w}:{sc}", "type": "shot", "url": viewer.resolve().as_uri(), "width": w,
                         "height": 900, "scheme": sc, "shot": str(out_dir.parent / "shots" / f"still-{w}-{sc}.png")})
    res = shoot(jobs, work, sha)
    R = {r["id"]: r for r in res["results"]}
    errs = [{"job": r["id"], "error": r.get("error", "")[:400]} for r in res["results"] if not r["ok"]]
    gates = []

    layout, contrast, fams, alt, faces = [], [], set(), [], set()
    for s in svgs:
        m = R[f"measure:{s}"].get("measure")
        if not m:
            continue
        layout += [{**p, "svg": s} for p in m["problems"]]
        contrast += [{**c, "svg": s} for c in m["contrast"]]
        fams |= _families(m["fonts"])
        faces |= set(m["loadedFaces"])
        alt.append({"svg": s, "title": bool(m["title"].strip()), "desc_chars": len(m["desc"].strip()),
                    "source_link": m["source"]})
    pages = []
    for w in WIDTHS:
        for sc in SCHEMES:
            r = R[f"shot:{w}:{sc}"]
            pm = r.get("measure", {"problems": [{"kind": "job-failed"}]})
            pages.append({"width": w, "scheme": sc, "problems": pm["problems"], "images_loaded": r.get("imagesLoaded"),
                          "shot": f"shots/still-{w}-{sc}.png"})
    min_px = min((R[f"measure:{s}"]["measure"]["minPx"] * 1 for s in svgs if R[f"measure:{s}"].get("measure")),
                 default=0)
    page_bad = [p for p in pages if p["problems"] or not p["images_loaded"]]
    gates.append(g("visual.still.layout", "still", not layout and not page_bad and not errs,
                   {"svg_problems": layout[:30], "pages": pages, "min_text_px_at_display": round(min_px, 2),
                    "job_errors": errs},
                   "" if not layout and not page_bad else "overflow, overlap or text under 11 px"))
    low = [c for c in contrast if c["ratio"] < c["min"]]
    t = fonts.tokens()["themes"]["dark"]
    dl = abs(_lab_l(t["red"]) - _lab_l(t["blue"]))
    text_min = min((c["ratio"] for c in contrast if c["kind"] == "text"), default=0)
    rule_min = min((c["ratio"] for c in contrast if c["kind"] == "rule"), default=0)
    gates.append(g("visual.still.contrast", "still", not low and dl >= 15 and contrast,
                   {"pairs_checked": len(contrast), "below_minimum": low[:20], "min_text_ratio": text_min,
                    "min_rule_ratio": rule_min, "dark_red_blue_delta_L": round(dl, 1)}))
    crops = []
    for s in svgs:
        crops += [{**c, "svg": s, "dark": "-dark" in s} for c in R[f"ocr:{s}"].get("crops", [])]
    ocr = ocr_crops(crops)
    bad_ocr = [o for o in ocr if not o["ok"]]
    gates.append(g("visual.still.ocr", "still", ocr and not bad_ocr,
                   {"cells": len(ocr), "misread": bad_ocr[:20], "engine": host.tool_version("tesseract")}))
    extra = fams - ALLOWED_FAMILIES
    gates.append(g("visual.still.fonts", "still", not extra and faces and faces <= ALLOWED_FAMILIES,
                   {"families_used": sorted(fams), "faces_loaded": sorted(faces), "not_bundled": sorted(extra)}))
    alt_ok = all(a["title"] and a["desc_chars"] > 40 and a["source_link"] for a in alt) and len(alt) == len(svgs)
    gates.append(g("visual.still.alt-source", "still", alt_ok, {"svgs": alt}))
    gates.append(g("visual.still.network", "still", not res["outbound"], {"outbound_requests": res["outbound"]}))
    return gates
