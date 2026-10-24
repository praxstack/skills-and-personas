#!/usr/bin/env python3
"""render_manim.py: render the Manim film as resumable segments, in parallel, and join them frame-exactly.

Each FilmScene subclass in source/scenes.py is one segment (usually one chapter). Its time span comes from the
voice timing, so segment i covers exactly [from, to) of the film and the joined video matches the voice to the
frame. Segments render in parallel, each with its own --media_dir (Manim's shared text cache races otherwise),
are recorded in build/segments/manifest.json, and are skipped on the next run when nothing they depend on
changed (timing, kit, shared module code, their own class body). The joined result is padded or trimmed to
round(TIMING.total * fps) frames.

Usage (run from anywhere; --project defaults to the current directory):
  python3 render_manim.py --project . --bench                 render the shortest segment, report fps and the ETA
  python3 render_manim.py --project .                         full render -> build/silent.mp4 (1920x1080, 30 fps)
  python3 render_manim.py --project . --draft                 quick check at 854x480 15 fps -> build/draft.mp4
  python3 render_manim.py --project . --stills lines          full-resolution review stills (Manim last-frame mode)
  python3 render_manim.py --project . --stills chapters --from-draft   stills cut from build/draft.mp4 (stills.py)
Options:
  --workers N        parallel Manim processes (default: CPUs, max 4; use 2 on a shared machine)
  --max-minutes M    stop launching segments that would not finish in M minutes, kill at M (default 100);
                     run the same command again to continue
  --only A,B         re-render these segments (by scene name) even if done
  --force            re-render everything
  --python PATH      prefer this Python, then MANIM_PYTHON, project/source venvs, this Python,
                     then a verified absolute Python shebang from the resolved manim CLI
Exit codes: 0 done, 1 error, 3 budget reached (re-run to continue).
"""
import argparse
import concurrent.futures as cf
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def log(*a):
    print(*a, flush=True)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe_frames(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
             "stream=nb_read_packets,width,height,r_frame_rate,codec_name,pix_fmt", "-of", "json", path])
    try:
        s = json.loads(r.stdout)["streams"][0]
    except Exception:  # noqa: BLE001
        return None
    n, d = s["r_frame_rate"].split("/")
    return {"frames": int(s.get("nb_read_packets", 0)), "w": s["width"], "h": s["height"],
            "fps": float(n) / float(d), "codec": s["codec_name"], "pix": s.get("pix_fmt")}


def cli_python():
    """Read a console script's absolute Python shebang; never execute a launcher.

    Resolve the CLI symlink, but retain the interpreter's venv path (resolving
    the Python symlink itself would lose its virtual environment). Shell and
    /usr/bin/env launchers are deliberately unsupported.
    """
    cli = shutil.which("manim")
    if not cli:
        return None
    try:
        with open(os.path.realpath(cli), "rb") as stream:
            line = stream.readline(4096).decode("utf-8").rstrip("\r\n")
    except (OSError, UnicodeError):
        return None
    candidate = line[2:] if line.startswith("#!") else ""
    if (os.path.isabs(candidate)
            and re.fullmatch(r"python(?:[0-9]+(?:\.[0-9]+)*)?", os.path.basename(candidate))
            and os.path.isfile(candidate) and os.access(candidate, os.X_OK)):
        return candidate
    return None


def resolve_python(project, source, given=None):
    """Shared discovery/render selection; a successful import is not render proof."""
    cands = [given, os.environ.get("MANIM_PYTHON"), os.path.join(project, ".venv", "bin", "python"),
             os.path.join(source, ".venv", "bin", "python"), sys.executable]
    # Probe existing module paths first, preserving their precedence.
    for c in cands + [cli_python()]:
        if c and os.path.isfile(c):
            try:
                if run([c, "-c", "import manim"], timeout=10).returncode == 0:
                    return c
            except (OSError, subprocess.SubprocessError):
                pass
    return None


