"""AC-0.1 (setup inventory, no writes outside $PTK_STATE) and the §5.5 env contract."""
import json
import re

from _util import ptk_cmd, under
from ptk import host

REQUIRED = {"playwright-chromium", "node-tools", "hyperframes-chrome", "kokoro-model", "kokoro-voices",
            "whisper-base-en", "core-venv", "kokoro-venv"}


def test_setup_inventory_and_paths():
    """`ptk host setup --yes`, run inside a sandbox that denies every write outside $PTK_STATE
    must finish and leave an inventory with a sha256 per item. The bundled fonts are checked against
    the committed SHA256SUMS, which setup never rewrites."""
    st = host.state_dir()
    jail = host.PKG / "tests" / "fixtures" / "write-jail.sb"
    sums_before = host.sha256_file(host.FONTS_DIR / "SHA256SUMS")
    res = host.run([host.sandbox_exec(), "-f", jail, "-D", f"STATE={st}",
                    *ptk_cmd(), "host", "setup", "--yes"],
                   env=host.child_env({"PTK_STATE": str(st), "TMPDIR": str(st / "tmp") + "/"}), timeout=3600)
    assert res.code == 0, f"setup failed inside the write jail: {res.stderr[-1500:]}"
    inv = json.loads((st / "setup-inventory.json").read_text())
    ids = {i["id"] for i in inv["items"]}
    assert REQUIRED <= ids, f"missing from inventory: {REQUIRED - ids}"
    for item in inv["items"]:
        assert re.fullmatch(r"[0-9a-f]{64}", item["sha256"]), item["id"]
        assert item["url"].startswith("https://"), item["id"]
        assert item["size"] and item["size"] > 0, item["id"]
        assert under(item["path"], st) or under(item["path"], host.FONTS_DIR), f"{item['id']} outside $PTK_STATE"
    node_tools = next(i for i in inv["items"] if i["id"] == "node-tools")
    versions = {p["name"]: p["version"] for p in node_tools["top"]}
    assert versions.get("hyperframes") == "0.8.169", versions
    assert (st / "tools" / "node" / "node_modules" / ".bin" / "hyperframes").exists()
    hf = host.registry()["hyperframes_chrome"]
    assert (st / "browsers" / "hyperframes" / hf["dir"] / hf["binary"]).exists()
    assert list((st / "browsers").glob("chromium_headless_shell-*")), "Playwright Chromium missing"
    assert host.sha256_file(host.FONTS_DIR / "SHA256SUMS") == sums_before, "setup rewrote the font pins"
    sums = dict(reversed(ln.split(None, 1)) for ln in (host.FONTS_DIR / "SHA256SUMS").read_text().splitlines() if ln.strip())
    for f in host.FONTS_DIR.glob("*.woff2"):
        assert sums.get(f.name) == host.sha256_file(f), f.name
    return {"items": len(inv["items"]), "total_bytes": inv["total_bytes"]}


def test_env_contract():
    env = host.child_env(lesson_sha256="ab" * 32, node_home=True)
    for k, v in host.CONTRACT.items():
        assert env[k] == v, k
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(host.state_dir() / "browsers")
    assert env["SOURCE_DATE_EPOCH"] == host.source_date_epoch("ab" * 32)
    assert under(env["HOME"], host.state_dir()), "HyperFrames HOME must live inside $PTK_STATE"
    for secret in host.SECRET_VARS:
        assert secret not in env


