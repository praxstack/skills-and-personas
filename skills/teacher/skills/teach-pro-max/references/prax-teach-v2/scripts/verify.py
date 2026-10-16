#!/usr/bin/env python3
"""Run reproducible Prax Teach v2 verification gates and emit one receipt."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from review_payload import distributable_mode

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EPOCH = "1785844800"
FULL_RECEIPT = ROOT / "evidence/verification/full.json"
RECEIPT_RELATIVE = FULL_RECEIPT.relative_to(ROOT).as_posix()
PRUNED_DIRECTORIES = {
    ".agent",
    ".agents",
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "attempts",
    "env",
    "hidden-bank",
    "hidden-banks",
    "hidden_bank",
    "hidden_banks",
    "learner-workspace",
    "learner-workspaces",
    "learner_workspace",
    "learner_workspaces",
    "node_modules",
    "private-bank",
    "private-banks",
    "private_bank",
    "private_banks",
    "runs",
    "openspec",
    "venv",
}
LOG_RETENTION = {
    "full_logs_persisted": False,
    "retained": ["sha256", "tail"],
    "tail_line_limit": 12,
}


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def release_file_manifest() -> dict[str, Any]:
    """Fingerprint every durable release byte except this self-referential receipt."""

    files: list[dict[str, Any]] = []
    for current, directory_names, file_names in os.walk(ROOT, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in sorted(directory_names):
            if name in PRUNED_DIRECTORIES or name.endswith(("_cache", "-cache")):
                continue
            path = current_path / name
            if path.is_symlink():
                raise RuntimeError(f"release tree contains a directory symlink: {path}")
            kept.append(name)
        directory_names[:] = kept
        for name in sorted(file_names):
            path = current_path / name
            relative = path.relative_to(ROOT).as_posix()
            if relative == RECEIPT_RELATIVE:
                continue
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise RuntimeError(
                    f"release tree contains a non-regular file: {relative}"
                )
            files.append(
                {
                    "mode": distributable_mode(metadata.st_mode),
                    "path": relative,
                    "sha256": sha256_file(path),
                }
            )
    files.sort(key=lambda item: item["path"])
    encoded = json.dumps(
        files, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return {
        "algorithm": "sha256(canonical-json(files[path,mode,sha256]))",
        "excluded": [RECEIPT_RELATIVE, ".git/", "runtime/cache directories"],
        "file_count": len(files),
        "files": files,
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def command_version(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return f"unavailable (exit {completed.returncode})"
    return (completed.stdout or completed.stderr).strip().splitlines()[0]


def dependency_receipt() -> dict[str, Any]:
    locks = {}
    for relative in (
        "package-lock.json",
        "uv.lock",
        "integrations/flint/package-lock.json",
        "integrations/skillopt/SOURCE.json",
    ):
        path = ROOT / relative
        locks[relative] = sha256_file(path)
    try:
        fsrs_version = importlib.metadata.version("fsrs")
    except importlib.metadata.PackageNotFoundError:
        fsrs_version = "unavailable"
    return {
        "installed": {
            "fsrs": fsrs_version,
            "node": command_version(["node", "--version"]),
            "npm": command_version(["npm", "--version"]),
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "ruff": command_version(["ruff", "--version"]),
        },
        "locks": locks,
    }


def git_source_receipt(source: Path) -> dict[str, Any]:
    def git(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=source,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"could not fingerprint SkillOpt source: {' '.join(arguments)}"
            )
        return completed.stdout.strip()

    status = git("status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError(
            "SkillOpt source worktree must be clean for full verification"
        )
    return {
        "commit": git("rev-parse", "HEAD"),
        "path": str(source),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "worktree_clean": True,
    }


def tail(value: str, lines: int = 12) -> list[str]:
    return value.splitlines()[-lines:]


def run_gate(
    name: str, command: list[str], environment: dict[str, str]
) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    combined = completed.stdout + completed.stderr
    policy_failures: list[str] = []
    if (
        name == "python-tests"
        and environment.get("PRAX_RUN_MACOS_SANDBOX_TESTS") == "1"
    ):
        if re.search(r"\.\.\.\s+skipped\b", combined, re.IGNORECASE):
            policy_failures.append(
                "a Python test skipped while trusted macOS sandbox tests were mandatory"
            )
        for required_test in (
            "test_builtin_macos_sandbox_blocks_adversarial_access",
            "test_builtin_macos_sandbox_passes_adversarial_probes_and_unlocks_held_out",
        ):
            if required_test not in combined:
                policy_failures.append(
                    f"required trusted sandbox E2E was not executed: {required_test}"
                )
    effective_exit = completed.returncode if not policy_failures else 1
    return {
        "command": command,
        "exit_code": effective_exit,
        "name": name,
        "output_sha256": sha256_text(combined),
        "output_tail": tail(combined),
        "policy_failures": policy_failures,
        "status": "passed" if effective_exit == 0 else "failed",
    }


def write_atomic(path: Path, contents: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=("core", "full"), default="full")
    parser.add_argument("--skillopt-source", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    environment = dict(os.environ)
    environment["SOURCE_DATE_EPOCH"] = environment.get(
        "SOURCE_DATE_EPOCH", DEFAULT_EPOCH
    )
    if (
        sys.platform == "darwin"
        and Path("/usr/bin/sandbox-exec").is_file()
        and environment.get("PRAX_DISABLE_MACOS_SANDBOX_TESTS") != "1"
    ):
        environment["PRAX_RUN_MACOS_SANDBOX_TESTS"] = "1"
    skillopt_source_receipt = None
    if args.skillopt_source:
        source = args.skillopt_source.expanduser().resolve()
        if not source.is_dir():
            parser.error(f"--skillopt-source is not a directory: {source}")
        environment["SKILLOPT_SOURCE"] = str(source)
    elif args.level == "full" and not environment.get("SKILLOPT_SOURCE"):
        parser.error("full verification requires --skillopt-source or SKILLOPT_SOURCE")
    if args.level == "full":
        source = Path(environment["SKILLOPT_SOURCE"]).expanduser().resolve()
        try:
            skillopt_source_receipt = git_source_receipt(source)
        except RuntimeError as exc:
            parser.error(str(exc))
        if (
            skillopt_source_receipt["commit"]
            != "e4ea6a6771e797ef820cdd8bfea64c57e0481065"
        ):
            parser.error("SkillOpt source does not match the exact pinned commit")

    receipt_path = args.receipt.expanduser().resolve() if args.receipt else None
    if args.level == "full":
        if receipt_path is None:
            receipt_path = FULL_RECEIPT
        if receipt_path != FULL_RECEIPT:
            parser.error(f"full verification receipt must be {FULL_RECEIPT}")

    source_manifest = release_file_manifest()
    generated_at = datetime.fromtimestamp(
        int(environment["SOURCE_DATE_EPOCH"]), tz=timezone.utc
    ).isoformat()
    run_id = sha256_text(
        f"{source_manifest['sha256']}:{args.level}:{environment['SOURCE_DATE_EPOCH']}"
    )[:32]
    receipt_base = {
        "dependencies": dependency_receipt(),
        "evidence_level": "engineering-verification",
        "external_human_learning_gates_satisfied": False,
        "generated_at": generated_at,
        "level": args.level,
        "log_retention": LOG_RETENTION,
        "root_manifest": source_manifest,
        "run_id": run_id,
        "schema_version": 3,
        "scientific_learning_claim_supported": False,
        "source_date_epoch": environment["SOURCE_DATE_EPOCH"],
        "skillopt_source": skillopt_source_receipt,
        "trusted_macos_sandbox_tests_required": environment.get(
            "PRAX_RUN_MACOS_SANDBOX_TESTS"
        )
        == "1",
        "verification_script_sha256": sha256_file(Path(__file__).resolve()),
    }
    environment["PRAX_ACTIVE_VERIFICATION_RUN_ID"] = run_id
    if receipt_path:
        write_atomic(
            receipt_path,
            stable_json({**receipt_base, "gates": [], "status": "running"}),
        )

    python_tests = [
        "test_core_cli.py",
        "test_evaluation_harness.py",
        "test_exports_cli.py",
        "test_scheduler_cli.py",
        "test_state_security.py",
        "test_study_cli.py",
        "test_validator_cli.py",
        "test_visual_routing.py",
    ]
    if args.level == "full":
        python_tests.append("test_skillopt_adapter.py")

    # unittest has no multi-pattern option. Discover all Python tests at the full
    # level; at core, run explicit modules so the optional SkillOpt source is not
    # required.
    if args.level == "full":
        python_command = [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
            "-v",
        ]
    else:
        modules = [f"tests.{Path(name).stem}" for name in python_tests]
        python_command = [sys.executable, "-m", "unittest", "-v", *modules]

    gates: list[tuple[str, list[str]]] = [
        ("python-tests", python_command),
        (
            "node-tests",
            [
                "npm",
                "test",
                "--silent",
            ]
            if args.level == "full"
            else ["node", "--test", "tests/render_markdown.test.mjs"],
        ),
        (
            "visual-registry-tests",
            [sys.executable, "scripts/test_visualization_registry.py"],
        ),
        (
            "visual-registry-count",
            [sys.executable, "scripts/find_visualization_tool.py", "--check"],
        ),
        ("html-exact-parity", ["node", "scripts/render_all.mjs", "--check", "."]),
        (
            "package-validator",
            [sys.executable, "scripts/validate_workspace.py", "--json", "."],
        ),
        (
            "python-lint",
            [
                "ruff",
                "check",
                "scripts",
                "integrations/skillopt",
                "tests",
            ],
        ),
        (
            "python-format",
            [
                "ruff",
                "format",
                "--check",
                "scripts",
                "integrations/skillopt",
                "tests",
            ],
        ),
    ]

    results = [run_gate(name, command, environment) for name, command in gates]
    passed = all(result["exit_code"] == 0 for result in results)
    receipt = {
        **receipt_base,
        "gates": results,
        "status": "passed" if passed else "failed",
    }
    # Keep the run-bound ``running`` receipt in place while the final validator
    # executes. A completed receipt requires a successful postflight field, so
    # publishing ``passed`` before that field exists creates a schema state the
    # validator must reject. Only publish an intermediate completed receipt when
    # no full postflight will follow (a failed gate or a core-only run).
    if receipt_path and not (passed and args.level == "full"):
        write_atomic(receipt_path, stable_json(receipt))
    if passed and args.level == "full" and receipt_path:
        postflight_command = [
            sys.executable,
            "scripts/validate_workspace.py",
            "--json",
            ".",
        ]
        postflight = subprocess.run(
            postflight_command,
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        combined = postflight.stdout + postflight.stderr
        receipt["postflight_validation"] = {
            "command": postflight_command,
            "exit_code": postflight.returncode,
            "output_sha256": sha256_text(combined),
            "output_tail": tail(combined),
            "status": "passed" if postflight.returncode == 0 else "failed",
        }
        if postflight.returncode != 0:
            passed = False
            receipt["status"] = "failed"
        write_atomic(receipt_path, stable_json(receipt))
    rendered = stable_json(receipt)
    if args.as_json or not passed:
        sys.stdout.write(rendered)
    else:
        print(f"PASS: {len(results)} verification gates ({args.level})")
        for result in results:
            print(f"- {result['name']}: {result['status']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
