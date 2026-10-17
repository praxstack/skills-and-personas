#!/usr/bin/env python3
"""Build a course (a folder with course.json and lesson files) into a static site.

  python3 build_course.py courses/segment-tree -o site/segment-tree [--fragment]
  python3 build_course.py --catalog courses/ -o site/        # every course plus a catalog page

Writes one page per lesson (explorable or concept animation, with the
course's shared model included), the course page (map, outline, notes,
quiz) as index.html, and copies narrated videos from the course's videos/
folder (videos/<lesson-id>.mp4 with its .vtt). Every page is one
self-contained HTML file, so the folder can be served from anywhere or opened
from disk.
"""

from __future__ import annotations

import argparse
import html
import json
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

ENGINE = HERE.parent / "assets" / "engine"
ANIM = SKILLS / "concept-animation" / "scripts"


def extract(course_dir: Path) -> dict:
    out = subprocess.run(["node", str(HERE / "extract.mjs"), str(course_dir)], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(f"extract failed for {course_dir}:\n{out.stderr}")
    return json.loads(out.stdout)


def build_course(course_dir: Path, out: Path, fragment: bool = False, titles: dict | None = None) -> dict:
    data = extract(course_dir)
    out.mkdir(parents=True, exist_ok=True)
    shared = [course_dir / s for s in data.get("shared", [])]
    for ident in [data.get("id", "course"), *(l["id"] for l in data["lessons"])]:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", str(ident)):
            raise SystemExit(f"{course_dir}: id {ident!r} may use only letters, digits, - and _ (it becomes a file name)")
    for lesson in data["lessons"]:
        src = course_dir / lesson["file"]
        page = f"{lesson['id']}.html"
        if lesson["kind"] == "animation":
            r = subprocess.run([sys.executable, str(ANIM / "build.py"), str(src), "-o", str(out / page), *(["--fragment"] if fragment else []),
                                *[x for s in shared for x in ("--include", str(s))]], capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(r.stderr)
        else:
            explorable_build.build(src, out / page, fragment, shared)
        lesson["page"] = page
        video = course_dir / "videos" / f"{lesson['id']}.mp4"
        vtt = video.with_suffix(".vtt")
        if video.exists() and not vtt.exists():
            print(f"skipping {video.name}: no {vtt.name} next to it, and a narrated video needs captions", file=sys.stderr)
        elif video.exists():
            (out / "videos").mkdir(exist_ok=True)
            shutil.copy2(video, out / "videos" / video.name)
            shutil.copy2(vtt, out / "videos" / vtt.name)
            lesson["video"] = f"videos/{video.name}"
    data["prereqTitles"] = titles or {}
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write("window.COURSE = " + json.dumps(data).replace("</", "<\\/") + ";\n")
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
    return data


CATALOG_CSS = ENGINE / "course.css"


def build_catalog(root: Path, out: Path, fragment: bool = False) -> None:
    dirs = sorted(d for d in root.iterdir() if (d / "course.json").exists())
    metas = {d.name: json.loads((d / "course.json").read_text()) for d in dirs}
    titles = {m["id"]: m["title"] for m in metas.values()}
    built = []
    for d in dirs:
        data = build_course(d, out / metas[d.name]["id"], fragment, titles)
        built.append(data)
        print(f"built {data['id']}: {len(data['lessons'])} lessons")
    # Courses a learner should take first come first; each card links both ways.
    order: list[dict] = []
    pending = list(built)
    while pending:
        ready = [c for c in pending if all(p in {o["id"] for o in order} or p not in titles for p in c.get("prereqs", []))] or pending[:1]
        order.append(ready[0])
        pending.remove(ready[0])
    link = lambda cid: f'<a href="{html.escape(cid)}/index.html">{html.escape(titles.get(cid, cid))}</a>'
    cards = []
    for c in order:
        needs = ", ".join(link(p) for p in c.get("prereqs", []) if p in titles)
        leads = ", ".join(link(o["id"]) for o in order if c["id"] in o.get("prereqs", []))
        videos = sum(1 for l in c["lessons"] if l.get("video"))
        meta = f'{len(c["lessons"])} lessons · about {sum(l.get("minutes", 10) for l in c["lessons"])} min' + (f" · {videos} narrated videos" if videos else "")
        cards.append(
            f'<article class="cs-card nb-sheet"><p class="nb-label">{html.escape(c.get("level", ""))}</p>'
            f'<a class="cs-title" href="{html.escape(c["id"])}/index.html">{html.escape(c["title"])}</a>'
            f'<p class="cs-sub">{html.escape(c.get("subtitle", ""))}</p>'
            f'<p class="nb-print">{meta}</p>'
            + (f'<p class="nb-print">builds on {needs}</p>' if needs else "")
            + (f'<p class="nb-print">leads to {leads}</p>' if leads else "")
            + "</article>"
        )
    body = (
        '<main id="app"><header class="cs-head"><p class="nb-label">Kai Mori</p><h1>Courses</h1>'
        '<p class="cs-sub">Pick a subject. Every lesson lets you move the idea yourself, watch it, read and run the code, and quiz yourself, as many times and in as many ways as you like.</p></header>'
        f'<section class="cs-catalog">{"".join(cards)}</section></main>'
    )
    page = bundle.page(title="Kai Mori Courses", description="Interactive courses with films, code and quizzes.", css=[bundle.NOTEBOOK_CSS, CATALOG_CSS],
                       modules=[*bundle.NOTEBOOK_MODULES], body=body, fragment=fragment)
    (out / "index.html").write_text(page)
    print(f"wrote {out / 'index.html'}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course", type=Path, help="a course folder, or the folder of courses with --catalog")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--catalog", action="store_true")
    ap.add_argument("--fragment", action="store_true")
    a = ap.parse_args()
    if a.catalog:
        build_catalog(a.course, a.out, a.fragment)
    else:
        data = build_course(a.course, a.out, a.fragment)
        print(f"built {data['id']}: {len(data['lessons'])} lessons into {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
