#!/usr/bin/env python3
"""package.py: assemble the deliverable folder from a project that passed QA.

Copies into the deliver folder (default <project>/deliver, or --to <dir>):
  <slug>.mp4           the exact file that passed QA (checked by hash)
  captions.srt         from timing.json
  timeline.json        every line's start, duration, chapter, caption and spoken text
  NOTES.md             your project NOTES.md (tool + versions, voice, style, re-render commands, limits)
  contact-sheet.png    from qa/
  bed.m4a              music + effects without voice
  edge_voice_swap.py   re-voice on a laptop with any Microsoft neural voice
  voice/narration.wav  the narration that source/'s preview and editor play
  source/              the re-renderable project (brief, script, timing, scene code; no node_modules or caches)

Usage: python3 package.py --project . [--to /path/to/share/folder]

The deliver folder is emptied of the files above and refilled, so package.py only writes to a folder that is new,
empty, the project's own deliver/, or one it delivered to before (it leaves a .video-deliver marker there). Every
check runs before the first write. A symlink or hard link left where a file goes is replaced, never written through.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {"node_modules", "media", "build", "dist", "out", ".cache", "__pycache__", ".venv", "venv", "stills",
        "segments", ".parcel-cache", ".vite", "output", "renders", ".git"}
MARKER = ".video-deliver"  # written into every folder package.py delivers to


def sha(path, n=16):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


def clear(path):
    """Make way for a new file at path. A symlink or hard link left there would send the write to a file outside
    the deliver folder, so the old entry itself is removed (never what it points to)."""
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    return path


def symlinks_under(src):
    """Symlinks anywhere in the source tree (outside the skipped caches): copying through them would put files
    from outside the project into a folder meant to be shared."""
    out = []
    for dp, dn, fn in os.walk(src):
        dn[:] = [d for d in dn if d not in SKIP]
        for n in dn + fn:
            if os.path.islink(os.path.join(dp, n)):
                out.append(os.path.relpath(os.path.join(dp, n), src))
    return out


def within(p, folder):
    """Whether p is folder or inside it (both real paths). On Windows two drives share no folder, and commonpath
    raises for them (a project on C: delivered to D:), so paths on different drives are not inside each other."""
    try:
        return os.path.commonpath([folder, p]) == folder
    except ValueError:
        return False


def unsafe_dest(root, dest, inside, src=None):
    """Why the deliver folder must not be written to, or None. Checked before anything is copied: the folder's
    source/ is deleted and refilled and the other deliverables are overwritten, so this refuses
      - a symlink as the folder or its source/ (deletes and writes would land outside it),
      - a relative deliver path (the default) that resolves outside the project,
      - the project itself, any folder that holds it, or a folder inside the scene source,
      - any folder but the project's own deliver/ that already holds files and was not made by package.py (no
        marker), including a custom relative deliver path such as `vstate.py set deliver=archive`."""
    sd = os.path.join(dest, "source")
    for p in (dest, sd):
        if os.path.islink(p):
            return f"{p} is a symlink; refusing to delete or write through it"
    real_root, real_dest = os.path.realpath(root), os.path.realpath(dest)
    if inside and not within(real_dest, real_root):
        return f"the deliver folder resolves outside the project ({real_dest}); refusing to write there"
    for p in (root, src):
        if p and within(os.path.realpath(p), real_dest):
            return f"the deliver folder {real_dest} is or holds {os.path.realpath(p)}; deliver to a folder of its own"
    if src and within(real_dest, os.path.realpath(src)):
        return f"the deliver folder {real_dest} is inside the scene source; deliver to a folder of its own"
    own = real_dest == os.path.join(real_root, "deliver")
    if (not own and os.path.isdir(dest) and os.listdir(dest)
            and not os.path.isfile(os.path.join(dest, MARKER))):
        return (f"{dest} already holds files that package.py did not deliver (its source/ would be replaced); "
                f"pass a new or empty folder, e.g. --to {os.path.join(dest, os.path.basename(root))}")
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--to", default=None, help="deliver folder (recorded in the state as config.deliver)")
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    sp = os.path.join(root, ".video-state.json")
    st = json.load(open(sp))
    slug, cfg = st["slug"], st["config"]
    dest = os.path.abspath(a.to) if a.to else cfg.get("deliver", "deliver")
    inside = not os.path.isabs(dest)
    dest = dest if os.path.isabs(dest) else os.path.join(root, dest)
    src = os.path.join(root, cfg.get("source", "source"))
    # every check before the first write
    why = unsafe_dest(root, dest, inside, src)
    if why:
        sys.exit(why)
    if os.path.islink(src):
        sys.exit(f"the scene source {src} is a symlink, which would copy files from outside the project into the "
                 "deliverable; use a real folder")
    # source/ is shared with the film: a configured source outside the project (an absolute path, or one with "..")
    # would copy that outside folder into the deliverable (and its tree is walked next)
    if not within(os.path.realpath(src), os.path.realpath(root)):
        sys.exit(f"the scene source {src} is outside the project, so packaging would copy an outside folder into the "
                 "deliverable; keep the scene in the project (vstate.py set source=source)")
    links = symlinks_under(src)
    if links:
        sys.exit("the scene source holds symlinks, which would copy files from outside the project into the deliverable; "
                 "replace them with real files: " + ", ".join(links[:5]))
    final = os.path.join(root, cfg.get("final", f"out/{slug}.mp4"))
    rep = json.load(open(os.path.join(root, "qa", "report.json")))
    if rep.get("video_sha") != sha(final) or not rep.get("pass"):
        sys.exit("the final video has not passed QA in its current form; run qa.py first")
    # the captions are made from timing.json and timeline.json ships beside the film: QA checked the film against
    # both, so one changed since (a re-voice, a hand edit) would ship captions and edit points for another cut
    for f in ("timing.json", "timeline.json"):
        fp, key = os.path.join(root, f), f.split(".")[0] + "_sha"
        if key in rep:
            changed = rep[key] != (sha(fp) if os.path.isfile(fp) else None)
        else:  # a report from before qa.py recorded them
            changed = os.path.isfile(fp) and os.path.getmtime(fp) > os.path.getmtime(os.path.join(root, "qa", "report.json"))
        if changed:
            sys.exit(f"{f} changed after QA, so the captions and timeline would not match the film; run qa.py again "
                     "(after voicing, rendering and mixing again if the narration changed), then package")
    if not os.path.isdir(src):  # the delivered source/ is replaced by a copy of it
        sys.exit(f"the scene source {src} is missing or not a folder; restore it, then package")
    # the project files copied below must be the project's own: a symlink (or a linked folder) that leads outside it
    # would copy that outside file into a folder meant to be shared
    rr = os.path.realpath(root)
    ins = ("brief.md", "script.json", "script.template.json", "timing.json", "timeline.json", "NOTES.md",
           "qa/contact-sheet.png", "audio/bed.m4a", "voice/narration.wav")
    away = [f for f in ins if os.path.lexists(os.path.join(root, f))
            and not within(os.path.realpath(os.path.join(root, f)), rr)]
    if away:
        sys.exit("these project files lead outside the project (symlinks), so packaging would copy outside files into "
                 "the deliverable; replace them with real files: " + ", ".join(away))
    # each is read or copied after the first write, so a folder (or anything but a file) in its place would stop
    # packaging halfway, with the deliver folder already partly replaced
    odd = [f for f in ins if os.path.lexists(os.path.join(root, f)) and not os.path.isfile(os.path.join(root, f))]
    if odd:
        sys.exit("these project files are not files (a folder, or a broken link), so packaging would stop halfway: "
                 + ", ".join(odd) + "; put the real files there")
    nar = os.path.join(root, "voice", "narration.wav")  # source/ pages play ../voice/narration.wav (preview, editor)
    if not os.path.isfile(nar):
        sys.exit("voice/narration.wav is missing; the packaged preview and editor play it (run voice.py again)")
    # the final was mixed from these; one changed since means the package would ship sound that no longer matches it
    # (by content when mix.py recorded it, so a file copied in with an old time counts too)
    sys.path.insert(0, HERE)
    import vstate
    newer = vstate.mix_changed(root, final)
    if newer:
        sys.exit(f"{', '.join(newer)} changed after the final was mixed; run mix.py and qa.py again, then package")
    # source/ ships as the way to re-make this film, so it must be the scene source the film was rendered from. The
    # render gate records the source's content hash next to the render's; without that record, every scene file must
    # be older than the final.
    pr = vstate.Project(root)
    pr.load()
    silent, rec = pr.p(pr.cfg("silent")), pr.s.get("artifacts", {}).get("silent") or {}
    # the final's picture must be that render: mix.py --video can mix another file, which the source check below
    # would never see, so a package of it could not be re-made from source/. A record from a mix.py that noted only
    # the audio cannot say which video it was, so that final is mixed again
    used = vstate.mix_inputs(root, final)
    vids = vstate.mix_videos(used) if used is not None else []
    if used is not None and not vids:
        sys.exit("audio/mix.json is from an older mix.py that did not record which video the final's picture came "
                 "from; run mix.py and qa.py again, then package")
    off = [v for v in vids if os.path.realpath(os.path.join(root, v)) != os.path.realpath(silent)]
    if off:
        sys.exit(f"the final was mixed from {off[0]}, not the render {pr.cfg('silent')} that source/ makes; mix from "
                 "that render (mix.py without --video) and run qa.py again, or set silent=<that file> if it is a "
                 "render of this source, then package")
    if os.path.isfile(silent) and os.path.getmtime(silent) > os.path.getmtime(final):
        sys.exit(f"the render {pr.cfg('silent')} is newer than the final; run mix.py and qa.py again, then package")
    if os.path.isfile(silent) and rec.get("sha") == vstate.sha(silent):
        if rec.get("source_hash") != vstate.source_hash(pr):
            sys.exit("the scene source changed after the film was rendered, so source/ would not make this film; render, "
                     "mix and qa again (or undo the edit), then package")
    elif vstate.source_newest(pr) > os.path.getmtime(final):
        sys.exit("a scene source file changed after the final was made, so source/ might not make this film; render, "
                 "mix and qa again (or undo the edit), then package")
    # the slug names <slug>.mp4 in the deliver folder: a "/" or ".." in it would write somewhere else
    if not isinstance(slug, str) or not slug or not set(slug) <= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-") or slug in (".", ".."):
        sys.exit(f"the slug {slug!r} must be a plain file name (letters, digits, '.', '_', '-'); fix it in .video-state.json")
    # where a file goes there must be no folder, and where the voice/ folder goes no file, or a write fails halfway
    vd = os.path.join(dest, "voice")
    outs = [MARKER, f"{slug}.mp4", "captions.srt", "timeline.json", "NOTES.md", "contact-sheet.png", "bed.m4a",
            "edge_voice_swap.py"] + ([] if os.path.islink(vd) else [os.path.join("voice", "narration.wav")])  # a linked voice/ is replaced
    blocked = [f for f in outs if os.path.isdir(os.path.join(dest, f)) and not os.path.islink(os.path.join(dest, f))]
    for d in ("voice", "source"):   # a linked voice/ is replaced; a linked source/ was refused above
        q = os.path.join(dest, d)
        if os.path.lexists(q) and not os.path.islink(q) and not os.path.isdir(q):
            blocked.append(f"{d} (a file where the {d}/ folder goes)")
    if blocked:
        sys.exit(f"{dest} has folders or files in the way of the delivery: {', '.join(blocked)}; move them out first")
    # the copied source/ then gets brief, script and timing and a pipeline/ folder laid over it: a folder in the scene
    # where one of those files goes, or a file where pipeline/ goes, would stop packaging halfway
    pipe = [f for f in os.listdir(HERE) if f.endswith((".py", ".mjs", ".js", ".sh"))] + ["tool.json"]
    over = [f for f in ["brief.md", "script.json", "timing.json", "script.template.json"] + [os.path.join("pipeline", f) for f in pipe]
            if os.path.isdir(os.path.join(src, f))]
    if os.path.lexists(os.path.join(src, "pipeline")) and not os.path.isdir(os.path.join(src, "pipeline")):
        over.append("pipeline (a file where the pipeline/ folder goes)")
    if over:
        sys.exit(f"the scene source has {', '.join(over)} in the way of what package.py adds to source/; rename or move them first")
    keep = vstate.scene_videos(src, SKIP)  # read now: nothing after the first write should be able to stop packaging
    notes = os.path.join(root, "NOTES.md")
    if not os.path.exists(notes):
        sys.exit("write NOTES.md first (start from: python3 vstate.py notes-md > NOTES.md, then fill it in)")
    if "fill in" in open(notes, encoding="utf-8").read():
        sys.exit("NOTES.md still has '(fill in)' placeholders")
    missing = [f for f in ("timing.json", "timeline.json", "qa/contact-sheet.png", "audio/bed.m4a", "brief.md",
                           "script.json") if not os.path.exists(os.path.join(root, f))]
    if missing:
        sys.exit("missing before packaging: " + ", ".join(missing))
    if a.to:
        cfg["deliver"] = dest
        json.dump(st, open(sp, "w"), indent=1, ensure_ascii=False)
    os.makedirs(dest, exist_ok=True)
    with open(clear(os.path.join(dest, MARKER)), "w", encoding="utf-8") as f:
        f.write(f"delivered by package.py for {slug}; package.py may replace the files it wrote here\n")

    shutil.copy2(final, clear(os.path.join(dest, f"{slug}.mp4")))
    sys.path.insert(0, HERE)
    import captions
    tm = json.load(open(os.path.join(root, "timing.json"), encoding="utf-8"))
    captions.write_srt(tm, clear(os.path.join(dest, "captions.srt")))
    for rel, name in [("timeline.json", "timeline.json"), ("NOTES.md", "NOTES.md"), ("qa/contact-sheet.png", "contact-sheet.png"),
                      ("audio/bed.m4a", "bed.m4a")]:
        shutil.copy2(os.path.join(root, rel), clear(os.path.join(dest, name)))
    shutil.copy2(os.path.join(HERE, "edge_voice_swap.py"), clear(os.path.join(dest, "edge_voice_swap.py")))

    sd = os.path.join(dest, "source")
    if os.path.isdir(sd):
        shutil.rmtree(sd)  # unsafe_dest() refused a symlink here and any folder package.py did not make
    shutil.copytree(src, sd, symlinks=True, ignore=lambda d, names: [
        n for n in names if n in SKIP or n.lower().endswith(vstate.VIDEO_EXT) and os.path.normpath(os.path.join(d, n)) not in keep])
    for f in ("brief.md", "script.json", "timing.json"):
        shutil.copy2(os.path.join(root, f), os.path.join(sd, f))
    if os.path.exists(os.path.join(root, "script.template.json")):  # a data clip's narration template (motion_fill.py)
        shutil.copy2(os.path.join(root, "script.template.json"), os.path.join(sd, "script.template.json"))
    vs = os.path.join(sd, "pipeline")
    os.makedirs(vs, exist_ok=True)
    for f in sorted(os.listdir(HERE)):  # the whole pipeline, including the skill's own render scripts
        if f.endswith((".py", ".mjs", ".js", ".sh")):
            shutil.copy2(os.path.join(HERE, f), os.path.join(vs, f))
    kit = os.path.join(os.path.dirname(HERE), "tool.json")  # the kit's settings, which captions.py reads (rich_captions)
    if os.path.isfile(kit):
        shutil.copy2(kit, os.path.join(vs, "tool.json"))
    if os.path.islink(vd):  # a link here would send the copy outside the deliver folder: remove the link itself
        os.unlink(vd)
    os.makedirs(vd, exist_ok=True)
    shutil.copy2(nar, clear(os.path.join(vd, "narration.wav")))
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(sd) for f in fs)
    print(f"delivered to {dest}  (source {size / 1e6:.1f} MB)")
    for f in sorted(os.listdir(dest)):
        print("  ", f)


if __name__ == "__main__":
    main()
