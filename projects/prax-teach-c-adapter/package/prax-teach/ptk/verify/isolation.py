"""Render isolation (AC-0.2, D18.3, E1, E16): canaries that must fail inside the render sandbox.

Three canaries run under exactly the profile and parameters the render uses:
    dns            getaddrinfo("example.com")
    https          curl https://example.com
    child-connect  a forked child connects to 1.1.1.1:443 by IP (no DNS needed)
Each also runs once outside the sandbox as a control, so a failure inside proves the
sandbox, not an offline machine. The render log must not contain any net::ERR_ line.
"""
import re
import sys

from .. import host

DNS = "import socket\nsocket.getaddrinfo('example.com', 443)\nprint('resolved')\n"
CHILD = ("import os, socket, sys\n"
         "pid = os.fork()\n"
         "if pid == 0:\n"
         "    try:\n"
         "        socket.create_connection(('1.1.1.1', 443), 5).close()\n"
         "        os._exit(0)\n"
         "    except OSError as e:\n"
         "        sys.stderr.write('child-connect failed: %s\\n' % e)\n"
         "        os._exit(7)\n"
         "_, status = os.waitpid(pid, 0)\n"
         "sys.exit(os.waitstatus_to_exitcode(status))\n")


def _canaries():
    py = sys.executable
    curl = host.which("curl", required=False) or "/usr/bin/curl"
    return {"dns": [py, "-c", DNS], "https": [curl, "-sS", "-m", "8", "-o", "/dev/null", "https://example.com/"],
            "child-connect": [py, "-c", CHILD]}


def run_canaries(proj, tmp):
    out = {}
    for name, cmd in _canaries().items():
        inside = host.run(host.sandboxed(cmd, "render", tmp=tmp, proj=proj, state=host.state_dir()), timeout=30)
        control = host.run(cmd, timeout=30)
        out[name] = {"inside_exit": inside.code, "inside_error": (inside.stderr or inside.stdout).strip()[-300:],
                     "blocked": inside.code != 0, "control_exit": control.code,
                     "control_reached_network": control.code == 0}
    return out


def denied_in_log(log):
    return sorted(set(re.findall(r"net::ERR_[A-Z_]+[^\n]*", log)))


def gate(canaries, render_ok, log, sandbox_path="sandbox-exec"):
    denied = denied_in_log(log)
    all_blocked = all(c["blocked"] for c in canaries.values())
    ok = all_blocked and render_ok and not denied
    reason = ""
    if not all_blocked:
        reason = "a canary reached the network inside the render sandbox"
    elif not render_ok:
        reason = "render failed under the sandbox profile"
    elif denied:
        reason = "the render tried to reach the network (OutboundRequest)"
    return {"id": "video.render-isolation", "medium": "video", "status": "passed" if ok else "failed",
            "measured": {"isolation": f"{sandbox_path} -f ptk/capture/sandbox.sb -D MODE=render", "canaries": canaries,
                         "render_succeeded": render_ok, "denied_requests_in_render_log": denied},
            "reason": reason}
