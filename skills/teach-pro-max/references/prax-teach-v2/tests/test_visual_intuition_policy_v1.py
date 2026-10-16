from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from praxteach.routing import route_request, route_visual


class VisualIntuitionPolicyV1Tests(unittest.TestCase):
    def test_versioned_public_routing(self):
        fixture = json.loads((ROOT / "fixtures/routing-cases-visual-intuition-v1.json").read_text())
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                options = {key: case[key] for key in ("answer_now", "explicit_mode") if key in case}
                result = route_request(case["request"], **options)
                for key, value in case["expected"].items():
                    self.assertEqual(result[key], value)

    def test_ordinary_non_teaching_requests_stay_ordinary(self):
        for request in (
            "Summarize this meeting", "What version of PostgreSQL is installed?",
            "Summarize this course syllabus", "Proofread this lesson",
            "Can you translate this paragraph?", "Quickly summarize this meeting",
        ):
            with self.subTest(request=request):
                result = route_request(request)
                self.assertEqual(result["action"], "ordinary_task")
                self.assertIsNone(result["mode"])
                self.assertFalse(result["persistence"])

    def test_explicit_teaching_intent_wins_over_ordinary_verbs(self):
        for request in ("Teach me how to proofread", "Help me learn how to translate a paragraph", "Proofread this lesson and teach me how to improve it"):
            with self.subTest(request=request):
                self.assertEqual(route_request(request)["mode"], "lesson")

    def test_explanation_is_not_retrieval(self):
        result = route_visual("Compare equal-sized fraction parts", retrieval=False)
        self.assertFalse(result["retrieval_safety"]["required"])

    def test_requested_quiz_keeps_retrieval_safety(self):
        result = route_visual("Compare fraction parts for a quiz", retrieval=True)
        self.assertTrue(result["retrieval_safety"]["required"])
        self.assertIn("source_code", result["retrieval_safety"]["surfaces_to_check"])

    def test_policy_v1_complete_delivery_and_optional_check(self):
        skill = " ".join((ROOT / "SKILL.md").read_text().split())
        for phrase in ("complete bounded lesson", "at most one optional intuition check", "retrieval=false", "save-nothing", "active consent", "essential", "two repair attempts"):
            self.assertIn(phrase, skill)


if __name__ == "__main__":
    unittest.main()
