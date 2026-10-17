from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.skill = " ".join(source.split())
        protocol = (ROOT / "references" / "TEACHING-PROTOCOL.md").read_text(
            encoding="utf-8"
        )
        cls.protocol = " ".join(protocol.split())
        artifact = (ROOT / "references" / "ARTIFACT-CONTRACT.md").read_text(
            encoding="utf-8"
        )
        cls.artifact = " ".join(artifact.split())
        mode = (ROOT / "references" / "MODE-CONTRACT.md").read_text(encoding="utf-8")
        cls.mode = " ".join(mode.split())
        router = (ROOT / "references" / "VISUALIZATION-ROUTER.md").read_text(
            encoding="utf-8"
        )
        legacy_router = (
            ROOT / "references" / "LEGACY-VISUALIZATION-ROUTER.md"
        ).read_text(encoding="utf-8")
        cls.router = " ".join(router.split())
        cls.legacy_router = " ".join(legacy_router.split())
        cls.public_cases = json.loads(
            (ROOT / "references" / "eval-cases.json").read_text(encoding="utf-8")
        )["cases"]
        cls.forward_cases = json.loads(
            (ROOT / "evals" / "forward-behavior.json").read_text(encoding="utf-8")
        )["cases"]

    def test_live_lesson_gate_requires_turn_boundary_and_complete_close(self) -> None:
        required = (
            "end the current turn at that attempt",
            "Do not call a named hint ladder progressive unless",
            "After an incorrect attempt, give exactly one next-needed hint",
            "end that tutor turn before any stronger hint or explanatory model",
            "no learner performance has been observed",
            "explicit retention horizon",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill)

    def test_course_consent_gate_exposes_ephemeral_path_before_consent(self) -> None:
        self.assertIn(
            "continue ephemerally without learner-state files",
            self.skill,
        )
        self.assertIn("before asking for persistence consent", self.skill)
        ephemeral = "If you decline persistence, we can continue in"
        consent = "whether to persist"
        self.assertIn(ephemeral, self.skill)
        self.assertLess(self.skill.index(ephemeral), self.skill.index(consent))

    def test_resume_gate_preserves_scaffold_metadata_and_retests(self) -> None:
        required = (
            "original response and exact hint level",
            "unchanged and inspectable",
            "fresh unassisted retrieval or discrimination prompt",
            "If the workspace path or topic is missing",
            "Never infer a filesystem path, score, timestamp, or prior attempt",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill)

    def test_post_error_hint_turn_precedes_substantive_feedback(self) -> None:
        required = (
            "Immediate post-error return gate",
            "exactly one next-needed hint",
            "end the tutor turn",
            "substantive feedback contract applies only after that revised learner turn",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.protocol)

    def test_session_close_labels_a_provisional_retention_horizon(self) -> None:
        self.assertIn("Retention horizon: <duration>", self.protocol)
        self.assertIn("Do not call the horizon unspecified", self.protocol)

    def test_unbundled_interaction_response_keeps_accessibility_claim_bounded(
        self,
    ) -> None:
        required = (
            "delivered through host chat with no custom artifact controls or scripts",
            "every learner action in an explicit text label in reading order",
            "complete static instructions and equivalent data",
            "host-UI keyboard, focus, reduced-motion, and assistive-technology behavior remains unverified",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill)

    def test_practical_learning_is_one_existing_teaching_mode(self) -> None:
        required = (
            "predict → run → inspect → modify → debug → explain → transfer",
            "Practical learning is a mode of this teaching protocol",
            "Engineering evidence is not learning evidence",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.protocol)

    def test_executable_visuals_share_an_authoritative_model_or_prove_parity(
        self,
    ) -> None:
        required = (
            "authoritative executable model",
            "independently specified literal parity vectors",
            "Do not add a scene or trace schema",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.artifact)
        self.assertIn(
            "Prefer direct reuse of one authoritative executable model",
            self.artifact,
        )

    def test_course_resume_and_adapters_keep_pedagogy_in_the_core(self) -> None:
        self.assertIn("exactly one next learner action", self.mode)
        self.assertIn("Adapters contain no teaching policy", self.mode)

    def test_public_and_forward_fixtures_cover_practical_execution(self) -> None:
        public_ids = {case["id"] for case in self.public_cases}
        forward_ids = {case["id"] for case in self.forward_cases}
        self.assertIn("practical-executable-learning", public_ids)
        self.assertIn("practical-executable-learning", forward_ids)
        self.assertNotIn("accessible-interaction-fallback", forward_ids)
        self.assertEqual(len(self.forward_cases), 8)
        takeover = "takes over or completes the learner's project"
        for cases in (self.public_cases, self.forward_cases):
            practical = next(
                case for case in cases if case["id"] == "practical-executable-learning"
            )
            self.assertIn(takeover, practical["forbidden"])

    def test_practical_forward_case_binds_replayable_execution(self) -> None:
        script = ROOT / "evidence/forward/execution/practical_gradient_descent.py"
        expected = ROOT / "evidence/forward/execution/practical_gradient_descent.stdout"
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.stderr, "")
        self.assertEqual(completed.stdout, expected.read_text(encoding="utf-8"))
        run = json.loads(
            (ROOT / "evidence/forward/run.json").read_text(encoding="utf-8")
        )
        execution = run["execution_files"]
        for path in (script, expected):
            relative = path.relative_to(ROOT).as_posix()
            self.assertEqual(
                execution[relative], hashlib.sha256(path.read_bytes()).hexdigest()
            )

    def test_scene_graph_requires_a_real_state_consumer(self) -> None:
        required = "playback, scrubbing, or synchronized-output consumer"
        self.assertIn(required, self.router)
        self.assertIn(required, self.legacy_router)


if __name__ == "__main__":
    unittest.main()
