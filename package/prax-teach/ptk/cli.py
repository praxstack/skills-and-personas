"""ptk command line (spec §5.4). Exit codes come from ptk/errors.py (D19.5).

WP0 implements: validate, capture, build [--only], claims check, report, host probe,
host setup, selftest, agent-tests. Later packages add route, new and package.
"""
import argparse
import json
import sys
from pathlib import Path

from . import errors


def _emit(obj, as_json=True):
    print(json.dumps(obj, indent=2) if as_json else obj)


def cmd_validate(a):
    """Schema plus reference checks. Every problem is printed as {pointer, message}; exit 3 (AC-2.1)."""
    from . import model
    try:
        lesson = model.load(a.lesson)
        model.validate(lesson)
    except errors.ModelError as e:
        listed = e.detail.get("errors") or [{"pointer": e.detail.get("pointer", ""), "message": e.message}]
        _emit({"valid": False, "error": e.kind, "lesson": str(a.lesson), "errors": listed})
        return e.exit_code
    _emit({"valid": True, "lesson": lesson.id, "path": str(lesson.path)})
    return errors.EXIT_OK


def cmd_new(a):
    """Scaffold <dir>/<slug>/lesson.json and programs/main.c with TODO: placeholders."""
    from . import model
    _emit(model.scaffold(a.slug, a.dir))
    return errors.EXIT_OK


def cmd_capture(a):
    from . import model
    from .capture import c_runner
    lesson = model.load(a.lesson)
    model.validate(lesson)
    out = c_runner.capture_lesson(lesson)
    _emit(out)
    return errors.EXIT_OK


def cmd_build(a):
    from . import build
    only = [m.strip() for m in a.only.split(",")] if a.only else None
    report = build.build(a.lesson, only=only, calibrate=a.calibrate)
    _emit(build.summary(report))
    return build.exit_code(report)


def cmd_claims(a):
    from . import build
    report = build.claims_check(a.lesson)
    _emit(build.summary(report))
    return build.exit_code(report)


def cmd_report(a):
    from . import build
    report = build.load_report(a.lesson)
    if a.json:
        _emit(report)
    else:
        print(build.render_text(report))
    return build.exit_code(report)


def cmd_host(a):
    from . import host
    if a.host_cmd == "probe":
        _emit(host.probe(artifact=a.artifact))
        return errors.EXIT_OK
    res = host.setup(yes=a.yes, log=lambda m: print(m, file=sys.stderr))
    if not res["fetched"]:
        print("ptk host setup would fetch (run again with --yes to fetch):", file=sys.stderr)
    _emit(res)
    return errors.EXIT_OK


def cmd_route(a):
    from . import route
    res = route.route(a.request, workspace_dir=a.workspace)
    if a.json:
        _emit(res)
    else:
        print(f"intent={res['intent']} mode={res['mode']} media={','.join(res['media']) or '-'} "
              f"build_needed={res['build_needed']} confidence={res['confidence']}"
              f"{' (' + '; '.join(res['reasons']) + ')' if res['reasons'] else ''}"
              f"\nfirst turn: {res['first_turn']['instruction']}")
    return errors.EXIT_OK


def cmd_package(a):
    """Build the install tree (AC-8.1) and run the host discovery check (AC-8.2). Exit 1 on any problem."""
    from . import package
    res = package.build(out=a.out, dry_run=a.dry_run)
    _emit(res)
    if res["problems"] or (not a.dry_run and not res["packaged"]):
        return errors.EXIT_GATE
    return errors.EXIT_OK


def cmd_selftest(a):
    from . import selftest
    return selftest.run(suite="auto", pattern=a.k)


def cmd_agent_tests(a):
    from . import selftest
    return selftest.run(suite="agent", pattern=a.k)


def parser():
    p = argparse.ArgumentParser(prog="ptk", description="Prax Teach lesson compiler")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("validate", cmd_validate), ("capture", cmd_capture)):
        s = sub.add_parser(name)
        s.add_argument("lesson")
        s.set_defaults(fn=fn)
    s = sub.add_parser("new", help="scaffold a lesson: lesson.json and programs/ with TODO: placeholders")
    s.add_argument("slug")
    s.add_argument("--dir", default="lessons", help="parent directory (default: lessons)")
    s.set_defaults(fn=cmd_new)
    s = sub.add_parser("build")
    s.add_argument("lesson")
    s.add_argument("--only", help="comma list of media: still,video,ive,explorer,qa,cards")
    s.add_argument("--calibrate", action="store_true",
                   help="write the full claims mutation suite (up to 12 mutations plus controls) instead of one "
                        "canary; run on a rubric or reviewer-model change and at acceptance (D21.1)")
    s.set_defaults(fn=cmd_build)
    s = sub.add_parser("claims")
    cs = s.add_subparsers(dest="claims_cmd", required=True)
    c = cs.add_parser("check")
    c.add_argument("lesson")
    c.set_defaults(fn=cmd_claims)
    s = sub.add_parser("report")
    s.add_argument("lesson")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_report)
    s = sub.add_parser("host")
    hs = s.add_subparsers(dest="host_cmd", required=True)
    hp = hs.add_parser("probe", help="which tools and ranked alternatives run here now (AC-8.5)")
    hp.add_argument("--artifact", help="only this artifact type: still, explorer, qa, cards, video, ive, tts")
    hp.set_defaults(fn=cmd_host)
    h = hs.add_parser("setup")
    h.add_argument("--yes", action="store_true")
    h.set_defaults(fn=cmd_host)
    s = sub.add_parser("route", help="intent, mode, media and first turn for a request (AC-1.1)")
    s.add_argument("request")
    s.add_argument("--workspace", help="learner workspace dir (default: current dir)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_route)
    s = sub.add_parser("package", help="build the install tree and check it, plus host discovery (AC-8.1, AC-8.2)")
    s.add_argument("--dry-run", action="store_true", help="list and check the files without writing anything")
    s.add_argument("--out", help="install tree directory (default: $PTK_STATE/package/prax-teach)")
    s.set_defaults(fn=cmd_package)
    for name, fn in (("selftest", cmd_selftest), ("agent-tests", cmd_agent_tests)):
        s = sub.add_parser(name)
        s.add_argument("-k", help="only tests whose name contains this")
        s.set_defaults(fn=fn)
    return p


def main(argv=None):
    a = parser().parse_args(argv)
    try:
        return a.fn(a)
    except errors.PtkError as e:
        print(json.dumps(e.as_dict(), indent=2, default=str), file=sys.stderr)
        return e.exit_code


if __name__ == "__main__":
    sys.exit(main())
