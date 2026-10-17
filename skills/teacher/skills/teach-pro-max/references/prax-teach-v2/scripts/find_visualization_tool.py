#!/usr/bin/env python3
"""Query prax-teach's machine-readable visualization tool registry."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent
    / "references"
    / "visualization-tool-registry.json"
)


def load_registry() -> dict[str, Any]:
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"registry not found: {REGISTRY_PATH}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid registry JSON: {exc}")

    if not isinstance(data, dict) or not isinstance(data.get("tools"), list):
        raise SystemExit("invalid registry: top-level 'tools' must be a list")
    return data


def searchable_text(tool: dict[str, Any]) -> str:
    values: list[str] = [
        str(tool.get("id", "")),
        str(tool.get("name", "")),
        str(tool.get("summary", "")),
        str(tool.get("fallback", "")),
    ]
    values.extend(map(str, tool.get("aliases", [])))
    values.extend(map(str, tool.get("routes", [])))
    values.extend(map(str, tool.get("capabilities", [])))
    return " ".join(values).lower()


def score_query(tool: dict[str, Any], query: str) -> int:
    normalized = query.strip().lower()
    if not normalized:
        return 1
    words = re.findall(r"[a-z0-9.+#-]+", normalized)
    haystack = searchable_text(tool)
    score = sum(1 for word in words if word in haystack)
    if normalized == str(tool.get("id", "")).lower():
        score += 20
    if normalized == str(tool.get("name", "")).lower():
        score += 20
    if normalized in [str(x).lower() for x in tool.get("aliases", [])]:
        score += 15
    return score


def select_tools(
    tools: list[dict[str, Any]],
    query: str | None,
    route: str | None,
    trust: str | None,
) -> list[dict[str, Any]]:
    selected: list[tuple[int, dict[str, Any]]] = []
    normalized_query = (query or "").strip().lower()
    for tool in tools:
        if tool.get("disposition") == "do-not-route":
            exact_names = {
                str(tool.get("id", "")).lower(),
                str(tool.get("name", "")).lower(),
                *[str(item).lower() for item in tool.get("aliases", [])],
            }
            if normalized_query not in exact_names:
                continue
        if route and route.lower() not in [
            str(item).lower() for item in tool.get("routes", [])
        ]:
            continue
        if trust and trust.lower() != str(tool.get("trust", "")).lower():
            continue
        score = score_query(tool, query or "")
        if query and score == 0:
            continue
        selected.append((score, tool))
    selected.sort(key=lambda item: (-item[0], str(item[1].get("name", ""))))
    return [tool for _, tool in selected]


def format_links(label: str, links: list[dict[str, str]]) -> list[str]:
    if not links:
        return []
    lines = [f"{label}:"]
    for link in links:
        lines.append(f"  - {link.get('label', 'resource')}: {link.get('url', '')}")
    return lines


def local_skill_roots() -> list[Path]:
    """Return portable runtime probe roots, with an explicit override for tests."""

    configured = os.environ.get("PRAX_AGENT_SKILLS_ROOTS")
    if configured is not None:
        return [
            Path(item).expanduser() for item in configured.split(os.pathsep) if item
        ]
    return [Path.home() / ".agents" / "skills", Path.home() / ".codex" / "skills"]


def materialize_integration(integration: dict[str, Any]) -> dict[str, Any]:
    """Resolve a declarative local skill hint without replaying stale host state."""

    result = dict(integration)
    relative = integration.get("relative_skill_path")
    if not isinstance(relative, str):
        return result
    match = next(
        (
            candidate
            for root in local_skill_roots()
            if (candidate := root / relative).is_file()
        ),
        None,
    )
    result["availability_scope"] = "runtime-probe"
    result["availability"] = "available-local" if match else "unavailable-local"
    if match is not None:
        result["resolved_local_path"] = str(match)
    return result


def materialize_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Copy one registry entry and attach current-host integration availability."""

    result = dict(tool)
    result["agent_integrations"] = [
        materialize_integration(item)
        for item in tool.get("agent_integrations", [])
        if isinstance(item, dict)
    ]
    return result


