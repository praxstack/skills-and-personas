"""AC-0.2: DNS, HTTPS and child-connect canaries fail inside the render sandbox; the render succeeds."""
import re
import shutil

from ptk import host, node
from ptk.verify import isolation

FIXTURE = host.PKG / "tests" / "fixtures" / "render-canary"


def test_canaries_fail_render_succeeds():
    tmp = host.make_tmp("isolation-test-")
    proj = tmp / "proj"
    shutil.copytree(FIXTURE, proj)
    canaries = isolation.run_canaries(proj, tmp)
    for name, c in canaries.items():
        assert c["blocked"], f"canary {name} reached the network inside the sandbox: {c}"
        assert c["inside_error"], f"canary {name} failed silently"
        assert c["control_reached_network"], f"control for {name} had no network, so the canary proves nothing"
    res = node.hyperframes(["render", ".", "-o", str(proj / "out.mp4"), "--workers", "1", "--no-browser-gpu"],
                           cwd=proj, timeout=900, sandbox_tmp=tmp, check=False)
    log = res.stdout + res.stderr
    assert res.code == 0 and (proj / "out.mp4").exists(), f"render failed under the sandbox: {log[-1500:]}"
    # the composition's own fetch to https://example.com must fail visibly in the render log
    denied = isolation.denied_in_log(log)
    assert denied, "in-page network canary left no denied request in the render log"
    frame = tmp / "frame.png"
    ffmpeg = host.which("ffmpeg")
    host.run([ffmpeg, "-v", "error", "-y", "-ss", "1", "-i", proj / "out.mp4", "-frames:v", "1", frame], check=True)
    seen = host.run([host.which("tesseract"), frame, "-", "--psm", "7"], timeout=60).stdout.strip().lower()
    assert "offline" in seen and "network" not in seen, f"frame shows {seen!r}"
    shutil.rmtree(tmp, ignore_errors=True)
    return {"isolation": "sandbox-exec MODE=render", "canaries": {k: v["inside_error"][-80:] for k, v in canaries.items()},
            "denied_in_render_log": denied, "frame_text": seen}
