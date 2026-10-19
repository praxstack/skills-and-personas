#!/usr/bin/env python3
"""Run one bounded CLI review against a small exported task pack, never a repo.

Provider read-only modes are tool policies, not an OS security boundary. Exit
zero means the worker returned; a separate reviewer must accept its answer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def inventory(root):
    result = {}
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Task packs must not contain symlinks")
        if not path.is_file():
            continue
        total += path.stat().st_size
        if len(result) >= 200 or total > 8_000_000:
            raise ValueError("Export a task pack of at most 200 files / 8 MB")
        result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def child_environment():
    env = os.environ.copy()
    for name in list(env):
        if (name.endswith(("_API_KEY", "_API_TOKEN")) or name in {
            "CURSOR_AUTH_TOKEN", "CURSOR_API_ENDPOINT", "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_BASE_URL", "OPENAI_BASE_URL", "XAI_BASE_URL",
        }):
            env.pop(name, None)
    return env


def command(provider, task, workspace):
    binary = shutil.which("grok" if provider == "grok" else "cursor-agent")
    if not binary:
        raise ValueError("Provider executable is not installed")
    if provider == "grok":
        return [binary, "--permission-mode", "plan", "--no-subagents",
                "--disable-web-search", "--max-turns", "4", "--output-format",
                "json", "--prompt-file", str(task)]
    return [binary, "--mode", "ask", "--model", "composer-2.5", "--print",
            "--output-format", "json", "--workspace", str(workspace),
            task.read_text()]


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def run(provider, task, workspace, output, timeout):
    workspace, task, output = workspace.resolve(), task.resolve(), output.resolve()
    if not workspace.is_dir() or not task.is_file():
        raise ValueError("Task file and workspace directory must exist")
    if not task.is_relative_to(workspace):
        raise ValueError("Task must be inside the exported task pack")
    if output.is_relative_to(workspace):
        raise ValueError("Evidence must be outside the input task pack")
    if task.stat().st_size > 32_000:
        raise ValueError("Keep TASK.md below 32 KB; put source material in separate files")
    before = inventory(workspace)
    argv = command(provider, task, workspace)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    started = time.time()
    receipt = {"provider": provider, "model_requested": "composer-2.5" if provider == "cursor" else "provider default",
               "task_sha256": before[str(task.relative_to(workspace))],
               "timeout_seconds": timeout, "input_inventory": before,
               "acceptance": "not_reviewed", "status": "starting"}
    process = None
    try:
        with (output / "stdout.json").open("wb") as stdout, (output / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(argv, cwd=workspace, env=child_environment(),
                                       stdin=subprocess.DEVNULL, stdout=stdout,
                                       stderr=stderr, start_new_session=True)
            try:
                exit_code = process.wait(timeout=timeout)
                receipt.update(exit_code=exit_code, status="returned_requires_review" if exit_code == 0 else "provider_failed")
            except subprocess.TimeoutExpired:
                stop_process(process)
                receipt.update(exit_code=process.returncode, status="local_process_timed_out")
        after = inventory(workspace)
        receipt["changed_input_files"] = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
        if receipt["changed_input_files"]:
            receipt["status"] = "input_modified_reject"
    except KeyboardInterrupt:
        stop_process(process)
        receipt.update(status="interrupted", exit_code=process.returncode if process else None)
    except Exception as error:
        stop_process(process)
        # Store the error class only; arbitrary provider/OS exception strings can contain secrets.
        receipt.update(status="runner_failed", error_type=type(error).__name__)
    finally:
        receipt["elapsed_seconds"] = round(time.time() - started, 3)
        receipt["output_inventory"] = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.iterdir()) if path.is_file()
        }
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("grok", "cursor"), required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 180:
        parser.error("timeout must be between 1 and 180 seconds")
    try:
        receipt = run(args.provider, args.task, args.workspace, args.output, args.timeout)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({key: receipt[key] for key in ("provider", "status", "acceptance", "elapsed_seconds")}))
    return 0 if receipt["status"] == "returned_requires_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