def format_tool(tool: dict[str, Any]) -> str:
    routes = ", ".join(map(str, tool.get("routes", [])))
    lines = [
        f"{tool.get('name', tool.get('id', 'unknown'))} [{routes}]",
        f"trust={tool.get('trust', 'unspecified')}",
        str(tool.get("summary", "")).strip(),
    ]
    if tool.get("disposition"):
        lines.append(f"disposition={tool['disposition']}")
    official = tool.get("official", {})
    lines.extend(format_links("official docs", official.get("docs", [])))
    lines.extend(format_links("syntax/API", official.get("syntax", [])))
    lines.extend(format_links("examples", official.get("examples", [])))
    lines.extend(format_links("source", official.get("source", [])))

    integrations = tool.get("agent_integrations", [])
    if integrations:
        lines.append("agent integrations:")
        for item in integrations:
            state = item.get("availability", "unknown")
            trust = item.get("trust", "unclassified")
            lines.append(
                f"  - {item.get('name', 'integration')} "
                f"({item.get('type', 'unknown')}; {trust}; {state})"
            )
            if item.get("url"):
                lines.append(f"    {item['url']}")
            if item.get("resolved_local_path"):
                lines.append(f"    local: {item['resolved_local_path']}")
            elif item.get("relative_skill_path"):
                lines.append(f"    local probe: {item['relative_skill_path']}")

    installs = tool.get("install", [])
    if installs:
        lines.append("install:")
        for item in installs:
            lines.append(
                f"  - {item.get('environment', 'shell')}: {item.get('command', '')}"
            )
            if item.get("note"):
                lines.append(f"    {item['note']}")

    if tool.get("fallback"):
        lines.extend(["fallback:", f"  {tool['fallback']}"])
    verification = tool.get("verification", [])
    if verification:
        lines.append("verification:")
        lines.extend(f"  - {item}" for item in verification)
    if tool.get("licensing"):
        lines.extend(["licensing/provenance:", f"  {tool['licensing']}"])
    return "\n".join(line for line in lines if line)


def validate_registry(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    required = {"id", "name", "routes", "summary", "trust", "official", "fallback"}
    for index, tool in enumerate(data.get("tools", [])):
        if not isinstance(tool, dict):
            errors.append(f"tools[{index}] is not an object")
            continue
        missing = sorted(required - set(tool))
        if missing:
            errors.append(f"tools[{index}] missing: {', '.join(missing)}")
        tool_id = str(tool.get("id", ""))
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", tool_id):
            errors.append(f"tools[{index}] has invalid id: {tool_id!r}")
        if tool_id in seen:
            errors.append(f"duplicate tool id: {tool_id}")
        seen.add(tool_id)
        if not tool.get("routes"):
            errors.append(f"{tool_id or index} has no routes")
        official = tool.get("official", {})
        if not isinstance(official, dict):
            errors.append(f"{tool_id or index} official must be an object")
            continue
        urls: list[str] = []
        for section in ("docs", "syntax", "examples", "source"):
            for link in official.get(section, []):
                if isinstance(link, dict):
                    urls.append(str(link.get("url", "")))
        for integration in tool.get("agent_integrations", []):
            relative = integration.get("relative_skill_path")
            if relative is not None:
                relative_path = Path(str(relative))
                if relative_path.is_absolute() or ".." in relative_path.parts:
                    errors.append(
                        f"{tool_id or index} has unsafe relative skill path: {relative!r}"
                    )
            local_path = integration.get("local_path")
            if local_path is not None:
                errors.append(
                    f"{tool_id or index} embeds non-portable local_path: {local_path!r}"
                )
            if integration.get("availability") == "installed":
                errors.append(f"{tool_id or index} embeds stale installed availability")
            if integration.get("url"):
                urls.append(str(integration["url"]))
        for url in urls:
            if not url.startswith(("https://", "http://")):
                errors.append(f"{tool_id or index} has invalid URL: {url!r}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find the smallest suitable visualization tool and its trusted resources."
    )
    parser.add_argument("query", nargs="?", help="tool name, alias, or capability")
    parser.add_argument("--route", help="filter by route, e.g. structure or quantity")
    parser.add_argument("--trust", help="filter by exact trust classification")
    parser.add_argument("--list", action="store_true", help="list tool ids and routes")
    parser.add_argument(
        "--json", action="store_true", help="emit selected entries as JSON"
    )
    parser.add_argument(
        "--check", action="store_true", help="validate registry structure"
    )
    parser.add_argument(
        "--limit", type=int, default=8, help="maximum matches to emit (default: 8)"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data = load_registry()

    if args.check:
        errors = validate_registry(data)
        if errors:
            print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
            return 1
        print(f"registry valid: {len(data['tools'])} tools")
        return 0

    if args.list:
        for tool in sorted(data["tools"], key=lambda item: item["name"]):
            print(f"{tool['id']}\t{','.join(tool['routes'])}\t{tool['name']}")
        return 0

    if not args.query and not args.route and not args.trust:
        build_parser().print_help()
        return 2

    selected = select_tools(data["tools"], args.query, args.route, args.trust)
    selected = selected[: max(args.limit, 0)]
    if not selected:
        print("No matching visualization tools.", file=sys.stderr)
        return 1

    selected = [materialize_tool(tool) for tool in selected]
    if args.json:
        print(json.dumps(selected, indent=2, ensure_ascii=False))
    else:
        print("\n\n".join(format_tool(tool) for tool in selected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
