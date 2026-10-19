"""Shared machinery for the v2.2 Track B visual-quality measures, AC-10.1 to AC-10.5 (not a test module).

Every measure reads the built artifact the way a learner meets it: SVG and HTML are rendered in Playwright
(through ptk's own shoot.mjs runner), video frames come from the composition seeked like the renderer seeks it
and from the encoded MP4, narration timing comes from the final audio. Lesson builds are read, never written:
scratch files go under $PTK_STATE/tmp and full measurements under $PTK_STATE/b0-measures/.

A lesson-level test raises NotRun("not built: ...") when the build it needs is missing. It never passes on a
missing build.
"""
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from _util import V21
from selftest_support import NotRun
from ptk import host, model
from ptk.verify import visual

LESSONS_DIR = V21 / "lessons"
FIXTURES = host.PKG / "tests" / "fixtures" / "layout"

# One mechanism kind per shipped lesson (SPEC v1.4 AC-10.2). A new lesson declares figure.mechanism instead.
MECHANISM_KIND = {
    "switch-fallthrough": "control-path",
    "factorial-stack": "stack-column",
    "one-byte-four-views": "bytes",
    "neuron": "neuron",
}


# ---------------------------------------------------------------- lessons and builds

def lesson_slugs():
    return sorted(p.name for p in LESSONS_DIR.iterdir() if (p / "lesson.json").is_file()) if LESSONS_DIR.is_dir() else []


def lesson_dir(slug):
    return LESSONS_DIR / slug


def need(slug, *rel):
    """The build paths a lesson-level measure reads; NotRun when any is missing (never a pass)."""
    b = lesson_dir(slug) / "build"
    missing = [r for r in rel if not (b / r).exists()]
    if missing:
        raise NotRun(f"not built: lessons/{slug}/build/{missing[0]}")
    return b


def load(slug):
    return model.load(lesson_dir(slug))


def record(name, data):
    """Full measurement for the review record: $PTK_STATE/b0-measures/<name>.json."""
    root = host.state_path("b0-measures")
    root.mkdir(parents=True, exist_ok=True)
    p = root / f"{name}.json"
    p.write_text(json.dumps(data, indent=1, default=str))
    return str(p)


def lesson_tests(module_globals, prefix, fn):
    """One test function per lesson: test_lesson_<slug> calls fn(slug)."""
    for slug in lesson_slugs():
        def t(slug=slug):
            return fn(slug)
        t.__name__ = f"test_lesson_{slug.replace('-', '_')}"
        t.__doc__ = f"{prefix} on the built lesson {slug} (not-run when the build is missing)."
        module_globals[t.__name__] = t


# ---------------------------------------------------------------- captured facts

def _stdout(capture_dir, program):
    p = Path(capture_dir) / f"{program}.stdout"
    return p.read_text() if p.is_file() else None


def capture_value(fact, capture_dir, platform):
    """A fact's value read again from the capture files (not from lesson.json): stdout line N (1-based), field K
    (1-based, whitespace split), the whole stdout, or a platform key. None when the capture lacks it."""
    sel = fact.get("select", {})
    if sel.get("stream") == "platform":
        cur = platform
        for k in sel.get("key", "").split(".", 1):
            cur = (cur or {}).get(k) if isinstance(cur, dict) else None
        return None if cur is None else str(cur)
    out = _stdout(capture_dir, fact.get("program"))
    if out is None:
        return None
    if "line" not in sel:
        return out
    lines = out.split("\n")
    n = sel["line"]
    if not 0 < n <= len(lines):
        return None
    line = lines[n - 1]
    if "field" in sel:
        parts = line.split()
        k = sel["field"]
        return parts[k - 1] if 0 < k <= len(parts) else None
    return line


def captured_facts(data, capture_dir):
    """{fact id: value from capture} plus the facts whose lesson.json value differs from the capture."""
    vals, drift = {}, []
    for f in data.get("facts", []):
        v = capture_value(f, capture_dir, data.get("platform", {}))
        vals[f["id"]] = v
        if v is not None and f.get("value") is not None and v.rstrip("\n") != f["value"].rstrip("\n"):
            drift.append({"fact": f["id"], "capture": v, "lesson_json": f["value"]})
    return vals, drift


