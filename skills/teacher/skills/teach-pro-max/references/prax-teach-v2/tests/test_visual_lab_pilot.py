import importlib.util
import json
import unittest
from pathlib import Path

PILOT = (
    Path(__file__).resolve().parents[1]
    / "examples/visual-lab/python-floating-point/pilot.py"
)
SPEC = importlib.util.spec_from_file_location("visual_lab_pilot", PILOT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class VisualLabPilotTests(unittest.TestCase):
    def test_float_and_decimal_transfer(self):
        self.assertEqual(MODULE.observe()["result"], 0.30000000000000004)
        self.assertFalse(MODULE.observe()["exact_decimal"])
        self.assertEqual(MODULE.transfer()["exact_decimal_result"], "0.8")

    def test_python_model_matches_independent_literal_parity_vectors(self):
        vectors = json.loads(
            (PILOT.with_name("parity-vectors.json")).read_text(encoding="utf-8")
        )
        for vector in vectors:
            self.assertEqual(
                MODULE.observe(vector["a"], vector["b"], vector["expected_decimal"]),
                vector["expected"],
            )


if __name__ == "__main__":
    unittest.main()
