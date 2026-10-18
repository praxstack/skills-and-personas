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
                     "width": 1200 if wide else 400, "height": 3000, "scale": 3,
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


# ---------------------------------------------------------------- IVE (AC-6.1..6.4 subset for WP0)

LEAK_JS = r"""(answerWords) => {
  const root = document.body.cloneNode(true);
  root.querySelectorAll('noscript, script, [data-code], video, track').forEach((e) => e.remove());
  const texts = [root.textContent];
  document.querySelectorAll('[alt], [aria-label], [title]').forEach((e) => {
    if (e.closest('noscript')) return;
    ['alt', 'aria-label', 'title'].forEach((a) => e.getAttribute(a) && texts.push(e.getAttribute(a)));
  });
  const words = new Set(texts.join(' ').toLowerCase().match(/[a-z']+/g) || []);
  return { hits: answerWords.filter((w) => words.has(w)), transcript_items: document.querySelectorAll('#tx li').length,
           state: document.getElementById('state').dataset.state || null, cue: document.getElementById('state').dataset.cue || null };
}"""


def _pause_points(c):
    """Just after the cue starts (1.5 frames), the old WP0 point, and just before it ends."""
    span = c["end"] - c["start"]
    pts = [c["start"] + min(0.05, span / 3), c["start"] + min(0.2, span / 2), c["end"] - min(0.05, span / 3)]
    return sorted({round(t, 3) for t in pts})


