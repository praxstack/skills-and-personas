#!/usr/bin/env python3
"""Build a course (a folder with course.json and lesson files) into a static site.

  python3 build_course.py courses/segment-tree -o site/segment-tree [--fragment]
  python3 build_course.py --catalog courses/ -o site/        # every course plus a catalog page
  python3 build_course.py --catalog courses/ -o public/courses --base /courses/   # for a host

Links are relative by default, so the pages work from disk and as standalone
files. --base gives the URL path the output folder is served at, and makes
every link root-absolute: a host with clean URLs serves /courses/ai-math/
as /courses/ai-math (no trailing slash), where relative links would point
one folder too high.

Writes one page per lesson (explorable or concept animation, with the
course's shared model included), the course page (map, outline, notes,
quiz) as index.html, and the narrated videos' .vtt captions. Every page is
one self-contained HTML file, so the folder can be served from anywhere or
opened from disk.

Narrated videos: a lesson's video is courses/<id>/videos/<lesson-id>.mp4
when that file exists (copied next to the pages, for local previews), else
the URL for "<course-id>/<lesson-id>.mp4" in courses/videos.json (the MP4s
live in Vercel Blob, see publish_videos.mjs), else the lesson has no video
button. The captions always come from videos/<lesson-id>.vtt in git and are
served beside the pages.

--video-url TEMPLATE points the pages at the host's own video route instead of
the Blob URL, e.g. --video-url "/api/watch?v={course}/{lesson}", so the host
decides who gets each video (Kai Mori's paywall does). Local MP4s are unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent
sys.path.insert(0, str(SKILLS / "lesson-notebook" / "scripts"))
sys.path.insert(0, str(SKILLS / "explorable" / "scripts"))
import bundle  # noqa: E402
import build as explorable_build  # noqa: E402
from safe_course import safe_lesson_id, optional_confined_file, validate_course_manifest, private_course_inputs  # noqa: E402

ENGINE = HERE.parent / "assets" / "engine"
ANIM = SKILLS / "concept-animation" / "scripts"


def extract(course_dir: Path, trust_authored_code: bool = False) -> dict:
    cmd = ["node", str(HERE / "extract.mjs"), str(course_dir)]
    if trust_authored_code:
        cmd.append("--trust-authored-code")
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(f"extract failed for {course_dir}:\n{out.stderr}")
    return json.loads(out.stdout)


def norm_base(base: str) -> str:
    """'' stays '' (relative links); anything else becomes '/a/b/'."""
    return "/" + base.strip("/") + "/" if base.strip("/") else ("/" if base else "")


def logical_path(p: Path) -> Path:
    """p made absolute without following symlinks. os.getcwd() is always the real
    folder, so a relative path starts from $PWD (the folder as the shell reached
    it, links and all) when that is the same folder."""
    base = os.getcwd()
    pwd = os.environ.get("PWD", "")
    try:
        if os.path.isabs(pwd) and os.path.samefile(pwd, base):
            base = pwd
    except OSError:
        pass
    return Path(os.path.normpath(os.path.join(base, p)))


def load_manifest(course_dir: Path) -> dict:
    """courses/videos.json: {"<course-id>/<lesson-id>.mp4": "https://...", ...}; empty values allowed."""
    f = logical_path(course_dir).parent / "videos.json"  # so "." finds the parent, and a linked course reads the one beside the link
    return json.loads(f.read_text()) if f.exists() else {}


def resolve_video(course_dir: Path, course_id: str, lesson_id: str, manifest: dict) -> tuple[str, str | Path] | None:
    """Where a lesson's narrated video comes from: ("local", path) when the MP4 is on
    disk, else ("url", url) from the manifest, else None (no video button)."""
    local = optional_confined_file(course_dir, Path("videos") / f"{lesson_id}.mp4", "lesson video")
    if local is not None:
        return ("local", local)
    url = (manifest.get(f"{course_id}/{lesson_id}.mp4") or "").strip()
    return ("url", url) if url.startswith("https://") else None


def unpublished_change(course_dir: Path, course_id: str, lesson_id: str, manifest: dict) -> str | None:
    """A warning when the local MP4 isn't the one on Blob: its sha256 doesn't
    start with the digest in the manifest URL (publish_videos.mjs names uploads
    <lesson-id>.<sha8>.mp4), so the site would serve the old video next to the
    new captions until publish:videos runs again. None when they match, or
    when there's no local MP4 or no URL to compare."""
    local = optional_confined_file(course_dir, Path("videos") / f"{lesson_id}.mp4", "lesson video")
    url = (manifest.get(f"{course_id}/{lesson_id}.mp4") or "").strip()
    if local is None or not url:
        return None
    h = hashlib.sha256()
    with local.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    m = re.search(r"\.([0-9a-f]{8})\.mp4$", url.split("?")[0])
    if m and m.group(1) == h.hexdigest()[:8]:
        return None
    return f"local {local.name} isn't the video on Blob; run npm run publish:videos"


