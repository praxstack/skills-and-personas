#!/usr/bin/env python3
"""Recompute the canonical zero-API tracker and its browser view."""

from __future__ import annotations

import hashlib
import html
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[3]
TRACKER_ROOT = REPOSITORY / "docs/teach-pro-max/research"
TRACKER = TRACKER_ROOT / "09-zero-api-visual-runtime-tracker.json"
MARKDOWN = TRACKER.with_suffix(".md")
WEB = TRACKER.with_suffix(".html")

EVIDENCE = {
    "ZV-00": ["evidence/zero-api-visual-runtime/baseline.json"],
    "ZV-01": [
        "references/NO-API-ARCHITECTURE.md",
        "openspec/changes/zero-api-visual-runtime/design.md",
    ],
    "ZV-02": [
        "scripts/verify_visual_runtime.py",
        "evidence/zero-api-visual-runtime/verification.json",
    ],
    "ZV-03": ["references/CAPABILITY-ADAPTIVE-EXECUTION.md"],
    "ZV-04": [
        "runtime/prax-visual-lab/contracts/visual-lesson.schema.json",
        "runtime/prax-visual-lab/contracts/learning-receipt.schema.json",
        "runtime/prax-visual-lab/tests/core.test.mjs",
    ],
    "ZV-05": [
        "references/EVIDENCE-PROTOCOL.md",
        "runtime/prax-visual-lab/src/index.html",
    ],
    "ZV-06": [
        "runtime/prax-visual-lab/package.json",
        "runtime/prax-visual-lab/build.mjs",
    ],
    "ZV-07": [
        "runtime/prax-visual-lab/src/components.mjs",
        "runtime/prax-visual-lab/tests/core.test.mjs",
    ],
    "ZV-08": [
        "runtime/prax-visual-lab/src/components.mjs",
        "runtime/prax-visual-lab/tests/core.test.mjs",
    ],
    "ZV-09": [
        "runtime/prax-visual-lab/src/core.mjs",
        "runtime/prax-visual-lab/tests/core.test.mjs",
    ],
    "ZV-10": [
        "examples/visual-lab/python-floating-point/pilot.py",
        "tests/test_visual_lab_pilot.py",
    ],
    "ZV-11": [
        "runtime/prax-visual-lab/src/index.html",
        "evidence/zero-api-visual-runtime/verification.json",
    ],
    "ZV-12": [
        "evidence/zero-api-visual-runtime/verification.json",
        "evidence/verification/full.json",
    ],
    "ZV-13": ["evidence/zero-api-visual-runtime/pilot-review.json"],
    "ZV-14": [
        "runtime/prax-visual-lab/src/components.mjs",
        "runtime/prax-visual-lab/tests/core.test.mjs",
    ],
    "ZV-15": [
        "runtime/prax-visual-lab/src/components.mjs",
        "runtime/prax-visual-lab/tests/core.test.mjs",
    ],
    "ZV-16": [
        "runtime/prax-visual-lab/src/core.mjs",
        "runtime/prax-visual-lab/tests/core.test.mjs",
    ],
    "ZV-17": [
        "runtime/prax-visual-lab/build.mjs",
        "runtime/prax-visual-lab/dist/manifest.json",
    ],
    "ZV-18": [
        "examples/visual-lab/rubiks-move-lab/lesson.json",
        "runtime/prax-visual-lab/tests/core.test.mjs",
    ],
    "ZV-19": [
        "examples/visual-lab/lost-update-lab/lesson.json",
        "runtime/prax-visual-lab/tests/core.test.mjs",
    ],
    "ZV-20": ["runtime/prax-visual-lab/tests/core.test.mjs"],
    "ZV-21": [
        "evidence/verification/full.json",
        "evidence/zero-api-visual-runtime/verification.json",
    ],
    "ZV-22": [
        "references/FORMAL-VERIFICATION.md",
        "evidence/zero-api-visual-runtime/lean-decision.json",
    ],
    "ZV-23": ["integrations/formal/lean/adapter.py", "tests/test_formal_adapter.py"],
    "ZV-24": [
        "examples/visual-lab/lean-proof-state/lesson.json",
        "examples/visual-lab/lean-proof-state/proof-state.json",
    ],
    "ZV-25": ["evidence/zero-api-visual-runtime/lean-decision.json"],
    "ZV-26": ["references/EVIDENCE-PROTOCOL.md"],
    "ZV-27": [
        "scripts/visual_evidence.py",
        "evidence/zero-api-visual-runtime/evidence-receipt.json",
    ],
    "ZV-28": [
        "references/EVIDENCE-PROTOCOL.md",
        "evidence/zero-api-visual-runtime/study-operations.json",
    ],
    "ZV-29": ["evidence/zero-api-visual-runtime/study-operations.json"],
    "ZV-30": ["evidence/zero-api-visual-runtime/optional-adapters.json"],
    "ZV-31": ["scripts/render_all.mjs", "evidence/verification/full.json"],
    "ZV-32": [
        "evidence/reviews/payload.json",
        "evidence/reviews/code-standards.json",
        "evidence/reviews/frozen-spec.json",
        "evidence/reviews/architecture-council.json",
    ],
    "ZV-33": [
        "evidence/zero-api-visual-runtime/clean-room.json",
        "evidence/verification/full.json",
    ],
    "ZV-34": ["evidence/zero-api-visual-runtime/archive-receipt.json"],
    "ZV-35": [
        "evidence/zero-api-visual-runtime/rollback.md",
        "evidence/zero-api-visual-runtime/truthful-handoff.md",
    ],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracker_timestamp() -> str:
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1785844800"))
    if epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be non-negative")
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def json_evidence_usable(identifier: str, document: object) -> bool:
    if not isinstance(document, dict):
        return False
    status = str(document.get("status", "")).lower()
    if any(word in status for word in ("failed", "invalid", "error")):
        return False
    return not (identifier == "ZV-25" and document.get("decision") == "deferred")


def review_payload_current() -> bool:
    from review_payload import payload_manifest

    path = ROOT / "evidence/reviews/payload.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) == payload_manifest(ROOT)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False


def full_receipt_current() -> bool:
    from verify import release_file_manifest

    path = ROOT / "evidence/verification/full.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        return (
            document.get("status") == "passed"
            and document.get("root_manifest") == release_file_manifest()
        )
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError):
        return False


