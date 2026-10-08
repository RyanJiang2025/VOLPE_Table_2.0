"""Independent pre-migration snapshots and shared-model integration checks."""
from dataclasses import replace
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from proforma import pipeline
from proforma.analysis import break_even_report
from proforma.bonuses import BonusPolicy, apply_quantity_limits, calibrate
from proforma.catalog import catalog_programs, reference_catalog
from proforma.config import load_config
from proforma.finance import financial_rates
from proforma.models import Program, Scenario

BASELINE = json.loads((Path(__file__).parent / "fixtures" / "before_reorganization.json").read_text(encoding="utf-8"))


class ProFormaPortTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def assertEquivalent(self, actual, expected):
        if isinstance(expected, dict):
            for key, value in expected.items():
                if key != "solver":
                    self.assertIn(key, actual)
                    self.assertEquivalent(actual[key], value)
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for a, e in zip(actual, expected):
                self.assertEquivalent(a, e)
        elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-6), (actual, expected))
        else:
            self.assertEqual(actual, expected)

    def test_resolved_programs_match_pre_reorganization(self):
        self.assertEquivalent([vars(p) for p in catalog_programs(config=self.config)], BASELINE["programs"])

    def test_prescribed_example_matches_pre_reorganization(self):
        from examples.building_use import build_example
        actual = build_example(self.config)
        for key in ("inputs", "allocation", "totals"):
            self.assertEquivalent(actual[key], BASELINE["example"][key])

    def test_financial_groups_and_reference_catalog_match_pre_reorganization(self):
        self.assertEquivalent(list(financial_rates(self.config).values()), BASELINE["financial_groups"])
        reference = json.loads(reference_catalog(self.config).to_json(orient="records"))
        self.assertEquivalent(reference, BASELINE["reference_catalog"])

    def test_both_policies_and_both_objectives_match_pre_reorganization(self):
        for policy in ("preference", "legacy"):
            for objective in ("annual-surplus", "development-profit"):
                with self.subTest(policy=policy, objective=objective):
                    result = pipeline.optimize(config=self.config, bonus_policy=policy, objective=objective)
                    self.assertEquivalent(result, BASELINE[policy + "/" + objective])

    def test_calibration_and_break_even_match_pre_reorganization(self):
        programs, schedule, _ = calibrate(Scenario.from_config(self.config), self.config.weights,
            catalog_programs(config=self.config), policy=BonusPolicy.from_config(self.config),
            solver_options=self.config.solver_options)
        self.assertEquivalent([vars(p) for p in programs], BASELINE["calibrated_programs"])
        self.assertEquivalent(schedule, BASELINE["schedule"])
        self.assertEquivalent(break_even_report(self.config), BASELINE["break_even"])

    def test_default_optimizer_uses_calibrated_policy(self):
        p = Program("housing", 1, 1, 10, 10, 0, 0, housing=True)
        with patch.object(pipeline.bonuses, "calibrate", return_value=([p], [], {})) as calibration:
            result = pipeline.optimize(config=self.config)
        calibration.assert_called_once()
        self.assertEqual(result["status"], "optimal")
        self.assertEqual(result["allocation"][0]["quantity"], 10)
        self.assertEqual(result["objective"], "annual-surplus")

    def test_legacy_optimizer_bypasses_calibration(self):
        p = Program("housing", 1, 1, 10, 10, 0, 0, housing=True)
        with patch.object(pipeline.bonuses, "calibrate", side_effect=AssertionError("Unexpected calibration")):
            with patch.object(pipeline, "catalog_programs", return_value=[p]):
                result = pipeline.optimize(config=self.config, bonus_policy="legacy")
        self.assertEqual(result["status"], "optimal")

    def test_quantity_and_office_lab_policies_are_preserved(self):
        policy = BonusPolicy.from_config(self.config)
        programs = apply_quantity_limits(catalog_programs(config=self.config), policy=policy)
        self.assertIsNone(policy.maximum_amenity_types)
        for p in programs:
            if p.name in ("general_office", "lab"):
                self.assertTrue(p.unrestricted_nonhousing)
                result = pipeline.optimize([replace(p, noi_per_sqft=1000)],
                    Scenario(base_tower_stories=30), objective="development-profit", config=self.config)
                self.assertAlmostEqual(result["totals"]["indoor_sqft"], 200000)
            elif not p.housing:
                self.assertEqual(p.maximum_sqft, max(p.minimum_sqft, p.unit_sqft))