def video_route(template: str, course_id: str, lesson_id: str) -> str:
    """The host's URL for a Blob-hosted video, from a --video-url template."""
    return template.replace("{course}", course_id).replace("{lesson}", lesson_id)


@private_course_inputs
def build_course(course_dir: Path, out: Path, fragment: bool = False, titles: dict | None = None, base: str = "", root: str = "", video_url: str = "", trust_authored_code: bool = False) -> dict:
    """base: URL path this course's folder is served at ('' for relative links);
    root: the URL path of the catalog that holds it (for prerequisite links);
    video_url: a --video-url template for Blob-hosted videos ('' for the Blob URL)."""
    base, root = norm_base(base), norm_base(root)
    try:
        validated = validate_course_manifest(course_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"unsafe course manifest in {course_dir}: {exc}")
    course_dir = validated.root
    data = extract(course_dir, trust_authored_code)
    if data.get("id") != validated.data.get("id") or {row.get("id") for row in data.get("lessons", [])} != set(validated.lessons):
        raise SystemExit(f"{course_dir}: extracted course identity differs from the validated manifest")
    for ident in [data.get("id", "course"), *(l["id"] for l in data["lessons"])]:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", str(ident)):
            raise SystemExit(f"{course_dir}: id {ident!r} may use only letters, digits, - and _ (it becomes a file name)")
    out.mkdir(parents=True, exist_ok=True)
    shared = list(validated.shared)
    manifest = load_manifest(course_dir)
    stale = []
    for lesson in data["lessons"]:
        src = validated.lessons[lesson["id"]]
        try:
            page = f"{safe_lesson_id(lesson['id'])}.html"
        except ValueError as exc:
            raise SystemExit(str(exc)) from None
        if lesson["kind"] == "animation":
            r = subprocess.run([sys.executable, str(ANIM / "build.py"), str(src), "-o", str(out / page), *(["--fragment"] if fragment else []), *[x for f in shared for x in ("--include", str(f))]], capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(r.stderr)
        else:
            explorable_build.build(src, out / page, fragment, shared)
        lesson["page"] = page
        found = resolve_video(course_dir, data["id"], lesson["id"], manifest)
        if not found or found[0] != "local":
            # An earlier build may have copied the local MP4 here; it's on Blob now
            # (or gone), and a left-over copy would still be served beside the page.
            stale.append(out / "videos" / f"{lesson['id']}.mp4")
        if found:
            (out / "videos").mkdir(exist_ok=True)
            kind, where = found
            if kind == "local":
                shutil.copy2(where, out / "videos" / where.name)
                lesson["video"] = f"{base}videos/{where.name}"
            else:
                lesson["video"] = video_route(video_url, data["id"], lesson["id"]) if video_url else where
            # Captions stay same-origin even when the video is on Blob. A video
            # without them isn't offered: narrate.py writes the .vtt beside the MP4.
            vtt = optional_confined_file(course_dir, Path("videos") / f"{lesson['id']}.vtt", "video captions")
            if vtt is None:
                raise SystemExit(f"{data['id']}/{lesson['id']}: the lesson has a video but no safe captions file")
            shutil.copy2(vtt, out / "videos" / vtt.name)
            lesson["captions"] = f"{base}videos/{vtt.name}"
    data["prereqTitles"] = titles or {}
    data["base"] = base
    data["root"] = root
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write("window.COURSE = " + json.dumps(data).replace("<", "\\u003c") + ";\n")
        data_js = Path(f.name)
    try:
        page = bundle.page(
            title=data["title"],
            description=data.get("subtitle", ""),
            css=[bundle.NOTEBOOK_CSS, ENGINE / "course.css"],
            modules=[*bundle.NOTEBOOK_MODULES, ENGINE / "course.js"],
            scripts=[data_js],
            body='<main id="app"><noscript><p>This course map needs JavaScript. The lessons are the other HTML files in this folder.</p></noscript></main>',
            fragment=fragment,
        )
    finally:
        data_js.unlink()
    (out / "index.html").write_text(page)
    # Only now: had a later lesson failed, the old index would still link these.
    for f in stale:
        f.unlink(missing_ok=True)
    return data


CATALOG_CSS = ENGINE / "course.css"


DEFAULT_BRAND = "Kai Mori"


def build_catalog(root: Path, out: Path, fragment: bool = False, base: str = "", brand: str = DEFAULT_BRAND, video_url: str = "", trust_authored_code: bool = False) -> None:
    """brand: the name over the catalog and in its title ("" for none)."""
    base = norm_base(base)
    root = root.resolve(strict=True)
    dirs = sorted(d for d in root.iterdir() if d.is_dir() and not d.is_symlink() and (d / "course.json").exists())
    try:
        checked = {d: validate_course_manifest(d) for d in dirs}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"unsafe course in catalog {root}: {exc}")
    metas = {d.name: checked[d].data for d in dirs}
    titles = {m["id"]: m["title"] for m in metas.values()}
    built = []
    for d in dirs:
        cid = metas[d.name]["id"]
        data = build_course(d, out / cid, fragment, titles, base=f"{base}{cid}/" if base else "", root=base, video_url=video_url, trust_authored_code=trust_authored_code)
        built.append(data)
        print(f"built {data['id']}: {len(data['lessons'])} lessons")
    # Courses a learner should take first come first; each card links both ways.
    order: list[dict] = []
    pending = list(built)
    while pending:
        ready = [c for c in pending if all(p in {o["id"] for o in order} or p not in titles for p in c.get("prereqs", []))] or pending[:1]
        order.append(ready[0])
        pending.remove(ready[0])
    href = lambda cid: f"{base}{cid}" if base else f"{cid}/index.html"
    link = lambda cid: f'<a href="{html.escape(href(cid))}">{html.escape(titles.get(cid, cid))}</a>'
    cards = []
    for c in order:
        needs = ", ".join(link(p) for p in c.get("prereqs", []) if p in titles)
        leads = ", ".join(link(o["id"]) for o in order if c["id"] in o.get("prereqs", []))
        videos = sum(1 for l in c["lessons"] if l.get("video"))
        meta = f'{len(c["lessons"])} lessons · about {sum(l.get("minutes", 10) for l in c["lessons"])} min' + (f" · {videos} narrated videos" if videos else "")
        cards.append(
            f'<article class="cs-card nb-sheet"><p class="nb-label">{html.escape(c.get("level", ""))}</p>'
            f'<a class="cs-title" href="{html.escape(href(c["id"]))}">{html.escape(c["title"])}</a>'
            f'<p class="cs-sub">{html.escape(c.get("subtitle", ""))}</p>'
            f'<p class="nb-print">{meta}</p>'
            + (f'<p class="nb-print">builds on {needs}</p>' if needs else "")
            + (f'<p class="nb-print">leads to {leads}</p>' if leads else "")
            + "</article>"
        )
    # Standalone lessons (a page of their own, not built from a course.json)
    # get a card too: <root>/links.json is a list of
    # {"href", "title", "subtitle", "level", "meta"}.
    links = root / "links.json"
    extra = json.loads(links.read_text()) if links.exists() else []
    if not isinstance(extra, list) or not all(isinstance(c, dict) and c.get("href") and c.get("title") for c in extra):
        raise SystemExit(f"{links}: expected a list of objects, each with an href and a title")
    for c in extra:
        if not (re.match(r"/(?![/\\])", c["href"]) or c["href"].startswith("https://")):
            raise SystemExit(f"{links}: href {c['href']!r} must be a path on this site (/...) or start with https://")
        cards.append(
            f'<article class="cs-card nb-sheet"><p class="nb-label">{html.escape(c.get("level", ""))}</p>'
            f'<a class="cs-title" href="{html.escape(c["href"])}">{html.escape(c["title"])}</a>'
            f'<p class="cs-sub">{html.escape(c.get("subtitle", ""))}</p>'
            + (f'<p class="nb-print">{html.escape(c["meta"])}</p>' if c.get("meta") else "")
            + "</article>"
        )
    body = (
        '<main id="app"><header class="cs-head">' + (f'<p class="nb-label">{html.escape(brand)}</p>' if brand else "") + '<h1>Courses</h1>'
        '<p class="cs-sub">Pick a subject. Every lesson lets you move the idea yourself, watch it, read and run the code, and quiz yourself, as many times and in as many ways as you like.</p></header>'
        f'<section class="cs-catalog">{"".join(cards)}</section></main>'
    )
    out.mkdir(parents=True, exist_ok=True)  # a links.json-only catalog builds no course folder first
    page = bundle.page(title=f"{brand} Courses" if brand else "Courses", description="Interactive courses with films, code and quizzes.", css=[bundle.NOTEBOOK_CSS, CATALOG_CSS],
                       modules=[*bundle.NOTEBOOK_MODULES], body=body, fragment=fragment)
    (out / "index.html").write_text(page)
    print(f"wrote {out / 'index.html'}")


