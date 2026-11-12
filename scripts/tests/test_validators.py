"""Regression tests for the stdlib-only graph contract validators."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "scripts" / "testdata"


def load_validator(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace("-", "_").removesuffix(".py"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


plan_validator = load_validator("validate-plan.py")
result_validator = load_validator("validate-results.py")


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((DATA / "plan-valid.json").read_text(encoding="utf-8"))

    def test_valid_fixture(self):
        self.assertEqual(plan_validator.validate(self.plan), [])

    def test_all_negative_fixtures(self):
        for path in sorted(DATA.glob("plan-*.json")):
            if path.name == "plan-valid.json":
                continue
            with self.subTest(fixture=path.name):
                errors = plan_validator.validate(json.loads(path.read_text(encoding="utf-8")))
                self.assertTrue(errors, path.name)

    def test_malformed_types_do_not_raise(self):
        value = copy.deepcopy(self.plan)
        value["nodes"][0].update(executor=[], tier=[], risk=[], requires={"unexpected": True})
        value["nodes"].append({"id": [], "requires": []})
        value["edges"][0]["from"] = []
        value["constraints"][0]["type"] = []
        value["gates"][0]["before"] = []
        errors = plan_validator.validate(value)
        self.assertGreaterEqual(len(errors), 7)

    def test_invalid_dependency_output_name(self):
        self.plan["nodes"][1]["requires"] = ["recon.typo"]
        self.assertIn("invalid requires entry", " ".join(plan_validator.validate(self.plan)))

    def test_missing_phase_node(self):
        self.plan["phases"][-1]["nodes"] = []
        self.assertIn("missing from phases", " ".join(plan_validator.validate(self.plan)))

    def test_duplicate_phase_node(self):
        self.plan["phases"][1]["nodes"].append("recon")
        self.assertIn("multiple phase entries", " ".join(plan_validator.validate(self.plan)))

    def test_reversed_phase_order(self):
        self.plan["phases"][1]["phase"] = 2
        self.plan["phases"][2]["phase"] = 1
        self.assertIn("violates phase order", " ".join(plan_validator.validate(self.plan)))

    def test_invalid_phase_shape(self):
        self.plan["phases"][0].update(phase=True, mode=[], batch_size=0)
        errors = plan_validator.validate(self.plan)
        self.assertTrue(any("phase must be a non-negative integer" in e for e in errors))
        self.assertTrue(any("mode must be" in e for e in errors))
        self.assertTrue(any("batch_size" in e for e in errors))

    def test_untrimmed_reason_and_bad_cardinality(self):
        self.plan["edges"][0]["reason"] = "  "
        self.plan["nodes"][0]["cardinality"] = True
        errors = plan_validator.validate(self.plan)
        self.assertTrue(any("reason" in e for e in errors))
        self.assertTrue(any("cardinality" in e for e in errors))

    def test_long_dag_and_cycle_without_recursion(self):
        ids = {f"n{i}" for i in range(2000)}
        edges = [(f"n{i}", f"n{i+1}") for i in range(1999)]
        self.assertEqual(plan_validator.has_cycle(ids, edges), [])
        cycle = plan_validator.has_cycle(ids, edges + [("n1999", "n0")])
        self.assertTrue(cycle and "n0" in cycle[0])

    def test_schema_document_example_is_valid(self):
        document = (ROOT / "references" / "plan-schema.md").read_text(encoding="utf-8")
        match = re.search(r"```json\s*(.*?)\s*```", document, flags=re.DOTALL)
        self.assertIsNotNone(match)
        example = json.loads(match.group(1))
        self.assertEqual(plan_validator.validate(example), [])


class ResultsTests(unittest.TestCase):
    def setUp(self):
        self.expected = result_validator.load_expected(str(DATA / "expected-ids.json"))
        self.items = result_validator.load_results(str(DATA / "results-complete.jsonl"))

    def test_valid_results(self):
        self.assertEqual(result_validator.validate(self.expected, self.items), [])

    def test_missing_result_ids(self):
        incomplete = result_validator.load_results(str(DATA / "results-gap.jsonl"))
        errors = result_validator.validate(self.expected, incomplete)
        self.assertIn("missing ids: src/auth/baz.ts", errors)

    def test_nonhashable_status_and_confidence(self):
        self.items[0]["status"] = []
        self.items[0]["confidence"] = []
        errors = result_validator.validate(self.expected, self.items)
        self.assertTrue(any("status" in e for e in errors))
        self.assertTrue(any("confidence" in e for e in errors))

    def test_evidence_must_have_nonblank_source_and_claim(self):
        self.items[0]["evidence"] = [{"source": None, "claim": " "}]
        self.assertIn("non-blank source and claim", " ".join(result_validator.validate(self.expected, self.items)))

    def test_ok_items_must_not_report_errors(self):
        self.items[0]["errors"] = ["unexpected"]
        self.assertIn("ok status must have no errors", " ".join(result_validator.validate(self.expected, self.items)))

    def test_failed_items_need_error(self):
        self.items[2]["errors"] = []
        self.assertIn("failed status must include an error", " ".join(result_validator.validate(self.expected, self.items)))

    def test_error_elements_are_strings(self):
        self.items[2]["errors"] = [123]
        self.assertIn("non-blank string", " ".join(result_validator.validate(self.expected, self.items)))

    def test_expected_id_files_reject_duplicates_and_empty(self):
        for expected, message in [
            ('["a", "a"]', "duplicates"),
            ('[]', "non-empty"),
            ('["a", " "]', "non-blank"),
            ("a\na\n", "duplicates"),
        ]:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "expected.txt"
                path.write_text(expected, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    result_validator.load_expected(str(path))

    def test_cli_reports_gap_without_traceback(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate-results.py"),
                str(DATA / "expected-ids.json"),
                str(DATA / "results-gap.jsonl"),
            ],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("missing ids", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)


if __name__ == "__main__":
    unittest.main()
