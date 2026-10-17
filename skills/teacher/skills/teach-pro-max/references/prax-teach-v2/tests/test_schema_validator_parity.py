"""Regressions for the package's dependency-free JSON-Schema subset."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from praxteach.errors import ValidationError
from praxteach.state import validate_learner_document
from validate_workspace import _schema_instance_errors


class SchemaValidatorParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.learner = json.loads(
            (ROOT / "fixtures/schema-valid/learner.json").read_text(encoding="utf-8")
        )
        cls.learner_schema = json.loads(
            (ROOT / "schemas/learner.schema.json").read_text(encoding="utf-8")
        )

    def schema_errors(self, value: Any, schema: dict[str, Any] | bool) -> list[str]:
        root = schema if isinstance(schema, dict) else {}
        return _schema_instance_errors(value, schema, root, "instance")

    def test_union_type_rejects_values_outside_every_member(self) -> None:
        schema = {"type": ["integer", "null"], "minimum": 0}
        self.assertEqual(self.schema_errors(0, schema), [])
        self.assertEqual(self.schema_errors(None, schema), [])
        self.assertTrue(self.schema_errors("0", schema))
        self.assertTrue(self.schema_errors(False, schema))

    def test_if_then_else_rejects_disabled_fields_on_active_consent(self) -> None:
        learner = copy.deepcopy(self.learner)
        learner["consent"]["disabled_at"] = "2026-08-05T12:00:00Z"
        learner["consent"]["disable_reason"] = "Fields from an inactive consent"

        with self.assertRaisesRegex(ValidationError, "unsupported field"):
            validate_learner_document(learner, require_active=False)
        self.assertTrue(
            self.schema_errors(learner, self.learner_schema),
            msg="schema accepted disabled consent fields while persistence is active",
        )

    def test_if_then_else_accepts_each_valid_consent_branch(self) -> None:
        self.assertEqual(self.schema_errors(self.learner, self.learner_schema), [])

        inactive = copy.deepcopy(self.learner)
        inactive["consent"]["persistent_state"] = False
        inactive["consent"]["disabled_at"] = "2026-08-05T12:00:00Z"
        inactive["consent"]["disable_reason"] = "Learner withdrew consent"
        validate_learner_document(inactive, require_active=False)
        self.assertEqual(self.schema_errors(inactive, self.learner_schema), [])


if __name__ == "__main__":
    unittest.main()