def find_python(project, source, given):
    selected = resolve_python(project, source, given)
    if selected:
        return selected
    sys.exit("no Python with manim found. Set it up (references/manim-guide.md, Setup):\n"
             f"  python3 -m venv {project}/.venv && {project}/.venv/bin/pip install -r {source}/requirements.txt")


def list_segments(py, source, fps):
    code = ("import json, scenes\nfrom kit.film import list_segments\n"
            f"print('SEGJSON' + json.dumps(list_segments(scenes, fps={fps!r})))")
    r = run([py, "-c", code], cwd=source)
    m = re.search(r"SEGJSON(.*)", r.stdout)
    if r.returncode != 0 or not m:
        sys.exit(f"could not import scenes.py:\n{r.stderr[-3000:]}")
    info = json.loads(m.group(1))
    if info["problems"]:
        sys.exit("segments do not tile the film:\n  " + "\n  ".join(info["problems"]))
    return info


def load_manifest(path):
    try:
        with open(path) as source:
            return json.load(source)
    except (OSError, ValueError):
        return {"segments": []}


def save_manifest(path, man, lock):
    with lock:
        tmp = path + ".tmp"
        with open(tmp, "w") as sink:
            json.dump(man, sink, indent=1)
        os.replace(tmp, path)


def fix_frames(src, dst, want, fps, w, h):
    """Re-encode src to exactly `want` frames (clone the last frame or trim)."""
    vf = f"fps={fps},scale={w}:{h}:flags=lanczos,tpad=stop_mode=clone:stop={want},trim=end_frame={want},setpts=N/({fps}*TB)"
    r = run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium",
             "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(fps), dst])
    if r.returncode:
        raise RuntimeError(r.stderr[-800:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 2))
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--draft-quality", default="l", choices=["l", "m"])
    ap.add_argument("--max-minutes", type=float, default=100.0)
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--bench", action="store_true")
    ap.add_argument("--stills", default=None, help="chapters | lines | busy | t1,t2,... (film seconds)")
    ap.add_argument("--from-draft", action="store_true", help="with --stills: cut them from build/draft.mp4")
    ap.add_argument("--out", default=None, help="output video (default build/silent.mp4, draft: build/draft.mp4)")
    ap.add_argument("--python", default=None)
    a = ap.parse_args()

    T0 = time.time()
    budget = a.max_minutes * 60
    project = os.path.abspath(a.project)
    st = {}
    sp = os.path.join(project, ".video-state.json")
    if os.path.exists(sp):
        with open(sp) as source_spec:
            st = json.load(source_spec)
    cfg = st.get("config", {})
    source = os.path.join(project, cfg.get("source", "source"))
    W, H, FPS = int(cfg.get("width", 1920)), int(cfg.get("height", 1080)), int(cfg.get("fps", 30))
    py = find_python(project, source, a.python)

    if a.stills and not a.from_draft:
        return stills_hires(a, project, source, py, W, H, FPS)

    if a.draft:
        W, H, FPS = (854, 480, 15) if a.draft_quality == "l" else (1280, 720, 30)
        quality = ["-ql"] if a.draft_quality == "l" else ["-qm"]
        bdir = os.path.join(project, "build", "draft")
        out = a.out or os.path.join(project, "build", "draft.mp4")
    else:
        quality = ["-r", f"{W},{H}", "--fps", str(FPS)]
        bdir = os.path.join(project, "build", "segments")
        out = a.out or os.path.join(project, cfg.get("silent", "build/silent.mp4"))
    os.makedirs(os.path.join(bdir, "logs"), exist_ok=True)
    info = list_segments(py, source, FPS)
    total_frames = int(round(info["total"] * FPS))
    mpath = os.path.join(bdir, "manifest.json")
    old = {s["id"]: s for s in load_manifest(mpath).get("segments", [])}
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    segs = []
    for s in info["segments"]:
        o = old.get(s["id"], {})
        fn = os.path.join(bdir, f"{s['id']}.mp4")
        keep = (o.get("done") and o.get("key") == s["key"] and o.get("frames") == s["frames"]
                and os.path.exists(fn) and not a.force and s["id"] not in only)
        segs.append({**s, "file": os.path.relpath(fn, project), "done": bool(keep),
                     "secs": o.get("secs") if keep else None, "overruns": o.get("overruns", []) if keep else []})
    man = {"tool": "manim", "width": W, "height": H, "fps": FPS, "total": info["total"], "timing_hash": info["hash"],
           "draft": a.draft, "segments": segs}
    lock = threading.Lock()
    save_manifest(mpath, man, lock)

    todo = [s for s in segs if not s["done"]]
    if a.bench and todo:
        todo = [min(todo, key=lambda s: s["frames"])]
    todo.sort(key=lambda s: -s["frames"])         # longest first packs the workers best
    done_frames = sum(s["frames"] for s in segs if s["done"])
    n_done = sum(1 for s in segs if s["done"])
    what = f"bench: rendering {todo[0]['id']} only" if a.bench and todo else f"{len(todo)} to render"
    log(f"{len(segs)} segments, {total_frames} frames at {W}x{H}@{FPS}; {n_done} done, {what} with {a.workers} "
        f"worker(s); python {py}")
    for s in segs:
        log(f"  {'[x]' if s['done'] else '[ ]'} {s['id']:<14} {s['from']:7.2f} -> {s['to']:7.2f}  {s['frames']:5d} frames")

    speed = {"frames": 0, "secs": 0.0}         # per-worker frames per second, measured
    for s in segs:
        if s["done"] and s.get("secs"):
            speed["frames"] += s["frames"]
            speed["secs"] += s["secs"]
    procs, stop = {}, threading.Event()

    def est(seg):
        if speed["secs"] > 0:
            return seg["frames"] / (speed["frames"] / speed["secs"])
        return None

    def render(seg):
        if stop.is_set():
            return seg, "skipped"
        e = est(seg)
        if e is not None and (time.time() - T0) + e > budget:
            return seg, "skipped"
        media = os.path.join(bdir, "media", seg["id"])
        shutil.rmtree(media, ignore_errors=True)
        cmd = [py, "-m", "manim", "render", *quality, "--disable_caching", "--media_dir", media, "--progress_bar",
               "none", "-v", "WARNING", "-o", seg["id"], "scenes.py", seg["scene"]]
        t = time.time()
        log_path = os.path.join(bdir, "logs", f"{seg['id']}.log")
        with open(log_path, "w") as logf:
            p = subprocess.Popen(cmd, cwd=source, stdout=logf, stderr=subprocess.STDOUT, text=True)
            procs[seg["id"]] = p
            while p.poll() is None:
                if time.time() - T0 > budget:
                    p.terminate()
                    stop.set()
                time.sleep(0.5)
        procs.pop(seg["id"], None)
        with open(log_path) as source_log:
            txt = source_log.read()
        if p.returncode != 0:
            return seg, "budget" if stop.is_set() else f"failed:\n{txt[-2500:]}"
        hits = [f for f in glob.glob(os.path.join(media, "videos", "**", f"{seg['id']}.mp4"), recursive=True)
                if "partial_movie_files" not in f]
        if not hits:
            return seg, f"failed: no output video\n{txt[-1500:]}"
        dst = os.path.join(project, seg["file"])
        pf = probe_frames(hits[0])
        if pf and pf["frames"] == seg["frames"] and (pf["w"], pf["h"]) == (W, H) and pf["codec"] == "h264" \
                and pf["pix"] == "yuv420p":
            shutil.move(hits[0], dst)
        else:
            got = pf["frames"] if pf else "?"
            log(f"  {seg['id']}: {got} frames rendered, {seg['frames']} wanted; re-timing the segment exactly")
            fix_frames(hits[0], dst, seg["frames"], FPS, W, H)
        shutil.rmtree(media, ignore_errors=True)
        seg["secs"] = round(time.time() - t, 1)
        seg["overruns"] = re.findall(r"FILM-OVERRUN[^\n]*", txt)
        seg["done"] = True
        return seg, "ok"

    failed, budget_hit = [], False
    with cf.ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        futs = [ex.submit(render, s) for s in todo]
        for f in cf.as_completed(futs):
            seg, status = f.result()
            if status == "ok":
                done_frames += seg["frames"]
                speed["frames"] += seg["frames"]
                speed["secs"] += seg["secs"]
                fps_w = speed["frames"] / speed["secs"]
                left = total_frames - done_frames
                eta = left / max(1e-6, fps_w * max(1, min(a.workers, len([s for s in segs if not s['done']]) or 1)))
                log(f"  done {seg['id']:<14} {seg['frames']} frames in {seg['secs']:.0f} s ({seg['frames'] / seg['secs']:.2f} fps); "
                    f"{done_frames}/{total_frames} frames, ETA {eta / 60:.1f} min")
                for o in seg["overruns"]:
                    log(f"    ! {o}")
                save_manifest(mpath, man, lock)
            elif status in ("skipped", "budget"):
                budget_hit = True
            else:
                failed.append((seg["id"], status))
                log(f"  FAILED {seg['id']}: {status}")
    save_manifest(mpath, man, lock)
    if failed:
        sys.exit(1)
    if a.bench:
        fps_w = speed["frames"] / speed["secs"] if speed["secs"] else 0
        whole = total_frames / max(1e-6, fps_w * a.workers) / 60 if fps_w else 0
        log(f"bench: {fps_w:.2f} frames/s per worker at {W}x{H}; whole film ~{whole:.1f} min with {a.workers} "
            f"worker(s) (the benched segment is kept)")
        return 0
    if budget_hit or any(not s["done"] for s in segs):
        log(f"budget reached after {(time.time() - T0) / 60:.1f} min; finished segments are saved. "
            "Run the same command again to continue.")
        sys.exit(3)

    # ------------------------------------------------------------------ join, frame-exact
    lst = os.path.join(bdir, "concat.txt")
    with open(lst, "w") as f:
        for s in segs:
            fp = os.path.join(project, s["file"]).replace("'", "'\\''")  # the concat list's escape for '
            f.write(f"file '{fp}'\n")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp.mp4"
    r = run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-an",
             "-movflags", "+faststart", tmp])
    pf = probe_frames(tmp) if r.returncode == 0 else None
    if not pf or pf["frames"] != total_frames:
        log(f"joined stream has {pf and pf['frames']} frames, want {total_frames}: re-encoding the join")
        fix_frames(tmp if pf else lst, tmp + ".fix.mp4", total_frames, FPS, W, H)
        os.replace(tmp + ".fix.mp4", tmp)
    os.replace(tmp, out)
    pf = probe_frames(out)
    over = [o for s in segs for o in s.get("overruns", [])]
    log(f"wrote {out}: {pf['frames']} frames = {pf['frames'] / FPS:.3f} s (timing total {info['total']:.3f} s), "
        f"{pf['w']}x{pf['h']} {pf['codec']} {pf['pix']}, in {(time.time() - T0) / 60:.1f} min")
    if over:
        log(f"{len(over)} overrun warning(s): a scene ran past a line it belongs to; check the timing there:")
        for o in over:
            log("  " + o)
    if a.stills and a.from_draft:
        at = a.stills
        rr = subprocess.run([sys.executable, os.path.join(HERE, "stills.py"), "--project", project, "--video", out,
                             "--at", at, "--out", cfg.get("stills", "stills")])
        return rr.returncode
    return 0