def test_env_contract_reaches_children():
    """AC-8.7: the contract is applied by host.run itself, so even a caller's allowlist env (the compiler's,
    the untrusted program's) carries it, and node.env() carries it to every Node child."""
    from ptk import node
    from ptk.capture import c_runner
    envs = {"default": None, "compile": c_runner.compile_env(host.state_path("tmp")), "program": host.program_env(),
            "node": node.env(lesson_sha256="cd" * 32)}
    seen = {}
    for label, env in envs.items():
        res = host.run(["/usr/bin/env"], env=env, timeout=30)
        assert res.code == 0, res.stderr
        got = dict(ln.split("=", 1) for ln in res.stdout.splitlines() if "=" in ln)
        for k, v in host.CONTRACT.items():
            assert got.get(k) == v, f"{label}: {k}={got.get(k)!r}"
        assert got.get("PLAYWRIGHT_BROWSERS_PATH"), label
        assert got.get("SOURCE_DATE_EPOCH", "").isdigit(), label
        for secret in host.SECRET_VARS:
            assert secret not in got, f"{label}: {secret} leaked"
        seen[label] = len(got)
    # an allowlist stays an allowlist: only the contract keys were added
    res = host.run(["/usr/bin/env"], env=host.program_env(), timeout=30)
    keys = {ln.split("=", 1)[0] for ln in res.stdout.splitlines() if "=" in ln}
    allowed = set(host.program_env()) | set(host.CONTRACT) | {"PLAYWRIGHT_BROWSERS_PATH", "SOURCE_DATE_EPOCH",
                                                               "DEVELOPER_DIR"}
    assert keys <= allowed, sorted(keys - allowed)
    assert node.env(lesson_sha256="cd" * 32)["SOURCE_DATE_EPOCH"] == host.source_date_epoch("cd" * 32)
    return seen


