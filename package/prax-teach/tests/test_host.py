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