# ---------------------------------------------------------------------- full-resolution stills
def still_times(spec, timing):
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")  # noqa: E731
    if spec == "chapters":
        # 45% into the chapter, moved off a caption swap (both captions faint for ~0.35 s): to just before it, where the
        # previous line rests, or, at the chapter's first line (before it is the chapter card), just after it
        off_swap = lambda t: next(((ln["voiceAt"] + 0.4 if next(x for x in timing["lines"] if x["chapter"] == ln["chapter"]) is ln
                                else ln["voiceAt"] - 0.35) for ln in timing["lines"] if abs(t - ln["voiceAt"]) < 0.3), t)  # noqa: E731
        return [(f"ch{c['n']}-{slug(c['name'])}", off_swap(c["start"] + 0.45 * (c["end"] - c["start"]))) for c in timing["chapters"]]
    if spec == "lines":
        return [(f"{ln['start']:07.2f}-{ln['id']}", ln["voiceAt"] + 0.7 * ln["voiceDur"]) for ln in timing["lines"]]
    if spec == "busy":
        return [(f"{ln['start']:07.2f}-{ln['id']}", ln["voiceAt"] + 0.85 * ln["voiceDur"])
                for ln in sorted(timing["lines"], key=lambda x: -x["dur"])[:8]]
    return [(f"t{float(x):07.2f}", float(x)) for x in spec.split(",") if x.strip()]


