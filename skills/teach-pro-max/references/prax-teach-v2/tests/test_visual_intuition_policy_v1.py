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
        fixture = json.loads(
            (ROOT / "fixtures/routing-cases-visual-intuition-v1.json").read_text()
        )
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                options = {
                    key: case[key]
                    for key in ("answer_now", "explicit_mode")
                    if key in case
                }
                result = route_request(case["request"], **options)
                for key, value in case["expected"].items():
                    self.assertEqual(result[key], value)

    def test_ordinary_non_teaching_requests_stay_ordinary(self):
        for request in (
            "Summarize this meeting",
            "What version of PostgreSQL is installed?",
            "Summarize this course syllabus",
            "Proofread this lesson",
            "Can you translate this paragraph?",
            "Quickly summarize this meeting",
        ):
            with self.subTest(request=request):
                result = route_request(request)
                self.assertEqual(result["action"], "ordinary_task")
                self.assertIsNone(result["mode"])
                self.assertFalse(result["persistence"])

    def test_explicit_teaching_intent_wins_over_ordinary_verbs(self):
        for request in (
            "Teach me how to proofread",
            "Help me learn how to translate a paragraph",
            "Proofread this lesson and teach me how to improve it",
        ):
            with self.subTest(request=request):
                self.assertEqual(route_request(request)["mode"], "lesson")

    def test_direct_teaching_artifact_creation(self):
        for request, mode in (
            ("Build an interactive lesson", "lesson"),
            ("Build a course for beginners", "course"),
            ("Create a lesson on fractions", "lesson"),
            ("Build a course for Python beginners", "course"),
        ):
            with self.subTest(request=request):
                result = route_request(request)
                self.assertEqual(result["action"], "teach")
                self.assertEqual(result["mode"], mode)
                self.assertEqual(
                    result["persistence"],
                    "consent_required" if mode == "course" else False,
                )

    def test_teaching_keywords_in_engineering_objects_are_ordinary(self):
        for request in (
            "Build a course scheduler in Python",
            "Create lesson routing in the CLI",
        ):
            with self.subTest(request=request):
                result = route_request(request)
                self.assertEqual(result["action"], "ordinary_task")
                self.assertIsNone(result["mode"])

    def assert_route(self, request, mode, *, action="teach", **options):
        result = route_request(request, **options)
        self.assertEqual(result["action"], action)
        self.assertEqual(result["mode"], mode)
        self.assertEqual(
            result["persistence"],
            "consent_required" if mode == "course" else False,
        )
        self.assertTrue(result["reason"].strip())

    def test_ordinary_tasks_precede_teaching_keywords_and_brevity(self):
        for request in (
            "Edit this lesson",
            "Delete this course",
            "Update this curriculum",
            "Remove this lesson",
            "Could you please edit this lesson?",
            "Can you please quickly delete this course?",
            "Please quickly edit this lesson",
            "Quickly write a poem",
            "Would you quickly write a poem?",
            "Write a poem in one sentence",
            "Fix this Python function",
            "Build a course scheduler in Python",
            "Build me a course scheduler in Python",
            "Create lesson routing in the CLI",
            "Create a lesson routing module",
            "Create a Python function that builds a course for beginners",
        ):
            variants = (
                request,
                "  \t" + request.swapcase().replace(" ", " \n ") + "  ",
                request + " in two minutes",
            )
            if not request.lower().startswith(("can ", "could ", "would ", "will ")):
                variants += ("Could you please quickly " + request, "Briefly " + request)
            for variant in variants:
                with self.subTest(request=variant):
                    self.assert_route(variant, None, action="ordinary_task")

    def test_direct_artifact_object_survives_polite_wrappers(self):
        for request, mode in (
            ("Build an interactive lesson", "lesson"),
            ("Build a course for beginners", "course"),
            ("Create a lesson on fractions", "lesson"),
            ("Build a course for Python beginners", "course"),
            ("Create a lesson on Python debugging", "lesson"),
        ):
            for prefix in ("", "Please ", "Could you please "):
                with self.subTest(request=prefix + request):
                    self.assert_route(prefix + request, mode)
            with self.subTest(request="Briefly " + request):
                self.assert_route("Briefly " + request, "quick")

    def test_course_and_resume_topic_nouns_do_not_imply_sequence(self):
        for request in (
            "Teach me the meaning of resume",
            "Explain the word course",
            "Teach me what a course is",
            "Teach me the difference between a course and a lesson",
            "Teach me fractions",
            "Teach me how to edit a lesson",
            "Help me learn how to translate a paragraph",
            "Proofread this lesson and teach me how to improve it",
        ):
            with self.subTest(request=request):
                self.assert_route(request, "lesson")
        self.assert_route("Explain the meaning of resume in one sentence", "quick")

    def test_affirmative_sequence_and_resumption_intent(self):
        for request in (
            "Resume my networking course",
            "Continue where we stopped",
            "I am resuming: the state says one heavily hinted application answer",
            "Help me learn algebra over six weeks",
            "Build a six-week course and let me resume it across sessions",
            "Build me a six-week course on database performance and remember my progress across sessions.",
        ):
            with self.subTest(request=request):
                self.assert_route(request, "course")

    def test_api_overrides_precede_ordinary_task_detection(self):
        request = "Delete this course"
        for mode in ("quick", "lesson", "course", "adapter-mode"):
            with self.subTest(mode=mode):
                self.assert_route(request, mode, explicit_mode=mode)
        self.assert_route(request, "quick", demote=True, explicit_mode="course")
        self.assert_route(
            request, "quick", action="answer_now", answer_now=True,
            demote=True, explicit_mode="course",
        )

    def test_existing_answer_now_wording_keeps_first_precedence(self):
        for override in (
            "answer now", "just give me the result", "just tell me the result",
            "just show me the result", "no questions", "no more Socratic",
            "skip questions", "skip the lesson", "skip the ceremony",
        ):
            with self.subTest(override=override):
                self.assert_route(
                    "Delete this course; " + override,
                    "quick", action="answer_now", demote=True, explicit_mode="course",
                )

    def test_empty_requests_still_fail_before_overrides(self):
        for request in ("", " \t\n "):
            with self.subTest(request=request):
                with self.assertRaisesRegex(ValueError, "request must not be empty"):
                    route_request(request, answer_now=True, demote=True, explicit_mode="course")

    def test_explanation_is_not_retrieval(self):
        result = route_visual("Compare equal-sized fraction parts", retrieval=False)
        self.assertFalse(result["retrieval_safety"]["required"])

    def test_requested_quiz_keeps_retrieval_safety(self):
        result = route_visual("Compare fraction parts for a quiz", retrieval=True)
        self.assertTrue(result["retrieval_safety"]["required"])
        self.assertIn("source_code", result["retrieval_safety"]["surfaces_to_check"])

    def test_policy_v1_complete_delivery_and_optional_check(self):
        skill = " ".join((ROOT / "SKILL.md").read_text().split())
        for phrase in (
            "complete bounded lesson",
            "at most one optional intuition check",
            "retrieval=false",
            "save-nothing",
            "active consent",
            "essential",
            "two repair attempts",
        ):
            self.assertIn(phrase, skill)


if __name__ == "__main__":
    unittest.main()
