import math
import random
import unittest
from experiments.preference_monte_carlo import random_weights, profit_override
from proforma.models import Program, Scenario
from proforma.catalog import catalog_programs
from proforma.optimizer import optimize
from proforma.bonuses import calibrate


class RandomWeightTests(unittest.TestCase):
    def test_office_and_lab_can_fill_entire_building_above_old_limits(self):
        s = Scenario(podium_footprint=4000, podium_stories=5, tower_footprint=6000,
                     base_tower_stories=30, max_tower_stories=30)
        from dataclasses import replace
        for name in ('general_office', 'lab'):
            p = next(p for p in catalog_programs() if p.name == name)
            self.assertTrue(p.unrestricted_nonhousing)
            # Override the physical envelope beyond the default catalog bounds.
            larger = replace(s, max_tower_stories=40, base_tower_stories=40)
            p = replace(p, noi_per_sqft=1000)
            result = optimize([p], larger, objective='development-profit')
            self.assertEqual(result['status'], 'optimal')
            self.assertAlmostEqual(result['totals']['indoor_sqft'], 260000)

    def test_profit_override_beats_luxury_in_both_zones(self):
        luxury = Program('luxury_multifamily', 1, 1, 100, 54.6, 624, 1092, housing=True)
        office = Program('general_office', 1, 1, 100, 61.93, 943, 1650, continuous=True)
        ps, metadata = profit_override([luxury, office], Scenario(), 'general_office')
        self.assertEqual(ps[0], luxury)
        self.assertEqual(ps[1].tower_cost_per_sqft, office.tower_cost_per_sqft)
        for numbers in metadata['comparisons'].values():
            self.assertGreaterEqual(numbers['winner_profit_per_sqft']+1e-9,
                                    1.1*numbers['luxury_profit_per_sqft'])

    def test_recalibration_baseline_includes_more_profitable_filler(self):
        luxury = Program('luxury_multifamily', 1, 1, 10, 1, 0, 0, housing=True)
        office = Program('general_office', 1, 1, 10, 2, 0, 0, continuous=True)
        s = Scenario(podium_footprint=10, podium_stories=1, base_tower_stories=0)
        _, _, baseline = calibrate(s, weights={'luxury_multifamily': .5, 'general_office': .5},
                                   programs=[luxury, office], use_all_fillers=True)
        self.assertEqual(baseline['allocation'][0]['amenity_type'], 'general_office')
        self.assertAlmostEqual(baseline['totals']['annual_noi'], 20)

    def test_preserves_total_and_identifiers_without_modifying_source(self):
        original = {"a": .2, "b": .3, "c": .5}
        rng = random.Random(7)
        for _ in range(10):
            result = random_weights(original, rng)
            self.assertEqual(set(result), set(original))
            self.assertTrue(all(v > 0 for v in result.values()))
            self.assertAlmostEqual(math.fsum(result.values()), 1, places=14)
        self.assertEqual(original, {"a": .2, "b": .3, "c": .5})

    def test_reproducible_but_successive_trials_differ(self):
        original = {"a": 2, "b": 3, "c": 5}
        rng = random.Random(7)
        first = random_weights(original, rng)
        self.assertEqual(first, random_weights(original, random.Random(7)))
        self.assertNotEqual(first, random_weights(original, rng))
