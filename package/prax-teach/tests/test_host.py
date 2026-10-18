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
    allowed = set(host.program_env()) | set(host.CONTRACT) | {"PLAYWRIGHT_BROWSERS_PATH", "SOURCE_DATE_EPOCH"}
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