def review_receipt_current(path: Path) -> bool:
    payload_path = ROOT / "evidence/reviews/payload.json"
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return (
        review_payload_current()
        and receipt.get("status") == "passed"
        and receipt.get("payload_manifest_sha256") == payload.get("sha256")
        and receipt.get("payload_file_sha256") == sha256(payload_path)
        and not receipt.get("unresolved_actionable")
    )


def archive_receipt_current(path: Path) -> bool:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        archive = ROOT / str(receipt["archive"])
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return (
            receipt.get("status") == "packaged"
            and receipt.get("package_commit") == head
            and archive.is_file()
            and receipt.get("archive_sha256") == sha256(archive)
        )
    except (
        KeyError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ):
        return False


def evidence_current(identifier: str, relative: str) -> bool:
    path = ROOT / relative
    if not path.is_file() or path.stat().st_size == 0:
        return False
    if relative == "evidence/verification/full.json":
        return full_receipt_current()
    if relative == "evidence/reviews/payload.json":
        return review_payload_current()
    if relative.startswith("evidence/reviews/") and relative.endswith(".json"):
        return review_receipt_current(path)
    if relative == "evidence/zero-api-visual-runtime/archive-receipt.json":
        return archive_receipt_current(path)
    if path.suffix != ".json":
        return True
    try:
        return json_evidence_usable(
            identifier, json.loads(path.read_text(encoding="utf-8"))
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False


def main() -> None:
    document = json.loads(TRACKER.read_text(encoding="utf-8"))
    now = tracker_timestamp()
    for criterion in document["criteria"]:
        identifier = criterion["id"]
        if identifier.startswith("EG-"):
            criterion["status"] = "waiting_external"
            criterion["evidence"] = []
        else:
            paths = EVIDENCE.get(identifier, [])
            dependencies_pass = all(
                next(item for item in document["criteria"] if item["id"] == dependency)[
                    "status"
                ]
                in {"verified", "waiting_external"}
                for dependency in criterion.get("dependencies", [])
            )
            criterion["status"] = (
                "verified"
                if paths
                and dependencies_pass
                and all(evidence_current(identifier, path) for path in paths)
                else "pending"
            )
            criterion["evidence"] = [
                {"path": path, "kind": "receipt" if path.endswith(".json") else "path"}
                for path in EVIDENCE.get(identifier, [])
            ]
    engineering = [
        item for item in document["criteria"] if item["type"] == "engineering"
    ]
    external = [item for item in document["criteria"] if item["type"] == "external"]
    engineering_verified = sum(item["status"] == "verified" for item in engineering)
    external_verified = sum(item["status"] == "verified" for item in external)
    document["updated_at"] = now
    document["progress"] = {
        "engineering": {
            "verified": engineering_verified,
            "total": len(engineering),
            "percent": round(engineering_verified / len(engineering) * 100),
        },
        "external": {
            "verified": external_verified,
            "total": len(external),
            "percent": round(external_verified / len(external) * 100),
        },
        "overall_claim": "ENGINEERING_IN_PROGRESS / SCIENTIFIC_EVIDENCE_PENDING",
    }
    TRACKER.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rows = [
        "# Prax Teach v2 — Zero-API Visual Runtime Upgrade Tracker",
        "",
        f"> Updated {now}. JSON is canonical; this is a generated view.",
        "",
        "| Track | Verified | Total | Progress | Claim |",
        "|---|---:|---:|---:|---|",
        f"| Engineering | {engineering_verified} | {len(engineering)} | {document['progress']['engineering']['percent']}% | Engineering work only |",
        f"| External learner evidence | {external_verified} | {len(external)} | {document['progress']['external']['percent']}% | Waiting for genuine observations |",
        "",
        "| ID | Phase | Status | Evidence |",
        "|---|---:|---|---|",
    ]
    for item in document["criteria"]:
        evidence = (
            ", ".join(
                item.get("evidence", [])
                and [entry["path"] for entry in item["evidence"]]
            )
            or "—"
        )
        rows.append(
            f"| {item['id']} | {item['phase']} | `{item['status']}` | {evidence} |"
        )
    rows += [
        "",
        "## Claim boundary",
        "",
        "Engineering fixtures, agent reviews, automated accessibility checks, and generated receipts do not satisfy the four external gates. The honest current state remains engineering progress with scientific evidence pending.",
        "",
        "## Promotion gates",
        "",
        "Global install/replacement, merge, push, deploy, publication, paid calls, participant recruitment, and material deletion remain human-authorized actions.",
    ]
    MARKDOWN.write_text("\n".join(rows) + "\n", encoding="utf-8")
    criteria_rows = "".join(
        f'<tr><th scope="row">{html.escape(item["id"])}</th><td>{item["phase"]}</td><td><code>{html.escape(item["status"])}</code></td><td>{html.escape(", ".join(entry["path"] for entry in item.get("evidence", [])) or "—")}</td></tr>'
        for item in document["criteria"]
    )
    body = (
        "<h1>Prax Teach v2 — Zero-API Visual Runtime Upgrade Tracker</h1>"
        "<p>Generated from the canonical JSON tracker.</p>"
        f"<table><caption>Progress</caption><thead><tr><th>Track</th><th>Verified</th><th>Total</th><th>Progress</th></tr></thead><tbody><tr><th>Engineering</th><td>{engineering_verified}</td><td>{len(engineering)}</td><td>{document['progress']['engineering']['percent']}%</td></tr><tr><th>External learner evidence</th><td>{external_verified}</td><td>{len(external)}</td><td>{document['progress']['external']['percent']}%</td></tr></tbody></table>"
        f"<table><caption>Criteria</caption><thead><tr><th>ID</th><th>Phase</th><th>Status</th><th>Evidence</th></tr></thead><tbody>{criteria_rows}</tbody></table>"
        "<h2>Claim boundary</h2><p>Engineering fixtures and automated checks do not satisfy external learner gates. Scientific evidence remains pending.</p>"
    )
    WEB.write_text(
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Zero-API Visual Runtime Tracker</title><style>body{{font:16px system-ui;max-width:1000px;margin:auto;padding:2rem}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}th,td{{border:1px solid #777;padding:.4rem;text-align:left}}caption{{font-weight:700;text-align:left;padding:.5rem 0}}</style></head><body><a href="#criteria">Skip to criteria</a><main id="criteria">{body}</main><footer><p>Generated view; edit the JSON source.</p></footer></body></html>\n',
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "tracker": str(TRACKER),
                "engineering": f"{engineering_verified}/{len(engineering)}",
                "external": f"{external_verified}/{len(external)}",
            }
        )
    )


if __name__ == "__main__":
    main()
