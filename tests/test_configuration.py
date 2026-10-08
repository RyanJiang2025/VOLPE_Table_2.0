"""Configuration relationships, isolation between scenarios, and result provenance."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from proforma import bonuses
from proforma.catalog import build_catalog, catalog_programs
from proforma.config import DEFAULT_SCENARIO, PROJECT_ROOT, load_config, thaw
from proforma.finance import financial_rates
from proforma.models import Program, Scenario
from proforma.pipeline import write_run


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def load_changed_dataset(self, directory, name, modify):
        data = thaw(self.config.datasets[name])
        modify(data)
        path = Path(directory) / (name + ".json")
        path.write_text(json.dumps(data), encoding="utf-8")
        scenario = thaw(self.config.data)
        scenario["inputs"] = {key: str((DEFAULT_SCENARIO.parent / value).resolve())
                              for key, value in scenario["inputs"].items()}
        scenario["inputs"][name] = path.name
        scenario_path = Path(directory) / "scenario.json"
        scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
        return load_config(scenario_path)

    def test_inactive_maximum_weight_is_preserved(self):
        active = {p.name for p in catalog_programs(config=self.config)}
        self.assertEqual(len(active), 33)
        self.assertEqual(len(self.config.weights), 37)
        winner = max(self.config.weights, key=self.config.weights.get)
        self.assertEqual(winner, "supermarket")
        self.assertNotIn(winner, active)
        catalog = build_catalog(self.config)
        expected = max(self.config.weights.values())
        park = catalog.set_index("amenity_type").loc["park"]
        self.assertAlmostEqual(park.amenity_pref_order / expected,
                               self.config.weights["park"] / self.config.weights["supermarket"])

    def test_configuration_is_immutable(self):
        with self.assertRaises(TypeError):
            self.config.data["finance"]["required_return"] = .99
        changed = self.config.with_overrides(finance={"required_return": .08})
        self.assertEqual(changed.data["finance"]["required_return"], .08)
        self.assertEqual(self.config.data["finance"]["required_return"], .06)

    def test_invalid_overrides_are_rejected(self):
        cases = [dict(finance={"cap_rate": .04}), dict(finance={"capitalization_rate": 0}),
                 dict(finance={"include_land": "false"}), dict(bonuses={"threshold": 1}),
                 dict(bonuses={"housing_block_units": 0}), dict(solver={"time_limit_seconds": float("nan")}),
                 dict(selection={"floor_limit_exemptions": ["unknown"]}), dict(inputs={"catalog": "other.json"})]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.config.with_overrides(**values)

    def test_duplicate_and_missing_preference_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Duplicate preference"):
                self.load_changed_dataset(directory, "preferences", lambda d: d["weights"].append(d["weights"][0]))
            with self.assertRaisesRegex(ValueError, "cover every active"):
                self.load_changed_dataset(directory, "preferences", lambda d: d["weights"].pop(1))

    def test_unknown_financial_group_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "unknown financial group"):
            self.load_changed_dataset(directory, "catalog", lambda d: d["amenities"][0].update(financial_group="typo"))

    def test_housing_conversion_follows_catalog_unit_size(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = self.load_changed_dataset(directory, "catalog",
                lambda d: d["amenities"][0].update(default_unit_sqft=1990))
            self.assertAlmostEqual(financial_rates(changed)["general_multifamily"]["rent_per_sqft_yearly"], 48000 / 1990)
            self.assertAlmostEqual(financial_rates(self.config)["general_multifamily"]["rent_per_sqft_yearly"], 48000 / 995)

    def test_effective_bounds_follow_explicit_scenario(self):
        scenario = replace(Scenario.from_config(self.config), max_nonhousing_stories=1)
        programs = {p.name: p for p in catalog_programs(config=self.config, scenario=scenario)}
        self.assertLessEqual(programs["cultural_venue"].maximum_sqft, 6000)
        self.assertNotIn("library", programs)  # Its indivisible 8,000-sqft package no longer fits.

    def test_reference_taxonomy_is_not_loaded_for_active_catalog(self):
        original = Path.read_text
        def guarded(path, *args, **kwargs):
            self.assertNotEqual(path.name, "poi_taxonomy.json")
            return original(path, *args, **kwargs)
        with patch.object(Path, "read_text", guarded):
            self.assertEqual(len(catalog_programs(config=self.config)), 33)

    def test_manifest_records_resolved_overrides_and_source_hashes(self):
        config = self.config.with_overrides(finance={"required_return": .08})
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = write_run({"optimization.json": {"status": "optimal"}}, config, command="test",
                                      output_dir=Path(directory) / "run")
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest["resolved_configuration"]["scenario"]["finance"]["required_return"], .08)
            self.assertEqual(len(manifest["source_hashes"]), 5)
            for source, digest in manifest["source_hashes"].items():
                self.assertEqual(digest, hashlib.sha256(Path(source).read_bytes()).hexdigest())
            self.assertEqual(manifest["reports"], {"optimization.json": "optimization.json"})
            self.assertIn("scipy", manifest["dependencies"])
            with self.assertRaises(FileExistsError):
                write_run({"optimization.json": {}}, config, command="test", output_dir=manifest_path.parent)

    def test_cli_resolves_default_inputs_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            environment = os.environ.copy()
            environment["PYTHONPATH"] = os.pathsep.join([str(PROJECT_ROOT / "src"), *sys.path])
            command = [sys.executable, "-B", "-m", "proforma", "--bonus-policy", "legacy", "--output", str(output)]
            process = subprocess.run(command, cwd=directory, env=environment, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads(output.read_text())
            self.assertEqual(result["objective"], "development-profit")
            self.assertEqual(result["bonus_policy"], "legacy")
            self.assertTrue(output.with_name("result.manifest.json").is_file())


class CalibrationCacheTests(unittest.TestCase):
    def test_threshold_reuse_matches_uncached_and_invalidates_on_economics_change(self):
        config = load_config()
        scenario = Scenario.from_config(config)
        all_programs = catalog_programs(config=config)
        programs = [p for p in all_programs if p.name in ("luxury_multifamily", "park")]
        policy = bonuses.BonusPolicy.from_config(config)
        cache = {}
        kwargs = dict(policy=policy, solver_options=config.solver_options)
        bonuses.calibrate(scenario, config.weights, programs, threshold_cache=cache, **kwargs)
        weights = config.weights
        weights["park"] *= .5
        with patch.object(bonuses, "optimize", wraps=bonuses.optimize) as solver:
            cached, rows, _ = bonuses.calibrate(scenario, weights, programs, threshold_cache=cache, **kwargs)
            self.assertEqual(solver.call_count, 1)  # Only the baseline must be re-solved.
        uncached, expected, _ = bonuses.calibrate(scenario, weights, programs, **kwargs)
        self.assertEqual(cached, uncached)
        self.assertEqual(rows, expected)
        changed = [replace(p, noi_per_sqft=p.noi_per_sqft + 1) if p.name == "luxury_multifamily" else p for p in programs]
        with patch.object(bonuses, "optimize", wraps=bonuses.optimize) as solver:
            bonuses.calibrate(scenario, weights, changed, threshold_cache=cache, **kwargs)
            self.assertGreater(solver.call_count, 1)

    def test_housing_block_size_is_an_explicit_solver_input(self):
        from proforma.optimizer import optimize
        program = Program("housing", 1, 1, 6, 10, 0, 0, housing=True,
                          bonus_blocks=(1, 1), bonus_eligible=True, bonus_block_units=3)
        scenario = Scenario(podium_footprint=1, podium_stories=0, tower_footprint=1,
                            base_tower_stories=4, max_tower_stories=6)
        result = optimize([program], scenario, objective="development-profit")
        self.assertEqual(result["allocation"][0]["quantity"], 6)
        self.assertEqual(result["totals"]["bonus_far"], 2)