def stills_hires(a, project, source, py, W, H, FPS=30):
    """Each still: the segment's scene run in Manim's last-frame mode (-s) with FILM_STOP_AT=t, so the scene
    builds itself without rendering frames and saves the state at film time t at full resolution."""
    T0 = time.time()
    st = json.load(open(os.path.join(project, ".video-state.json"))) if os.path.exists(
        os.path.join(project, ".video-state.json")) else {}
    out_dir = os.path.join(project, st.get("config", {}).get("stills", "stills"))
    os.makedirs(out_dir, exist_ok=True)
    timing = json.load(open(os.path.join(source, "timing.json")))
    info = list_segments(py, source, FPS)
    shots = still_times(a.stills, timing)
    tmp = os.path.join(project, "build", "stills-tmp")
    os.makedirs(tmp, exist_ok=True)

    def one(shot):
        name, t = shot
        seg = next((s for s in info["segments"] if s["from"] <= t < s["to"]), info["segments"][-1])
        media = os.path.join(tmp, name)
        shutil.rmtree(media, ignore_errors=True)
        env = dict(os.environ, FILM_STOP_AT=f"{t:.3f}")
        cmd = [py, "-m", "manim", "render", "-s", "-r", f"{W},{H}", "--fps", str(FPS), "--disable_caching", "--media_dir", media,
               "--progress_bar", "none", "-v", "WARNING", "-o", name, "scenes.py", seg["scene"]]
        r = run(cmd, cwd=source, env=env)
        pngs = glob.glob(os.path.join(media, "images", "**", "*.png"), recursive=True)
        if r.returncode or not pngs:
            return name, t, f"failed: {r.stderr[-1500:] or r.stdout[-1500:]}"
        dst = os.path.join(out_dir, f"{name}.png")
        shutil.move(pngs[0], dst)
        shutil.rmtree(media, ignore_errors=True)
        return name, t, "ok"

    bad = []
    with cf.ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        for name, t, status in ex.map(one, shots):
            log(f"still {name} at {t:.2f} s: {status}")
            if status != "ok":
                bad.append(name)
    files = sorted(f for f in glob.glob(os.path.join(out_dir, "*.png")) + glob.glob(os.path.join(out_dir, "*.jpg"))
                   if not f.endswith("sheet.png"))
    if files:
        cols = 4
        rows = (len(files) + cols - 1) // cols
        seq = os.path.join(tmp, "sheet")
        shutil.rmtree(seq, ignore_errors=True)
        os.makedirs(seq)
        for i, f in enumerate(files):
            # one size and pixel format for the whole sequence (a change mid-stream resets the tile filter)
            run(["ffmpeg", "-v", "error", "-y", "-i", f, "-vf", "scale=480:270", "-pix_fmt", "rgb24",
                 os.path.join(seq, f"{i:04d}.png")])
        run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(seq, "%04d.png"),
             "-vf", f"tile={cols}x{rows}:padding=4:color=0x111111", "-frames:v", "1",
             os.path.join(out_dir, "sheet.png")])
    log(f"{len(shots) - len(bad)} stills in {out_dir} ({(time.time() - T0):.0f} s); contact sheet: {out_dir}/sheet.png")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main() or 0)