def ive_gates(lesson, ive_dir, cue_list, timing):
    sha = lesson.sha256()
    work = ive_dir.parent / "work" / "ive"
    gates = []
    answer_cues = [c for c in cue_list if c["kind"] == "answer"]
    with LocalServer(ive_dir) as srv:
        url = srv.url + "/index.html"
        ready = {"waitFor": "window.__ptkReady && window.__ptkReady()", "timeout": 30000}
        steps = [ready]
        # pause/seek: every cue at three points (just after its start, inside it, just before its end)
        for c in cue_list:
            for t in _pause_points(c):
                steps += [{"eval": f"(async () => {{ const v = document.getElementById('v'); v.pause(); v.currentTime = {t:.3f}; "
                                   f"await new Promise(r => v.addEventListener('seeked', r, {{once: true}})); "
                                   f"await new Promise(r => setTimeout(r, 150)); "
                                   f"const s = document.getElementById('state'); return {{t: {t:.3f}, state: s.dataset.state, cue: s.dataset.cue}}; }})()",
                           "as": f"seek:{c['cue']}@{t:.3f}"}]
        # leak: 0.1 s before each answer cue
        for c in answer_cues:
            q = next(x for x in cue_list if x.get("question") and x["question"]["scene"] == c["answer_for"])
            sc = next(s for s in timing["scenes"] if s["id"] == c["answer_for"])
            words = [w.strip().lower() for w in lesson.fact(sc["question"]["answer_fact"])["value"].split("\n") if w.strip()]
            t = c["start"] - 0.1
            steps += [{"eval": f"(async () => {{ const v = document.getElementById('v'); v.pause(); v.currentTime = {t:.3f}; "
                               f"await new Promise(r => v.addEventListener('seeked', r, {{once: true}})); "
                               f"await new Promise(r => setTimeout(r, 200)); return ({LEAK_JS})({json.dumps(words)}); }})()",
                       "as": f"leak:{c['cue']}"},
                      {"shot": str(ive_dir.parent / "shots" / f"ive-before-answer-{c['cue']}.png"), "full": True}]
        # chapters: click each, read state
        steps += [{"eval": "(async () => { const out = []; const bs = [...document.querySelectorAll('#chapters button')]; "
                           "const v = document.getElementById('v'); "
                           "for (const b of bs) { b.click(); await new Promise(r => v.addEventListener('seeked', r, {once: true})); "
                           "await new Promise(r => setTimeout(r, 150)); out.push({t: v.currentTime, paused: v.paused, "
                           "state: document.getElementById('state').dataset.state}); } return out; })()", "as": "chapters"},
                  {"eval": "(async () => { const v = document.getElementById('v'); v.currentTime = v.duration - 0.05; "
                           "await new Promise(r => v.addEventListener('seeked', r, {once: true})); await new Promise(r => setTimeout(r, 150)); "
                           "const b = document.querySelector('#tx li button'); const n = document.querySelectorAll('#tx li').length; b.click(); "
                           "await new Promise(r => v.addEventListener('seeked', r, {once: true})); "
                           "const caps = [...v.textTracks].find(t => t.kind === 'captions'); const cb = document.getElementById('caps'); "
                           "const m0 = caps.mode; cb.click(); const m1 = caps.mode; cb.click(); const m2 = caps.mode; "
                           "return {transcript_items_at_end: n, seek_after_click: v.currentTime, caption_modes: [m0, m1, m2], "
                           "chapters: document.querySelectorAll('#chapters li').length, can_play_h264: v.canPlayType('video/mp4; codecs=\"avc1.640028\"'), "
                           "readyState: v.readyState, error: v.error && v.error.code, "
                           "nav_kinds: [...new Set(window.__ptkNav.map(e => e.kind))], nav_events: window.__ptkNav.length}; })()",
                   "as": "controls"}]
        jobs = [{"id": "ive-behaviour", "type": "script", "url": url, "width": 1440, "height": 1000, "steps": steps}]
        for w in WIDTHS:
            for scn in SCHEMES:
                jobs.append({"id": f"ive-shot:{w}:{scn}", "type": "script", "url": url, "width": w, "height": 900, "scheme": scn,
                             "steps": [ready, {"eval": f"(async () => {{ const v = document.getElementById('v'); v.currentTime = {cue_list[-2]['start'] + 0.3:.3f}; "
                                                       "await new Promise(r => v.addEventListener('seeked', r, {once: true})); "
                                                       "await new Promise(r => setTimeout(r, 300)); return 1; })()", "as": "seek"},
                                       {"shot": str(ive_dir.parent / "shots" / f"ive-{w}-{scn}.png"), "full": True}]})
                jobs.append({"id": f"ive-measure:{w}:{scn}", "type": "shot", "url": url, "width": w, "height": 900, "scheme": scn})
        jobs.append({"id": "ive-nojs", "type": "shot", "url": url, "width": 1440, "height": 900, "js": False,
                     "shot": str(ive_dir.parent / "shots" / "ive-nojs-1440.png")})
        jobs.append({"id": "ive-nojs-dom", "type": "script", "url": url, "width": 390, "height": 900, "js": False,
                     "steps": [{"shot": str(ive_dir.parent / "shots" / "ive-nojs-390.png"), "full": True}]})
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
    chap = vals.get("chapters") or []
    exp_chap = []
    for s in timing["scenes"]:
        k = max((i for i, c in enumerate(cue_list) if c["start"] <= s["start"] + 1e-3), default=0)
        exp_chap.append(cue_list[k]["state"]["state_id"])
    chap_bad = [{"chapter": i, "expected": e, "shown": (chap[i] if i < len(chap) else {}).get("state")}
                for i, e in enumerate(exp_chap) if i >= len(chap) or chap[i].get("state") != e]
    gates.append(g("ive.pause-state", "ive", beh.get("ok") and not bad_seek and not chap_bad
                   and len(seek_rows) == len(times) and len(frame_at) == len(set(times)),
                   {"rule": "explorer == cue state, and explorer == state derived from the frame (a transition or "
                            "answer cue may show a frame in mid-tween)", "pauses_checked": len(seek_rows),
                    "mismatches": bad_seek, "chapter_jumps": chap, "chapter_mismatches": chap_bad,
                    "frame_states": {f"{r['cue']}@{r['t']}": r["frame_state"] for r in seek_rows},
                    "error": beh.get("error", "")[:500]}))
    leaks = {k: v for k, v in vals.items() if k.startswith("leak:")}
    leak_bad = [{"cue": k, **v} for k, v in leaks.items() if v.get("hits")]
    gates.append(g("ive.no-answer-leak", "ive", beh.get("ok") and bool(leaks) and not leak_bad,
                   {"checked_before": {k: v for k, v in leaks.items()}, "leaks": leak_bad},
                   "" if leaks else "no answer cue found"))
    ctl = vals.get("controls") or {}
    nojs = R.get("ive-nojs", {})
    ok_ctl = (ctl.get("chapters") == len(timing["scenes"]) and ctl.get("caption_modes") == ["showing", "hidden", "showing"]
              and ctl.get("transcript_items_at_end") == len(timing["cues"]) and ctl.get("seek_after_click") is not None
              and abs(ctl["seek_after_click"] - timing["cues"][0]["start"]) < 0.25 and ctl.get("nav_kinds") == ["navigation"])
    gates.append(g("ive.controls", "ive", ok_ctl and nojs.get("ok") and nojs.get("imagesLoaded"),
                   {"controls": ctl, "nojs_images_loaded": nojs.get("imagesLoaded"), "nojs_shot": "shots/ive-nojs-1440.png"}))
    pages, errs = [], []
    for w in WIDTHS:
        for scn in SCHEMES:
            m = R[f"ive-measure:{w}:{scn}"]
            keys = (m.get("measure") or {}).get("keyNodes", [])
            missing = [k for k in ("code", "output") if k not in keys]
            pages.append({"width": w, "scheme": scn, "key_nodes": keys,
                          "problems": (m.get("measure") or {}).get("problems", ["job failed"])
                          + ([{"kind": "key-node-missing", "keys": missing}] if missing else []),
                          "console": [c for c in m.get("console", []) if "error" in c.lower() or "violat" in c.lower()],
                          "shot": f"shots/ive-{w}-{scn}.png"})
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
