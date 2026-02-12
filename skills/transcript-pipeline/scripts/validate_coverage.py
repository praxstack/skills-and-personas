#!/usr/bin/env python3
"""Deterministic Stage-4 validator for transcript pipeline artifacts.

No API usage. Pure local deterministic checks.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SOURCE_TAG_RE = re.compile(r"\[source:\s*([^\]]+)\]", re.IGNORECASE)
SEGMENT_ID_RE = re.compile(r"[A-Za-z0-9._:-]*seg-\d{4,}")


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def parse_source_ids_from_text(text: str) -> set[str]:
    ids: set[str] = set()
    for match in SOURCE_TAG_RE.findall(text):
        parts = re.split(r"[,\s]+", match.strip())
        for part in parts:
            token = part.strip().strip("`[](){}")
            if token and SEGMENT_ID_RE.fullmatch(token):
                ids.add(token)
    return ids


def extract_segment_ids_from_obj(obj: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(obj, str):
        token = obj.strip().strip("`[](){}")
        if SEGMENT_ID_RE.fullmatch(token):
            ids.add(token)
        return ids

    if isinstance(obj, list):
        for item in obj:
            ids |= extract_segment_ids_from_obj(item)
        return ids

    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and SEGMENT_ID_RE.fullmatch(key.strip()):
                ids.add(key.strip())

            if key in {"segment_id", "source", "source_id"} and isinstance(value, str):
                candidate = value.strip().strip("`[](){}")
                if SEGMENT_ID_RE.fullmatch(candidate):
                    ids.add(candidate)

            ids |= extract_segment_ids_from_obj(value)
        return ids

    return ids


def parse_coverage_matrix(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    obj = json.loads(path.read_text(encoding="utf-8"))
    return extract_segment_ids_from_obj(obj)


def parse_unresolved_uncertainty_ids(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        rows = data["items"]
    elif isinstance(data, list):
        rows = data
    else:
        rows = [data]

    unresolved: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        seg_id = row.get("segment_id")
        if not isinstance(seg_id, str):
            continue

        status = str(row.get("status", "")).lower()
        tier = str(row.get("confidence_tier", "")).upper()
        resolved = row.get("resolved")

        if status in {"open", "unresolved"} or tier == "LOW" or resolved is False:
            unresolved.add(seg_id)

    return unresolved


def resolve_paths(args: argparse.Namespace) -> dict[str, Path | None]:
    if args.pipeline_dir:
        pipeline_dir = Path(args.pipeline_dir).expanduser().resolve()
        ledger = pipeline_dir / "segment_ledger.jsonl"
        final_notes = Path(args.final_notes).expanduser().resolve() if args.final_notes else pipeline_dir.parent / "final_notes.md"
        coverage = Path(args.coverage_matrix).expanduser().resolve() if args.coverage_matrix else pipeline_dir / "coverage_matrix.json"
        uncertainty = Path(args.uncertainty_report).expanduser().resolve() if args.uncertainty_report else pipeline_dir / "uncertainty_report.json"
        review_queue = Path(args.human_review_queue).expanduser().resolve() if args.human_review_queue else pipeline_dir / "human_review_queue.md"
        report_out = Path(args.report_out).expanduser().resolve() if args.report_out else pipeline_dir / "validation_report.md"
        exceptions_out = Path(args.exceptions_out).expanduser().resolve() if args.exceptions_out else pipeline_dir / "exceptions.json"
        return {
            "ledger": ledger,
            "final_notes": final_notes,
            "coverage": coverage,
            "uncertainty": uncertainty,
            "review_queue": review_queue,
            "report_out": report_out,
            "exceptions_out": exceptions_out,
        }

    required = [args.ledger, args.final_notes, args.report_out, args.exceptions_out]
    if any(v is None for v in required):
        raise ValueError("Provide either --pipeline-dir or the explicit required arguments.")

    return {
        "ledger": Path(args.ledger).expanduser().resolve(),
        "final_notes": Path(args.final_notes).expanduser().resolve(),
        "coverage": Path(args.coverage_matrix).expanduser().resolve() if args.coverage_matrix else None,
        "uncertainty": Path(args.uncertainty_report).expanduser().resolve() if args.uncertainty_report else None,
        "review_queue": Path(args.human_review_queue).expanduser().resolve() if args.human_review_queue else None,
        "report_out": Path(args.report_out).expanduser().resolve(),
        "exceptions_out": Path(args.exceptions_out).expanduser().resolve(),
    }


def write_markdown_report(
    output_path: Path,
    passed: bool,
    summary: dict,
    missing_content: list[str],
    missing_noise_reason: list[str],
    orphan_sources: list[str],
    missing_uncertain: list[str],
) -> None:
    lines: list[str] = []
    lines.append("# Validation Report")
    lines.append("")
    lines.append(f"- **status:** {'PASS' if passed else 'FAIL'}")
    lines.append(f"- **segments_total:** {summary['segments_total']}")
    lines.append(f"- **segments_content:** {summary['segments_content']}")
    lines.append(f"- **segments_noise:** {summary['segments_noise']}")
    lines.append(f"- **source_ids_in_notes:** {summary['source_ids_in_notes']}")
    lines.append(f"- **source_ids_in_coverage_matrix:** {summary['source_ids_in_coverage_matrix']}")
    lines.append(f"- **missing_content_count:** {len(missing_content)}")
    lines.append(f"- **missing_noise_reason_count:** {len(missing_noise_reason)}")
    lines.append(f"- **orphan_source_count:** {len(orphan_sources)}")
    lines.append(f"- **missing_uncertainty_retention_count:** {len(missing_uncertain)}")
    lines.append("")

    if missing_content:
        lines.append("## Missing Content Segment IDs")
        lines.extend(f"- `{sid}`" for sid in missing_content[:300])
        lines.append("")

    if missing_noise_reason:
        lines.append("## Noise Segments Missing Reason")
        lines.extend(f"- `{sid}`" for sid in missing_noise_reason[:300])
        lines.append("")

    if orphan_sources:
        lines.append("## Orphan Source IDs (Referenced But Not In Ledger)")
        lines.extend(f"- `{sid}`" for sid in orphan_sources[:300])
        lines.append("")

    if missing_uncertain:
        lines.append("## Missing Uncertainty Retention IDs")
        lines.extend(f"- `{sid}`" for sid in missing_uncertain[:300])
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic validation for transcript pipeline artifacts.")
    parser.add_argument("--pipeline-dir", help="Path to .pipeline directory")
    parser.add_argument("--ledger", help="Path to segment_ledger.jsonl")
    parser.add_argument("--final-notes", help="Path to final_notes.md")
    parser.add_argument("--coverage-matrix", help="Path to coverage_matrix.json")
    parser.add_argument("--uncertainty-report", help="Path to uncertainty_report.json")
    parser.add_argument("--human-review-queue", help="Path to human_review_queue.md")
    parser.add_argument("--report-out", help="Path to validation_report.md")
    parser.add_argument("--exceptions-out", help="Path to exceptions.json")
    args = parser.parse_args()

    try:
        paths = resolve_paths(args)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    ledger_path = paths["ledger"]
    final_notes_path = paths["final_notes"]
    coverage_path = paths["coverage"]
    uncertainty_path = paths["uncertainty"]
    review_queue_path = paths["review_queue"]
    report_out = paths["report_out"]
    exceptions_out = paths["exceptions_out"]

    if ledger_path is None or not ledger_path.exists():
        print(f"ERROR: ledger not found: {ledger_path}")
        return 2
    if final_notes_path is None or not final_notes_path.exists():
        print(f"ERROR: final notes not found: {final_notes_path}")
        return 2

    ledger_rows = read_jsonl(ledger_path)
    notes_text = final_notes_path.read_text(encoding="utf-8")

    source_ids_from_notes = parse_source_ids_from_text(notes_text)
    source_ids_from_matrix = parse_coverage_matrix(coverage_path)
    mapped_source_ids = source_ids_from_notes | source_ids_from_matrix

    ledger_ids = {row.get("segment_id") for row in ledger_rows if isinstance(row.get("segment_id"), str)}
    content_ids = {
        row["segment_id"]
        for row in ledger_rows
        if isinstance(row.get("segment_id"), str)
        and str(row.get("segment_type", row.get("type", "content"))).lower() != "noise"
    }
    noise_ids = {
        row["segment_id"]
        for row in ledger_rows
        if isinstance(row.get("segment_id"), str)
        and str(row.get("segment_type", row.get("type", "content"))).lower() == "noise"
    }

    missing_content = sorted(sid for sid in content_ids if sid not in mapped_source_ids)
    missing_noise_reason = sorted(
        row["segment_id"]
        for row in ledger_rows
        if isinstance(row.get("segment_id"), str)
        and str(row.get("segment_type", row.get("type", "content"))).lower() == "noise"
        and not str(row.get("noise_reason", "")).strip()
    )
    orphan_sources = sorted(sid for sid in mapped_source_ids if sid not in ledger_ids)

    unresolved_uncertain = parse_unresolved_uncertainty_ids(uncertainty_path)
    retained_uncertain = {sid for sid in unresolved_uncertain if sid in mapped_source_ids}
    if review_queue_path and review_queue_path.exists():
        queue_text = review_queue_path.read_text(encoding="utf-8")
        retained_uncertain |= {sid for sid in unresolved_uncertain if sid in queue_text}
    missing_uncertain = sorted(unresolved_uncertain - retained_uncertain)

    passed = not missing_content and not missing_noise_reason and not orphan_sources and not missing_uncertain

    summary = {
        "segments_total": len(ledger_rows),
        "segments_content": len(content_ids),
        "segments_noise": len(noise_ids),
        "source_ids_in_notes": len(source_ids_from_notes),
        "source_ids_in_coverage_matrix": len(source_ids_from_matrix),
    }

    write_markdown_report(
        output_path=report_out,
        passed=passed,
        summary=summary,
        missing_content=missing_content,
        missing_noise_reason=missing_noise_reason,
        orphan_sources=orphan_sources,
        missing_uncertain=missing_uncertain,
    )

    exceptions_payload = {
        "status": "PASS" if passed else "FAIL",
        "summary": summary,
        "failed_gates": {
            "segment_accountability": {
                "missing_content_segment_ids": missing_content,
                "noise_missing_reason_segment_ids": missing_noise_reason,
            },
            "uncertainty_retention": {
                "missing_uncertainty_segment_ids": missing_uncertain,
            },
            "orphan_claims": {
                "orphan_source_ids": orphan_sources,
            },
        },
    }
    exceptions_out.parent.mkdir(parents=True, exist_ok=True)
    exceptions_out.write_text(json.dumps(exceptions_payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    print(f"status: {'PASS' if passed else 'FAIL'}")
    print(f"wrote: {report_out}")
    print(f"wrote: {exceptions_out}")
    if missing_content:
        print(f"missing_content_count: {len(missing_content)}")
    if missing_noise_reason:
        print(f"missing_noise_reason_count: {len(missing_noise_reason)}")
    if orphan_sources:
        print(f"orphan_source_count: {len(orphan_sources)}")
    if missing_uncertain:
        print(f"missing_uncertainty_retention_count: {len(missing_uncertain)}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
