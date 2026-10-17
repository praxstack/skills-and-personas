"""Public command-line interface for the Prax Teach v2 learner core."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from .errors import ConsentRequired, PraxTeachError, ValidationError
from .export import export_workspace
from .routing import route_request, route_visual
from .scheduler import due_items, move_due_date, review_item, set_review_status
from .state import (
    DIMENSIONS,
    SOURCE_TYPES,
    add_source_record,
    append_observation,
    correct_event,
    delete_events,
    delete_workspace,
    disable_persistence,
    initialize_workspace,
    invalidate_events,
    make_observation,
    rebuild,
    reject_misconception,
    show_state,
)
from .visual_verify import verify_visual_delivery


def _now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _emit(value: Any) -> None:
    json.dump(
        value, sys.stdout, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    sys.stdout.write("\n")


def _add_timestamp(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--timestamp",
        help="ISO-8601 event time with UTC offset (defaults to the current UTC time)",
    )


def _optional_boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prax-teach",
        description="Consent-first learner evidence, projection, routing, and export.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    route = subparsers.add_parser("route", help="choose the least-cost teaching mode")
    route.add_argument("--request", required=True)
    route.add_argument("--answer-now", action="store_true")
    route.add_argument("--demote", action="store_true")
    route.add_argument("--mode", choices=("quick", "lesson", "course"))

    visual_route = subparsers.add_parser(
        "visual-route", help="choose the smallest representation for a learning job"
    )
    visual_route.add_argument("--job", required=True)
    visual_route.add_argument("--retrieval", action="store_true")
    visual_route.add_argument("--exact-quantitative", action="store_true")
    visual_route.add_argument("--static-sufficient", type=_optional_boolean)
    visual_route.add_argument(
        "--force", choices=("none", "static", "interactive", "motion")
    )

    visual_verify = subparsers.add_parser(
        "visual-verify", help="verify visual delivery and its static fallback"
    )
    visual_verify.add_argument("--route-output", required=True)
    visual_verify.add_argument("--source", required=True)
    visual_verify.add_argument("--html", required=True)
    visual_verify.add_argument("--forbidden-answer-file", required=True)
    visual_verify.add_argument("--receipt")
    visual_verify.add_argument("--check", action="store_true")

    init = subparsers.add_parser(
        "init", help="initialize a consented private workspace"
    )
    init.add_argument("workspace")
    init.add_argument("--learner-id", required=True)
    init.add_argument("--goal", required=True)
    init.add_argument("--horizon-days", type=int, default=30)
    init.add_argument(
        "--consent",
        action="store_true",
        help="confirm explicit consent for the printed scope and controls",
    )
    _add_timestamp(init)

    source_add = subparsers.add_parser(
        "source-add", help="add one reviewed, versioned source record"
    )
    source_add.add_argument("workspace")
    source_add.add_argument("--source-id", required=True)
    source_add.add_argument("--title", required=True)
    source_add.add_argument("--url", required=True)
    source_add.add_argument("--author-or-publisher", required=True)
    source_add.add_argument("--source-type", choices=SOURCE_TYPES, required=True)
    source_add.add_argument("--retrieved-at", required=True)
    source_add.add_argument("--version-or-date", required=True)
    source_add.add_argument("--license-or-use-note", required=True)
    source_add.add_argument("--supports", action="append", required=True)
    source_add.add_argument("--limitations", required=True)

    observe = subparsers.add_parser(
        "observe", help="append an observable practice event"
    )
    observe.add_argument("workspace")
    observe.add_argument("--session", required=True)
    observe.add_argument("--concept", required=True)
    observe.add_argument("--dimension", choices=DIMENSIONS, required=True)
    observe.add_argument("--score", type=float, required=True)
    observe.add_argument("--hint-level", type=int, required=True)
    observe.add_argument("--item", required=True)
    observe.add_argument("--item-version", required=True)
    observe.add_argument("--content-id", required=True)
    observe.add_argument("--content-version", required=True)
    observe.add_argument("--objective-id", required=True)
    observe.add_argument("--model-and-prompt-version", required=True)
    observe.add_argument("--source-id", required=True)
    observe.add_argument("--source-version", required=True)
    response = observe.add_mutually_exclusive_group(required=True)
    response.add_argument(
        "--response", help="exact inline learner response to preserve"
    )
    response.add_argument(
        "--response-ref", help="exact artifact or transcript reference for the response"
    )
    observe.add_argument("--confidence", type=float)
    observe.add_argument("--attempt-number", type=int, default=1)
    observe.add_argument("--learner-authored")
    observe.add_argument("--agent-inference-summary")
    observe.add_argument("--agent-inference-certainty", type=float)
    observe.add_argument("--misconception-claim")
    observe.add_argument("--learner-reasoning")
    observe.add_argument(
        "--misconception-provenance",
        choices=("learner_reported", "tutor_inference"),
    )
    observe.add_argument("--confirm-misconception", action="store_true")
    _add_timestamp(observe)

    rebuild_parser = subparsers.add_parser(
        "rebuild", help="replay evidence into deterministic projections"
    )
    rebuild_parser.add_argument("workspace")

    show = subparsers.add_parser("show", help="inspect the current learner model")
    show.add_argument("workspace")

    correct = subparsers.add_parser(
        "correct", help="append a compensating correction event"
    )
    correct.add_argument("workspace")
    correct.add_argument("--event-id", required=True)
    correct.add_argument("--reason", required=True)
    _add_timestamp(correct)

    reject = subparsers.add_parser(
        "reject-misconception",
        help="reject a misconception inference without deleting valid practice evidence",
    )
    reject.add_argument("workspace")
    reject.add_argument("--event-id", required=True)
    reject.add_argument("--reason", required=True)
    _add_timestamp(reject)

    for command in ("invalidate", "invalidate-version"):
        invalidate = subparsers.add_parser(
            command,
            help="append an auditable source/item version invalidation",
        )
        invalidate.add_argument("workspace")
        invalidate.add_argument("--event-id")
        invalidate.add_argument("--item")
        invalidate.add_argument("--item-version")
        invalidate.add_argument("--content-version")
        invalidate.add_argument("--source-id")
        invalidate.add_argument("--source-version")
        invalidate.add_argument("--reason", required=True)
        _add_timestamp(invalidate)

    delete = subparsers.add_parser("delete", help="physically delete scoped evidence")
    delete.add_argument("workspace")
    delete.add_argument("--event-id", action="append", default=[])
    delete.add_argument("--session")
    delete.add_argument("--concept")
    delete.add_argument("--item")
    delete.add_argument("--all-state", action="store_true")
    delete.add_argument("--dry-run", action="store_true")
    delete.add_argument("--confirm", action="store_true")

    disable = subparsers.add_parser(
        "disable-persistence",
        help="withdraw persistence consent while retaining inspect, export, and deletion controls",
    )
    disable.add_argument("workspace")
    disable.add_argument("--reason", required=True)
    _add_timestamp(disable)

    export = subparsers.add_parser(
        "export", help="create a deterministic learner archive"
    )
    export.add_argument("workspace")
    export.add_argument("output")
    _add_timestamp(export)

    review = subparsers.add_parser(
        "review",
        help="derive a transparent pinned FSRS transition from one observation",
    )
    review.add_argument("workspace")
    review.add_argument("--observation-event", required=True)

    due = subparsers.add_parser(
        "due", help="replay the learner-visible review queue at an explicit time"
    )
    due.add_argument("workspace")
    due.add_argument("--at", required=True)

    for command in ("snooze", "reschedule"):
        move = subparsers.add_parser(
            command, help=f"{command} one reviewed item with an auditable reason"
        )
        move.add_argument("workspace")
        move.add_argument("--item", required=True)
        move.add_argument("--until", required=True)
        move.add_argument("--reason", required=True)
        _add_timestamp(move)

    for command in ("disable-reviews", "enable-reviews"):
        controls = subparsers.add_parser(
            command, help="change the learner-controlled review queue status"
        )
        controls.add_argument("workspace")
        controls.add_argument("--reason", required=True)
        _add_timestamp(controls)
    return parser


def dispatch(args: argparse.Namespace) -> Any:
    if args.command == "route":
        try:
            return route_request(
                args.request,
                answer_now=args.answer_now,
                demote=args.demote,
                explicit_mode=args.mode,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
    if args.command == "visual-route":
        try:
            return route_visual(
                args.job,
                retrieval=args.retrieval,
                exact_quantitative=args.exact_quantitative,
                static_sufficient=args.static_sufficient,
                force=args.force,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
    if args.command == "visual-verify":
        return verify_visual_delivery(
            route_output=args.route_output,
            source=args.source,
            generated_html=args.html,
            forbidden_answer_file=args.forbidden_answer_file,
            receipt=args.receipt,
            check=args.check,
        )
    if args.command == "init":
        if not args.consent:
            raise ConsentRequired(
                "explicit consent is required before the learner workspace or any state file is created"
            )
        workspace, _ = initialize_workspace(
            args.workspace,
            learner_id=args.learner_id,
            goal=args.goal,
            horizon_days=args.horizon_days,
            granted_at=args.timestamp or _now(),
        )
        return {
            "consent_controls": ["inspect", "correct", "export", "delete"],
            "consent_scope": ["goal", "practice_evidence", "reviews"],
            "status": "initialized",
            "workspace": str(workspace),
        }
    if args.command == "observe":
        event = make_observation(
            session_id=args.session,
            concept_id=args.concept,
            dimension=args.dimension,
            score=args.score,
            hint_level=args.hint_level,
            item_id=args.item,
            item_version=args.item_version,
            content_id=args.content_id,
            content_version=args.content_version,
            objective_id=args.objective_id,
            model_and_prompt_version=args.model_and_prompt_version,
            source_id=args.source_id,
            source_version=args.source_version,
            timestamp=args.timestamp or _now(),
            response=args.response,
            response_ref=args.response_ref,
            confidence=args.confidence,
            attempt_number=args.attempt_number,
            learner_authored=args.learner_authored,
            agent_inference_summary=args.agent_inference_summary,
            agent_inference_certainty=args.agent_inference_certainty,
            misconception_claim=args.misconception_claim,
            learner_reasoning=args.learner_reasoning,
            misconception_provenance=args.misconception_provenance,
            misconception_learner_confirmed=args.confirm_misconception,
        )
        return append_observation(args.workspace, event)
    if args.command == "source-add":
        return add_source_record(
            args.workspace,
            {
                "author_or_publisher": args.author_or_publisher,
                "license_or_use_note": args.license_or_use_note,
                "limitations": args.limitations,
                "retrieved_at": args.retrieved_at,
                "source_id": args.source_id,
                "source_type": args.source_type,
                "supports": args.supports,
                "title": args.title,
                "url": args.url,
                "version_or_date": args.version_or_date,
            },
        )
    if args.command == "rebuild":
        concepts, misconceptions = rebuild(args.workspace)
        return {
            "concept_count": len(concepts["concepts"]),
            "misconception_count": len(misconceptions["misconceptions"]),
            "status": "rebuilt",
        }
    if args.command == "show":
        return show_state(args.workspace)
    if args.command == "correct":
        return correct_event(
            args.workspace,
            event_id=args.event_id,
            reason=args.reason,
            timestamp=args.timestamp or _now(),
        )
    if args.command == "reject-misconception":
        return reject_misconception(
            args.workspace,
            event_id=args.event_id,
            reason=args.reason,
            timestamp=args.timestamp or _now(),
        )
    if args.command in {"invalidate", "invalidate-version"}:
        if not any(
            (
                args.event_id,
                args.item,
                args.item_version,
                args.content_version,
                args.source_id,
            )
        ):
            raise ValidationError(
                "invalidation requires --event-id, --item, --item-version, --content-version, or --source-id"
            )
        return invalidate_events(
            args.workspace,
            event_id=args.event_id,
            item_id=args.item,
            item_version=args.item_version,
            content_version=args.content_version,
            source_id=args.source_id,
            source_version=args.source_version,
            reason=args.reason,
            timestamp=args.timestamp or _now(),
        )
    if args.command == "delete":
        if args.all_state and any(
            (args.event_id, args.session, args.concept, args.item)
        ):
            raise ValidationError(
                "--all-state cannot be combined with scoped selectors"
            )
        if not args.all_state and not any(
            (args.event_id, args.session, args.concept, args.item)
        ):
            raise ValidationError(
                "deletion requires an event, session, concept, item, or --all-state selector"
            )
        if args.dry_run and args.confirm:
            raise ValidationError("choose either --dry-run or --confirm, not both")
        operation = delete_workspace if args.all_state else delete_events
        return operation(
            args.workspace,
            dry_run=args.dry_run,
            confirm=args.confirm,
            **(
                {}
                if args.all_state
                else {
                    "event_ids": args.event_id,
                    "session_id": args.session,
                    "concept_id": args.concept,
                    "item_id": args.item,
                }
            ),
        )
    if args.command == "disable-persistence":
        return disable_persistence(
            args.workspace,
            reason=args.reason,
            timestamp=args.timestamp or _now(),
        )
    if args.command == "export":
        return export_workspace(
            args.workspace,
            args.output,
            exported_at=args.timestamp or _now(),
        )
    if args.command == "review":
        return review_item(
            args.workspace,
            observation_event_id=args.observation_event,
        )
    if args.command == "due":
        return due_items(args.workspace, at=args.at)
    if args.command in {"snooze", "reschedule"}:
        return move_due_date(
            args.workspace,
            event_type=args.command,
            item_id=args.item,
            until=args.until,
            reason=args.reason,
            timestamp=args.timestamp or _now(),
        )
    if args.command in {"disable-reviews", "enable-reviews"}:
        return set_review_status(
            args.workspace,
            enabled=args.command == "enable-reviews",
            reason=args.reason,
            timestamp=args.timestamp or _now(),
        )
    raise ValidationError(f"unsupported command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        _emit(dispatch(args))
        return 0
    except PraxTeachError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except (OSError, UnicodeError) as exc:
        print(f"error: safe state operation failed: {exc}", file=sys.stderr)
        return 8


if __name__ == "__main__":
    raise SystemExit(main())