def norm_text(s):
    return re.sub(r"\s+", " ", (s or "").replace("−", "-").replace(" ", " ")).strip()


def stdout_fact_ids(data):
    return {f["id"] for f in data.get("facts", []) if f.get("select", {}).get("stream") == "stdout"}


# ---------------------------------------------------------------- geometry

def clip(b, W, H):
    x0, y0 = max(0.0, b[0]), max(0.0, b[1])
    x1, y1 = min(float(W), b[0] + b[2]), min(float(H), b[1] + b[3])
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def rect_union_area(rects):
    """Exact area of a union of (x0, y0, x1, y1) rectangles (coordinate sweep)."""
    rects = [r for r in rects if r and r[2] > r[0] and r[3] > r[1]]
    if not rects:
        return 0.0
    xs = sorted({r[0] for r in rects} | {r[2] for r in rects})
    area = 0.0
    for xa, xb in zip(xs, xs[1:]):
        ivs = sorted((r[1], r[3]) for r in rects if r[0] <= xa and r[2] >= xb)
        tot, cs, ce = 0.0, None, None
        for s, e in ivs:
            if cs is None or s > ce:
                if cs is not None:
                    tot += ce - cs
                cs, ce = s, e
            else:
                ce = max(ce, e)
        if cs is not None:
            tot += ce - cs
        area += tot * (xb - xa)
    return area


def hull(boxes):
    bs = [b for b in boxes if b]
    if not bs:
        return None
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


def largest_empty_rect(occ, cols, rows):
    """Largest all-empty axis-aligned rectangle in a cols x rows occupancy grid, in cells (histogram method)."""
    heights = [0] * cols
    best, where = 0, None
    for r in range(rows):
        for c in range(cols):
            heights[c] = 0 if occ[r * cols + c] else heights[c] + 1
        stack = []
        for c in range(cols + 1):
            h = heights[c] if c < cols else 0
            start = c
            while stack and stack[-1][1] >= h:
                s, sh = stack.pop()
                if sh * (c - s) > best:
                    best, where = sh * (c - s), (s, r - sh + 1, c - s, sh)
                start = s
            stack.append((start, h))
    return best, where


EMPTY_CELL = 20  # px at 1080p: the grid the DOM empty-region measure uses (96 x 54 cells)