def add_icon(out: Path, href: str) -> int:
    """Link a site icon from every built page's <head> (the host's own icon,
    e.g. /favicon.svg), so browsers don't ask for a missing /favicon.ico."""
    link = f'<link rel="icon" href="{html.escape(href)}" type="image/svg+xml">\n'
    n = 0
    for f in out.rglob("*.html"):
        text = f.read_text()
        if 'rel="icon"' in text or "</head>" not in text:
            continue
        f.write_text(text.replace("</head>", link + "</head>", 1))
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course", type=Path, help="a course folder, or the folder of courses with --catalog")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--catalog", action="store_true")
    ap.add_argument("--fragment", action="store_true")
    ap.add_argument("--base", default="", help="URL path the output folder is served at, e.g. /courses/ (default: relative links)")
    ap.add_argument("--root", default="", help="with a single course and --base: the URL path of its catalog, for prerequisite links")
    ap.add_argument("--brand", default=DEFAULT_BRAND, help=f"with --catalog: the name over the catalog page (default: {DEFAULT_BRAND}; \"\" for none)")
    ap.add_argument("--video-url", default="", help='URL template for Blob-hosted videos, e.g. "/api/watch?v={course}/{lesson}" (default: the Blob URL)')
    ap.add_argument("--icon", default="", help="URL of an SVG site icon to link from every page, e.g. /favicon.svg")
    ap.add_argument("--trust-authored-code", action="store_true", help="after review, allow lesson JavaScript to execute during extraction")
    a = ap.parse_args()
    if a.catalog:
        build_catalog(a.course, a.out, a.fragment, a.base, a.brand, a.video_url, a.trust_authored_code)
    else:
        data = build_course(a.course, a.out, a.fragment, base=a.base, root=a.root, video_url=a.video_url, trust_authored_code=a.trust_authored_code)
        print(f"built {data['id']}: {len(data['lessons'])} lessons into {a.out}")
    if a.icon and not a.fragment:
        add_icon(a.out, a.icon)
    return 0


if __name__ == "__main__":
    sys.exit(main())
