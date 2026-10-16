#!/usr/bin/env python3
"""Deterministic tests for the prax-teach visualization registry and lookup CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "references" / "visualization-tool-registry.json"
CLI = ROOT / "scripts" / "find_visualization_tool.py"


class VisualizationRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.tools = cls.data["tools"]
        cls.by_id = {tool["id"]: tool for tool in cls.tools}

    def run_cli(
        self, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_cli_schema_check(self) -> None:
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("registry valid", result.stdout)

    def test_ids_are_unique(self) -> None:
        ids = [tool["id"] for tool in self.tools]
        self.assertEqual(len(ids), len(set(ids)))

    def test_visual_router_technologies_are_covered(self) -> None:
        required = {
            "svg",
            "mermaid",
            "d2",
            "graphviz",
            "drawio",
            "vega-lite",
            "observable-plot",
            "echarts",
            "html",
            "javascript",
            "react-flow",
            "canvas-2d",
            "webgl",
            "manim",
            "motion-canvas",
            "remotion",
            "hyperframes",
            "openai-image-generation",
            "wikimedia-commons",
        }
        self.assertFalse(required - set(self.by_id))

    def test_exact_name_query_prefers_exact_tool(self) -> None:
        result = self.run_cli("mermaid", "--limit", "1", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        selected = json.loads(result.stdout)
        self.assertEqual(selected[0]["id"], "mermaid")

    def test_route_filter_only_returns_route(self) -> None:
        result = self.run_cli("--route", "quantity", "--json", "--limit", "100")
        self.assertEqual(result.returncode, 0, result.stderr)
        selected = json.loads(result.stdout)
        self.assertTrue(selected)
        self.assertTrue(all("quantity" in tool["routes"] for tool in selected))

    def test_default_motion_route_excludes_retired_video_engines(self) -> None:
        result = self.run_cli("--route", "change-over-time", "--json", "--limit", "100")
        self.assertEqual(result.returncode, 0, result.stderr)
        selected = {tool["id"] for tool in json.loads(result.stdout)}
        self.assertFalse({"motion-canvas", "remotion"} & selected)
        self.assertTrue({"manim", "hyperframes"} <= selected)

    def test_documented_film_routes_are_canonical_and_executable(self) -> None:
        router = (ROOT / "references/VISUALIZATION-ROUTER.md").read_text()
        expected = {
            "change-over-time": {"manim", "hyperframes"},
            "mathematics": {"manim"},
        }
        for route, required in expected.items():
            with self.subTest(route=route):
                self.assertIn(f"--route {route}", router)
                result = self.run_cli("--route", route, "--json", "--limit", "100")
                self.assertEqual(result.returncode, 0, result.stderr)
                selected = {tool["id"] for tool in json.loads(result.stdout)}
                self.assertTrue(required <= selected)

    def test_retired_engine_remains_inspectable_by_exact_name(self) -> None:
        result = self.run_cli("motion-canvas", "--json", "--limit", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        selected = json.loads(result.stdout)
        self.assertEqual(selected[0]["id"], "motion-canvas")
        self.assertEqual(selected[0]["disposition"], "do-not-route")

    def test_registry_is_portable_and_does_not_assert_installation(self) -> None:
        violations: list[str] = []
        for tool in self.tools:
            for integration in tool.get("agent_integrations", []):
                if integration.get("availability") == "installed":
                    violations.append(f"{tool['id']}: static installed state")
                path = integration.get("local_path")
                if path and Path(path).is_absolute():
                    violations.append(f"{tool['id']}: absolute path {path}")
        self.assertFalse(violations, "\n".join(violations))

    def test_query_probes_relative_skill_paths_at_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "svg-principal-engineer" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("# test\n", encoding="utf-8")
            env = os.environ.copy()
            env["PRAX_AGENT_SKILLS_ROOTS"] = str(root)
            result = self.run_cli("svg", "--limit", "1", "--json", env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            selected = json.loads(result.stdout)
            integration = selected[0]["agent_integrations"][0]
            self.assertEqual(integration["availability"], "available-local")
            self.assertEqual(integration["resolved_local_path"], str(skill))

    def test_official_resources_use_http(self) -> None:
        bad: list[str] = []
        for tool in self.tools:
            for group in tool["official"].values():
                for resource in group:
                    if not resource["url"].startswith(("https://", "http://")):
                        bad.append(f"{tool['id']}: {resource['url']}")
        self.assertFalse(bad, "\n".join(bad))

    def test_canvas_warning_prevents_false_skill_routing(self) -> None:
        canvas = self.by_id["canvas-2d"]
        text = " ".join([canvas["summary"], canvas["fallback"]]).lower()
        self.assertIn("dcanvas", text)
        self.assertIn("json canvas", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
