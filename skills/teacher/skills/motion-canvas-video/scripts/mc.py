#!/usr/bin/env python3
"""mc.py: the Motion Canvas side of the pipeline (set up, build, stills, bench, render, editor).

Motion Canvas has no render CLI. The template ships a headless render page (source/render.html +
src/render.ts) that drives the same Renderer the editor's Render button uses and implements the
capture.mjs page contract, so the shared capturer does segments, resume, the time budget, stills and
the benchmark. Frames are pixel-identical to the editor's own export.

  python3 mc.py setup  --project .          copy assets/template to source/ (if absent) and npm ci
  python3 mc.py build  --project .          typecheck + vite build to source/dist (skipped when nothing changed)
  python3 mc.py stills --project . [--at lines|chapters|12.5,30]   review stills into stills/ + a sheet
  python3 mc.py bench  --project . [--seconds 3] [--workers N]
  python3 mc.py render --project . [--workers N] [--max-minutes 100] [--segment 20]
  python3 mc.py editor --project .          the Motion Canvas editor with the voice (laptop preview)

render exits 3 when it stops at the time budget: run the same command again and it resumes
(build/segments/manifest.json records finished segments). Any change to the built page restarts the
segments, so build only changes when source/ changes.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

S = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(S)
TEMPLATE = os.path.join(SKILL, "assets", "template")
CAPTURE = os.path.join(S, "capture.mjs")
STATE = ".video-state.json"
# the Motion Canvas plugin loads Vite through its CommonJS entry; the deprecation notice is noise here
os.environ.setdefault("VITE_CJS_IGNORE_WARNING", "true")
HASH_INPUTS = ("src", "public", "render.html", "vite.config.ts", "package.json", "package-lock.json", "tsconfig.json")


# ----------------------------------------------------------------------------- project paths
class Proj:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        st = os.path.join(self.root, STATE)
        self.state = json.load(open(st)) if os.path.exists(st) else {"config": {}}
        c = self.state.get("config", {})
        self.src = self.p(c.get("source", "source"))
        self.stills = self.p(c.get("stills", "stills"))
        self.silent = self.p(c.get("silent", "build/silent.mp4"))
        self.timing = self.p("timing.json")
        t = json.load(open(self.timing)) if os.path.exists(self.timing) else {}
        self.fps = int(c.get("fps") or t.get("fps") or 30)
        self.width = int(c.get("width") or t.get("width") or 1920)
        self.height = int(c.get("height") or t.get("height") or 1080)
        if t and (t.get("fps"), t.get("width"), t.get("height")) != (self.fps, self.width, self.height):
            print(f"warning: timing.json says {t.get('width')}x{t.get('height')}@{t.get('fps')} but the project is "
                  f"{self.width}x{self.height}@{self.fps}; set script meta to match", file=sys.stderr)

    def p(self, *parts):
        return os.path.join(self.root, *parts)

    @property
    def page(self):
        return os.path.join(self.src, "dist", "render.html")


def run(cmd, cwd, check=True, **kw):
    print("$ " + " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd, **kw)
    if check and r.returncode != 0:
        sys.exit(r.returncode)
    return r


def need(tool, hint):
    if not shutil.which(tool):
        sys.exit(f"{tool} not found. {hint}")


def tree_hash(root, names):
    h = hashlib.sha1()
    for n in names:
        p = os.path.join(root, n)
        files = []
        if os.path.isdir(p):
            for dp, dn, fn in os.walk(p):
                dn[:] = sorted(d for d in dn if d not in ("node_modules", "dist", "output"))
                files += [os.path.join(dp, f) for f in sorted(fn)]
        elif os.path.isfile(p):
            files = [p]
        for f in files:
            h.update(os.path.relpath(f, root).encode() + b"\0")
            with open(f, "rb") as fh:
                h.update(hashlib.sha1(fh.read()).digest())
    return h.hexdigest()


# ----------------------------------------------------------------------------- commands
def cmd_setup(pr, a):
    need("node", "Install Node 18+ (node 22 is what this was tested with).")
    need("npm", "Install npm (it comes with Node).")
    if not os.path.isdir(pr.src):
        shutil.copytree(TEMPLATE, pr.src, ignore=shutil.ignore_patterns("node_modules", "dist", "output"))
        print(f"copied the template to {os.path.relpath(pr.src, pr.root)}/")
    else:
        print(f"{os.path.relpath(pr.src, pr.root)}/ exists: keeping it (delete it to start from the template again)")
    stamp = os.path.join(pr.src, "node_modules", ".mc-lock")
    lock = tree_hash(pr.src, ("package-lock.json",))
    if os.path.exists(stamp) and open(stamp).read() == lock and not a.force:
        print("node_modules is up to date with package-lock.json")
        return
    t0 = time.time()
    # --legacy-peer-deps: the template pins Vite 6.4.4 (security fix) while the plugin still declares "4.x || 5.x"
    run(["npm", "ci", "--legacy-peer-deps", "--no-audit", "--no-fund", "--loglevel=error"], cwd=pr.src)
    with open(stamp, "w") as f:
        f.write(lock)
    print(f"npm ci took {time.time() - t0:.0f} s")


def ensure_installed(pr):
    if not os.path.isdir(pr.src):
        sys.exit(f"no {pr.src}: run  python3 {S}/mc.py setup --project {pr.root}")
    if not os.path.isdir(os.path.join(pr.src, "node_modules", "@motion-canvas", "core")):
        sys.exit(f"dependencies missing: run  python3 {S}/mc.py setup --project {pr.root}")


def cmd_build(pr, a, quiet=False):
    ensure_installed(pr)
    h = tree_hash(pr.src, HASH_INPUTS)
    mark = os.path.join(pr.src, "dist", ".mc-build")
    if os.path.exists(pr.page) and os.path.exists(mark) and open(mark).read() == h and not getattr(a, "force", False):
        if not quiet:
            print("build is up to date (source/ unchanged)")
        return
    t0 = time.time()
    if not getattr(a, "no_typecheck", False):
        tsc = os.path.join(pr.src, "node_modules", "typescript", "bin", "tsc")
        r = run(["node", tsc, "--noEmit", "-p", "."], cwd=pr.src, check=False)
        if r.returncode != 0:
            sys.exit("typecheck failed (errors above). Fix them, or pass --no-typecheck to build anyway.")
    run(["node", os.path.join(pr.src, "node_modules", "vite", "bin", "vite.js"), "build", "--logLevel", "warn"], cwd=pr.src)
    if not os.path.exists(pr.page):
        sys.exit("vite build did not produce dist/render.html")
    with open(mark, "w") as f:
        f.write(h)
    print(f"built source/dist in {time.time() - t0:.1f} s")


PROBLEM = re.compile(r"\[timing\]|\[motion-canvas|page error|console:")


def capture(pr, args):
    """Run capture.mjs, echo its output, and collect timing/scene problems the page reported."""
    cmd = ["node", CAPTURE, "--page", pr.page] + args
    print("$ " + " ".join(cmd), flush=True)
    problems = []
    proc = subprocess.Popen(cmd, cwd=pr.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        if PROBLEM.search(line) and "favicon" not in line:
            problems.append(line.rstrip())
    proc.wait()
    return proc.returncode, problems


def report_problems(problems):
    if not problems:
        return
    uniq = list(dict.fromkeys(problems))
    print(f"\n{len(uniq)} problem(s) reported by the scenes:")
    for p in uniq[:20]:
        print("  " + p)
    print("[timing] late: an animation awaited with yield* ran past the next cue; start it with `yield` "
          "(spawn) or shorten it. Errors: fix the scene code.")


def tile_sheet(images, out, cols=4, w=480):
    if not images or not shutil.which("ffmpeg"):
        return None
    rows = (len(images) + cols - 1) // cols
    h = w * 9 // 16
    inputs, filt = [], []
    for i, f in enumerate(images):
        inputs += ["-i", f]
        filt.append(f"[{i}:v]scale={w}:{h}[s{i}]")
    pads = len(images)
    lay = "|".join(f"{(i % cols) * w}_{(i // cols) * h}" for i in range(len(images)))
    filt.append("".join(f"[s{i}]" for i in range(pads)) + f"xstack=inputs={pads}:layout={lay}:fill=black[out]"
                if pads > 1 else "[s0]copy[out]")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(filt), "-map", "[out]",
                        "-frames:v", "1", "-q:v", "3", out])
    return out if r.returncode == 0 else None


def cmd_stills(pr, a):
    cmd_build(pr, a, quiet=True)
    os.makedirs(pr.stills, exist_ok=True)
    if not a.keep:
        for f in os.listdir(pr.stills):
            if f.lower().endswith((".jpg", ".png")):
                os.remove(os.path.join(pr.stills, f))
    args = ["--stills", a.at, "--stills-dir", pr.stills, "--width", str(pr.width), "--height", str(pr.height)]
    if a.at in ("lines", "chapters"):
        if not os.path.exists(pr.timing):
            sys.exit("no timing.json yet: run the voice phase first")
        args += ["--timing", pr.timing]
    code, problems = capture(pr, args)
    if code != 0:
        sys.exit(code)
    imgs = sorted(os.path.join(pr.stills, f) for f in os.listdir(pr.stills) if f.endswith(".jpg"))
    sheet = tile_sheet(imgs, pr.p("build", "stills-sheet.jpg"))
    print(f"\n{len(imgs)} stills in {os.path.relpath(pr.stills, pr.root)}/" + (f"; overview: {os.path.relpath(sheet, pr.root)}" if sheet else ""))
    print("Open the sheet, then every still, with the Read tool before attesting.")
    report_problems(problems)


def cmd_bench(pr, a):
    cmd_build(pr, a, quiet=True)
    code, problems = capture(pr, ["--bench", str(a.seconds), "--fps", str(pr.fps), "--width", str(pr.width),
                                  "--height", str(pr.height)] + (["--workers", str(a.workers)] if a.workers else []))
    report_problems(problems)
    sys.exit(code)


def cmd_render(pr, a):
    cmd_build(pr, a, quiet=False)
    os.makedirs(os.path.dirname(pr.silent), exist_ok=True)
    args = ["--out", pr.silent, "--fps", str(pr.fps), "--width", str(pr.width), "--height", str(pr.height),
            "--max-minutes", str(a.max_minutes), "--segment", str(a.segment)]
    if a.workers:
        args += ["--workers", str(a.workers)]
    man = os.path.join(os.path.dirname(pr.silent), "segments", "manifest.json")
    t0 = time.time()
    code, problems = capture(pr, args)
    el = time.time() - t0
    if os.path.exists(man):
        m = json.load(open(man))
        done = sum(1 for s in m["segments"] if s.get("done"))
        frames = sum(s["b"] - s["a"] for s in m["segments"])
        print(f"segments done: {done}/{len(m['segments'])} ({frames} frames total); this run {el / 60:.1f} min")
    report_problems(problems)
    if code == 3:
        print("Stopped at the time budget. Run the same command again: finished segments are kept.")
    sys.exit(code)


def cmd_editor(pr, a):
    ensure_installed(pr)
    print("Motion Canvas editor on http://127.0.0.1:%d/  (voice from voice/narration.wav; Ctrl+C stops it)" % a.port,
          flush=True)
    os.chdir(pr.src)
    os.execvp("node", ["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", str(a.port)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, **kw):
        p = sub.add_parser(name, **kw)
        p.add_argument("--project", default=".")
        return p

    p = add("setup", help="copy the template to source/ and install dependencies")
    p.add_argument("--force", action="store_true", help="reinstall node_modules")
    p = add("build", help="typecheck and build the headless render page")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-typecheck", action="store_true")
    p = add("stills", help="render review stills")
    p.add_argument("--at", default="lines", help="lines (one per line, default) | chapters | comma-separated seconds")
    p.add_argument("--keep", action="store_true", help="keep earlier stills in the folder")
    p.add_argument("--no-typecheck", action="store_true")
    p = add("bench", help="time a few seconds of frames and print the full-film ETA")
    p.add_argument("--seconds", type=float, default=3)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--no-typecheck", action="store_true")
    p = add("render", help="segmented, resumable render of build/silent.mp4")
    p.add_argument("--workers", type=int, default=0, help="parallel browsers (default: up to 4, one per CPU)")
    p.add_argument("--max-minutes", type=float, default=100, help="stop cleanly after this many minutes (exit 3)")
    p.add_argument("--segment", type=float, default=20, help="segment length in seconds")
    p.add_argument("--no-typecheck", action="store_true")
    p = add("editor", help="run the Motion Canvas editor (preview with the voice)")
    p.add_argument("--port", type=int, default=9000)
    a = ap.parse_args()
    pr = Proj(a.project)
    {"setup": cmd_setup, "build": cmd_build, "stills": cmd_stills, "bench": cmd_bench, "render": cmd_render,
     "editor": cmd_editor}[a.cmd](pr, a)


if __name__ == "__main__":
    main()