def dom_empty_fraction(boxes, W, H, cell=EMPTY_CELL):
    """Share of the frame taken by the largest rectangle that no drawn content touches. Content boxes are
    (x, y, w, h); a cell is occupied when any box overlaps it."""
    cols, rows = math.ceil(W / cell), math.ceil(H / cell)
    occ = [False] * (cols * rows)
    for b in boxes:
        c = clip(b, W, H)
        if not c:
            continue
        for r in range(int(c[1] // cell), min(rows, int(math.ceil(c[3] / cell)))):
            for k in range(int(c[0] // cell), min(cols, int(math.ceil(c[2] / cell)))):
                occ[r * cols + k] = True
    best, where = largest_empty_rect(occ, cols, rows)
    rect = [where[0] * cell, where[1] * cell, where[2] * cell, where[3] * cell] if where else None
    return round(best / (cols * rows), 4), rect


# ---------------------------------------------------------------- pixels (MP4 frames, screenshots)

FRAME_W, FRAME_H, BLOCK = 480, 270, 5  # a 1080p frame at quarter size; 5 x 5 blocks = 20 px cells at 1080p
FLAT_RANGE = 10  # a block whose gray levels span at most this many values is flat (nothing drawn there)


def gray_raw(src, out, t=None, w=FRAME_W, h=FRAME_H):
    """8-bit gray w x h raster of a video frame at time t, or of an image (t None), via ffmpeg."""
    cmd = [host.which("ffmpeg"), "-v", "error", "-y"]
    if t is not None:
        cmd += ["-ss", f"{t:.3f}"]
    cmd += ["-i", str(src), "-frames:v", "1", "-vf", f"scale={w}:{h}:flags=area,format=gray", "-f", "rawvideo", str(out)]
    host.run(cmd, check=True, timeout=120)
    data = Path(out).read_bytes()
    if len(data) != w * h:
        raise ValueError(f"frame grab gave {len(data)} bytes, expected {w * h}")
    return data


def flat_empty_fraction(raw, w=FRAME_W, h=FRAME_H, block=BLOCK, flat=FLAT_RANGE):
    """Largest rectangle of flat blocks (no detail drawn) as a share of the frame. A flat card counts as empty:
    a viewer sees an empty card, so this is stricter than the DOM measure."""
    cols, rows = w // block, h // block
    occ = [False] * (cols * rows)
    for r in range(rows):
        for c in range(cols):
            lo, hi = 255, 0
            for y in range(r * block, r * block + block):
                row = raw[y * w + c * block: y * w + c * block + block]
                lo, hi = min(lo, min(row)), max(hi, max(row))
            occ[r * cols + c] = hi - lo > flat
    best, where = largest_empty_rect(occ, cols, rows)
    scale = 1920 / w
    rect = [round(v * block * scale) for v in where] if where else None
    return round(best / (cols * rows), 4), rect


# ---------------------------------------------------------------- in-page extraction

EXTRACT_JS = r"""(opts) => {
  opts = opts || {};
  const W = opts.W || window.innerWidth, H = opts.H || window.innerHeight;
  const eop = (el) => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (s.display === 'none' || s.visibility === 'hidden' || s.visibility === 'collapse') return 0;
      o *= parseFloat(s.opacity); if (e.tagName === 'svg' && !e.parentElement) break; } return o; };
  const R = (v) => Math.round(v * 10) / 10;
  const box = (b) => [R(b.x), R(b.y), R(b.width), R(b.height)];
  const dataOf = (el) => { const o = {}; for (const a of el.attributes) if (a.name.startsWith('data-')) o[a.name.slice(5)] = a.value; return o; };
  const near = (el, attr) => { const c = el.closest('[' + attr + ']'); return c ? c.getAttribute(attr) : null; };
  const conts = { fig: [], mech: [], part: [] };
  const idx = (el, sel, arr) => { const c = el.closest(sel); if (!c) return null; let i = arr.indexOf(c); if (i < 0) { arr.push(c); i = arr.length - 1; } return i; };
  const SKIP = 'defs, marker, clipPath, mask, symbol, pattern, script, style, noscript, template, title, desc, head';
  const items = [];
  const common = (el) => ({
    fig: idx(el, '[data-role="figure"]', conts.fig), mech: idx(el, '[data-role="mechanism"]', conts.mech),
    part: idx(el, '[data-part]', conts.part), key: near(el, 'data-key'),
    fact: near(el, 'data-fact') || near(el, 'data-m'), claim: near(el, 'data-claim') || near(el, 'data-claims'),
    chrome: near(el, 'data-chrome'), label: near(el, 'data-label'), role: near(el, 'data-role'),
    misc: near(el, 'data-misconception'), question: near(el, 'data-question'), srcline: near(el, 'data-src-line'),
    code: !!el.closest('[data-code], code, pre, .src, [data-key="code"]'), d: dataOf(el) });
  const ctmScale = (el) => { const m = el.getScreenCTM && el.getScreenCTM(); return m ? Math.hypot(m.a, m.b) : 1; };
  const blockText = (el) => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const d = getComputedStyle(e).display;
      if (e.tagName === 'text' || /block|flex|grid|list-item|table-cell|table-caption/.test(d)) return (e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 400); }
    return ''; };
  // painted SVG shapes
  for (const el of document.querySelectorAll('path, line, polyline, polygon, circle, ellipse, rect, image, use')) {
    if (el.closest(SKIP)) continue;
    const o = eop(el); if (o < 0.02) continue;
    const cs = getComputedStyle(el), b = el.getBoundingClientRect();
    const sw = parseFloat(cs.strokeWidth) || 0;
    const fillOn = cs.fill && cs.fill !== 'none' && parseFloat(cs.fillOpacity) > 0;
    const strokeOn = cs.stroke && cs.stroke !== 'none' && sw > 0 && parseFloat(cs.strokeOpacity) > 0;
    if (!fillOn && !strokeOn && el.tagName !== 'image' && el.tagName !== 'use') continue;
    if (b.width <= 0 && b.height <= 0) continue;
    const bb = [b.x, b.y, Math.max(b.width, sw), Math.max(b.height, sw)];
    items.push({ k: 'shape', tag: el.tagName, b: bb.map(R), o: R(o), fill: fillOn ? cs.fill : null, stroke: strokeOn ? cs.stroke : null, ...common(el) });
  }
  // SVG text
  for (const el of document.querySelectorAll('text')) {
    if (el.closest(SKIP)) continue;
    const o = eop(el); if (o < 0.02) continue;
    const t = (el.textContent || '').replace(/\s+/g, ' ').trim(); if (!t) continue;
    const cs = getComputedStyle(el), b = el.getBoundingClientRect();
    items.push({ k: 'text', tag: 'text', t, b: box(b), o: R(o), ff: cs.fontFamily, px: R(parseFloat(cs.fontSize) * ctmScale(el)),
                 block: t, ...common(el) });
  }
  // HTML text (own text nodes), media
  for (const el of (document.body ? document.body.querySelectorAll('*') : [])) {
    if (el.closest('svg') || el.closest(SKIP)) continue;
    if (/^(IMG|VIDEO|CANVAS)$/.test(el.tagName)) {
      const o = eop(el); const b = el.getBoundingClientRect();
      if (o >= 0.02 && b.width > 0 && b.height > 0) items.push({ k: 'media', tag: el.tagName.toLowerCase(), b: box(b), o: R(o), ...common(el) });
      continue;
    }
    const own = [...el.childNodes].filter((n) => n.nodeType === 3 && n.textContent.trim());
    if (!own.length) continue;
    const o = eop(el); if (o < 0.02) continue;
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const n of own) { const r = document.createRange(); r.selectNodeContents(n);
      for (const q of r.getClientRects()) { if (!q.width || !q.height) continue; x0 = Math.min(x0, q.left); y0 = Math.min(y0, q.top); x1 = Math.max(x1, q.right); y1 = Math.max(y1, q.bottom); } }
    if (x1 <= x0) continue;
    const cs = getComputedStyle(el), eb = el.getBoundingClientRect();
    const sc = el.offsetWidth > 0 ? eb.width / el.offsetWidth : 1;
    items.push({ k: 'text', tag: el.tagName.toLowerCase(), t: own.map((n) => n.textContent).join(' ').replace(/\s+/g, ' ').trim(),
                 b: [x0, y0, x1 - x0, y1 - y0].map(R), o: R(o), ff: cs.fontFamily, px: R(parseFloat(cs.fontSize) * sc),
                 block: blockText(el), ...common(el) });
  }
  // the containers named by the contract (figure, mechanism, parts), whether or not anything inside is painted
  for (const el of document.querySelectorAll('[data-role="figure"]')) idx(el, '[data-role="figure"]', conts.fig);
  for (const el of document.querySelectorAll('[data-role="mechanism"]')) idx(el, '[data-role="mechanism"]', conts.mech);
  for (const el of document.querySelectorAll('[data-role="mechanism"] [data-part]')) idx(el, '[data-part]', conts.part);
  const desc = (arr) => arr.map((el) => ({ b: box(el.getBoundingClientRect()), o: R(eop(el)), d: dataOf(el),
    mech: idx(el, '[data-role="mechanism"]', conts.mech), parent: el.parentElement ? idx(el.parentElement, '[data-part]', conts.part) : null }));
  const panels = [...document.querySelectorAll('[data-key="panel"]')].map((el) => ({ b: box(el.getBoundingClientRect()), o: R(eop(el)) }));
  const svg = document.documentElement.tagName === 'svg' ? document.documentElement : null;
  const vb = svg && svg.viewBox && svg.viewBox.baseVal ? [svg.viewBox.baseVal.width, svg.viewBox.baseVal.height] : null;
  const bg = document.getElementById('frame-bg');
  return { W, H, scrollH: document.documentElement.scrollHeight, viewBox: vb,
           rendered: svg ? box(svg.getBoundingClientRect()) : null,
           ground: bg ? getComputedStyle(bg).fill : getComputedStyle(document.body || document.documentElement).backgroundColor,
           items, figures: desc(conts.fig), mechanisms: desc(conts.mech), parts: desc(conts.part), panels };
}"""


def extract_step(opts=None, as_="m"):
    return {"eval": f"({EXTRACT_JS})({json.dumps(opts or {})})", "as": as_}


def shoot(jobs, name, lesson_sha=None, timeout=1200):
    work = host.make_tmp(f"b0-{name}-")
    try:
        res = visual.shoot(jobs, work, lesson_sha, timeout=timeout)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return res


def svg_size(path):
    root = ET.parse(path).getroot()
    vb = [float(v) for v in (root.get("viewBox") or "0 0 0 0").split()]
    w = float(re.sub(r"[^\d.]", "", root.get("width") or "") or vb[2])
    h = float(re.sub(r"[^\d.]", "", root.get("height") or "") or vb[3])
    return w, h


def extract_svgs(paths, name):
    """{path: extraction} for SVG files rendered at their natural size; plus outbound requests."""
    jobs = []
    for p in paths:
        w, h = svg_size(p)
        jobs.append({"id": str(p), "type": "script", "url": Path(p).resolve().as_uri(), "width": max(1, round(w)),
                     "height": max(1, round(h)), "steps": [extract_step({"W": w, "H": h})]})
    res = shoot(jobs, name)
    out = {}
    for r in res["results"]:
        out[r["id"]] = (r.get("values") or {}).get("m") if r.get("ok") else {"error": (r.get("error") or "")[:500]}
    return out, res["outbound"]


def is_ink(it, W, H):
    """Drawn content, as opposed to a background: text, media, and painted shapes, except a fill-only rect larger
    than 10% of the canvas (a card or ground) or one filled with the ground colour."""
    if it.get("o", 1) < 0.05:
        return False
    if it["k"] in ("text", "media"):
        return True
    if it["tag"] == "rect" and not it.get("stroke"):
        if it["b"][2] * it["b"][3] > 0.10 * W * H:
            return False
    return True


def ink_boxes(m, pred=None):
    W, H = m["W"], m["H"]
    return [it["b"] for it in m["items"] if is_ink(it, W, H) and (pred is None or pred(it))]


def group_coverage(m, key):
    """Union of the hulls of the painted content of each visible container of one kind ('fig' or 'mech'),
    clipped to the canvas, as a share of the canvas."""
    W, H = m["W"], m["H"]
    hulls = []
    conts = m["figures"] if key == "fig" else m["mechanisms"]
    for i, c in enumerate(conts):
        if c.get("o", 1) < 0.05:
            continue
        h = hull([clip(b, W, H) for b in ink_boxes(m, lambda it, i=i: it.get(key) == i)])
        if h:
            hulls.append(h)
    return round(rect_union_area(hulls) / (W * H), 4), [[round(v) for v in h] for h in hulls]


def panel_coverage(m):
    """rc1 has no data-role marks; the old data-key="panel" box is reported for comparison only, never gated."""
    W, H = m["W"], m["H"]
    rs = [clip(p["b"], W, H) for p in m.get("panels", []) if p.get("o", 1) >= 0.05]
    return round(rect_union_area(rs) / (W * H), 4)


# ---------------------------------------------------------------- video composition harness

def _harness(video_dir):
    """Standalone pages per scene (the template's body, GSAP, fonts), in a scratch dir that links the build's
    composition read-only. Nothing is written into the build."""
    tmp = host.make_tmp("b0-harness-")
    (tmp / "composition").symlink_to(Path(video_dir).resolve() / "composition")
    pages = {}
    for f in sorted((Path(video_dir) / "composition" / "compositions").glob("*.html")):
        m = re.search(r"<template>(.*)</template>", f.read_text(), re.S)
        if not m:
            continue
        page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><base href="composition/">'
                '<script src="vendor/gsap.min.js"></script><style>html,body{margin:0;width:1920px;height:1080px;'
                f'overflow:hidden;position:relative}}</style></head><body>{m.group(1)}</body></html>')
        (tmp / f.name).write_text(page)
        pages[f.stem] = f.name
    return tmp, pages


SEEK_JS = r"""((t) => { const root = document.querySelector('[data-composition-id]');
  const tl = window.__timelines[root.dataset.compositionId]; tl.seek(t, false);
  return { scene: root.dataset.compositionId, kind: root.getAttribute('data-scene-kind') }; })"""


def frame_time(t, fps):
    return math.floor(t * fps + 1e-6) / fps


def scene_at(timing, t):
    return next((s for s in timing["scenes"] if s["start"] <= t + 1e-6 < s["end"]), timing["scenes"][-1])


def check_points(scene):
    """The scene's midpoint and its settled point (after its drawing finishes), local seconds (as frames.py)."""
    last = round(scene["duration"] - 1 / 30, 3)
    shown = scene.get("shown", scene["start"])
    settled = min(max(round(shown - scene["start"] + 0.05, 3), round(scene["duration"] / 2, 3)), last)
    return {"mid": round(scene["duration"] / 2, 3), "settled": settled}


_PROBES = {}


def probe_video(video_dir, timing, samples, name, lesson_sha=None):
    """{label: extraction} for samples [(label, video time)], each from the scene on screen at that frame."""
    key = (str(video_dir), tuple(samples))
    if key in _PROBES:
        return _PROBES[key]
    fps = timing.get("fps", 30)
    tmp, pages = _harness(video_dir)
    per = {}
    for label, t in samples:
        ft = frame_time(t, fps)
        sc = scene_at(timing, ft)
        per.setdefault(sc["id"], []).append((label, round(ft - sc["start"], 4)))
    out = {}
    try:
        with visual.LocalServer(tmp) as srv:
            jobs = []
            for sid, rows in per.items():
                if sid not in pages:
                    for label, _ in rows:
                        out[label] = {"error": f"no composition page for {sid}"}
                    continue
                steps = [{"waitFor": "window.__timelines && Object.keys(window.__timelines).length > 0", "timeout": 20000}]
                for label, local in rows:
                    steps += [{"eval": f"{SEEK_JS}({local})", "as": f"s:{label}"},
                              extract_step({"W": 1920, "H": 1080}, f"m:{label}")]
                jobs.append({"id": sid, "type": "script", "url": f"{srv.url}/{pages[sid]}", "width": 1920,
                             "height": 1080, "steps": steps})
            res = shoot(jobs, name, lesson_sha)
        for r in res["results"]:
            vals = r.get("values") or {}
            for label, local in per[r["id"]]:
                m = vals.get(f"m:{label}")
                if not r.get("ok") or not m:
                    out[label] = {"error": (r.get("error") or "no values")[:500]}
                else:
                    m["scene"], m["local"], m["scene_kind"] = r["id"], local, (vals.get(f"s:{label}") or {}).get("kind")
                    out[label] = m
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    _PROBES[key] = out
    return out


# ---------------------------------------------------------------- spoken words

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]


def int_words(n):
    """English words for a non-negative integer, as a TTS voice reads it ("sixty six" is 2 words)."""
    if n < 20:
        return 1
    if n < 100:
        return 1 + (n % 10 != 0)
    if n < 1000:
        return 2 + (int_words(n % 100) if n % 100 else 0)
    for size in (10 ** 12, 10 ** 9, 10 ** 6, 10 ** 3):
        if n >= size:
            return int_words(n // size) + 1 + (int_words(n % size) if n % size else 0)
    return 1


NUM_TOKEN = re.compile(r"^([-+−]?)(\d+)(?:\.(\d+))?$")


def token_words(tok):
    """Spoken words in one whitespace token of a TTS input: number tokens are expanded as read aloud, a
    hyphenated token counts each part ("print-f" is 2)."""
    tok = tok.strip(".,;:!?\"'()[]")
    if not tok:
        return 0
    m = NUM_TOKEN.match(tok)
    if m:
        n = (1 if m.group(1) else 0) + int_words(int(m.group(2)))
        if m.group(3) is not None:
            n += 1 + len(m.group(3))  # "point" and one word per digit
        return n
    parts = [p for p in re.split(r"-", tok) if re.search(r"[A-Za-z0-9]", p)]
    return sum(token_words(p) if NUM_TOKEN.match(p) else 1 for p in parts) or (1 if re.search(r"[A-Za-z0-9]", tok) else 0)


def spoken_word_count(s):
    return sum(token_words(t) for t in (s or "").split())