def test_selftest_reports_unique():
    """WP8 bug: two `ptk selftest` runs at once used to write the same .state/selftest-auto.json.
    Each run now writes its own report file, created exclusively."""
    import threading
    results = []

    def one():
        results.append(host.run([*ptk_cmd(), "selftest", "-k", "test_host.py::test_env_contract"],
                                env=host.child_env(), timeout=300))

    threads = [threading.Thread(target=one) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    paths = []
    for res in results:
        assert res.code == 0, res.stderr[-800:]
        out = json.loads(res.stdout)
        paths.append(out["report"])
        rep = json.loads(open(out["report"]).read())
        assert {r["test"] for r in rep["results"]} == {"tests/test_host.py::test_env_contract",
                                                       "tests/test_host.py::test_env_contract_reaches_children"}
    assert len(set(paths)) == 3, paths
    assert all(under(p, host.state_path("selftest")) for p in paths)
    return {"reports": len(set(paths))}


def test_setup_core_venv_has_genanki_and_fsrs():
    """WP8: `ptk host setup` installs genanki (cards) and fsrs (learner state) into the core venv, with
    hashes, in the same pip run as jsonschema. Checks the plan, the pinned files, and the installed venv."""
    item = next(d for d in host.registry()["downloads"] if d["id"] == "core-venv")
    reqs = item["requirements"]
    text = "".join((host.PKG / r).read_text() for r in reqs)
    for pin in ("genanki==0.13.1", "fsrs==6.3.1", "jsonschema=="):
        assert pin in text, pin
    for ln in text.splitlines():
        if ln.strip() and not ln.startswith("#"):
            assert "--hash=sha256:" in ln, ln
    py = host.state_path("venvs", "core", "bin", "python")
    if not py.exists():
        from selftest_support import NotRun
        raise NotRun("core venv missing: run `ptk host setup --yes`")
    res = host.run([py, "-I", "-c", "import genanki, fsrs, jsonschema, importlib.metadata as m; "
                    "print(m.version('genanki'), m.version('fsrs'))"], timeout=60)
    assert res.code == 0, f"core venv lacks genanki or fsrs (run `ptk host setup --yes`): {res.stderr[-400:]}"
    assert res.stdout.split() == ["0.13.1", "6.3.1"], res.stdout
    return {"versions": res.stdout.split()}


def test_developer_dir_pinned_and_no_xcrun_shim_runs():
    """Round-17 incident (17:44): a ptk run made macOS offer to install the Command Line Tools. An /usr/bin
    developer shim (clang, git, as, ld, ...) asks xcrun for the active developer dir, and when it cannot find one
    (a scrubbed env, a sandbox, Xcode mid-update) macOS pops that dialog. So: DEVELOPER_DIR is pinned in every
    child env, a caller's DEVELOPER_DIR never wins, the compilers run by their absolute path inside that dir,
    and host.run swaps any /usr/bin shim for the real tool (or refuses when there is none)."""
    import os
    from ptk.capture import c_runner
    dev = host.developer_dir()
    assert dev and os.path.isdir(dev), dev
    saved = os.environ.get("DEVELOPER_DIR")
    try:
        os.environ["DEVELOPER_DIR"] = "/nonexistent-hostile-devdir"
        envs = {"default": None, "child": host.child_env(), "program": host.program_env(),
                "compile": c_runner.compile_env(host.state_path("tmp"))}
        for label, env in envs.items():
            res = host.run(["/usr/bin/env"], env=env, timeout=30)
            got = dict(ln.split("=", 1) for ln in res.stdout.splitlines() if "=" in ln)
            assert got.get("DEVELOPER_DIR") == dev, (label, got.get("DEVELOPER_DIR"))
    finally:
        if saved is None:
            os.environ.pop("DEVELOPER_DIR", None)
        else:
            os.environ["DEVELOPER_DIR"] = saved
    cenv = c_runner.compile_env(host.state_path("tmp"))
    assert cenv.get("DEVELOPER_DIR") == dev and cenv.get("SDKROOT", "").startswith(dev), cenv
    assert cenv["PATH"].split(":")[0].startswith(dev), "the real toolchain comes before the /usr/bin shims"
    clang = c_runner.clang_path()
    assert clang.startswith(dev + "/") and os.access(clang, os.X_OK), clang
    assert host.which("clang") == clang, host.which("clang")
    for tool in host.XCRUN_SHIMS:
        real = host.dev_tool(tool)
        assert real is None or (real.startswith(dev + "/") and real != f"/usr/bin/{tool}"), (tool, real)
    res = host.run(["/usr/bin/git", "--version"], timeout=30)
    assert res.cmd[0] != "/usr/bin/git" and res.cmd[0].startswith(dev + "/"), res.cmd
    v = host.tool_version("clang")
    assert v and "clang" in v.lower(), v
    sb = host.SANDBOX_PROFILE.read_text()
    assert '(subpath (param "DEVDIR"))' in sb, "compile mode must read the developer dir"
    return {"developer_dir": dev, "clang": clang}


def test_setup_npm_skips_ci_when_installed_tree_matches_lock():
    """v2.2 bug fix: `npm ci` deletes node_modules before reinstalling, so a setup run (the
    write-jail test above runs one against the shared $PTK_STATE) pulled HyperFrames and Playwright
    out from under every concurrent build. Setup must leave a tree that already matches the pinned
    lock alone, and still run `npm ci` when the lock or the tree differs."""
    import shutil
    import tempfile
    from pathlib import Path
    from ptk import node
    tmp = Path(tempfile.mkdtemp(dir=host.state_path("tmp")))
    calls = []
    real_state_path, real_npm = host.state_path, node.npm
    try:
        host.state_path = lambda *p: tmp.joinpath(*p)
        node.npm = lambda args, cwd=None, **kw: calls.append(list(args))
        tools = tmp / "tools" / "node"
        mods = tools / "node_modules"
        lock = json.loads((host.PKG / "node" / "package-lock.json").read_text())
        for f in ("package.json", "package-lock.json"):
            tools.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(host.PKG / "node" / f, tools / f)
        mods.mkdir(parents=True)
        shutil.copyfile(host.PKG / "node" / "package-lock.json", mods / ".package-lock.json")
        for key, meta in lock.get("packages", {}).items():
            if key and not meta.get("link"):
                d = tools / key
                d.mkdir(parents=True, exist_ok=True)
                (d / "package.json").write_text(json.dumps({"version": meta.get("version")}))
        host._setup_npm({"id": "node-tools"})
        assert calls == [], f"npm ci ran over a tree that already matches the lock: {calls}"
        first = next(k for k, m in lock["packages"].items() if k and not m.get("link"))
        (tools / first / "package.json").write_text(json.dumps({"version": "0.0.0-wrong"}))
        host._setup_npm({"id": "node-tools"})
        assert calls and calls[-1][0] == "ci", "a tree that differs from the lock must be reinstalled"
    finally:
        host.state_path, node.npm = real_state_path, real_npm
        shutil.rmtree(tmp, ignore_errors=True)
    return {"skipped_when_current": True}
