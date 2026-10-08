"""Physical tower limits must hold even when amenities grant excess FAR."""
import unittest
from examples import building_use
from proforma.models import Scenario


class TowerCapacityTests(unittest.TestCase):
    def test_shared_model_limits_bonus_capacity(self):
        scenario = Scenario.from_config()
        for bonus, expected in ((0, 30000), (10, 90000), (25, 180000), (1000, 180000)):
            with self.subTest(bonus=bonus):
                self.assertEqual(scenario.tower_capacity_for_bonus(bonus), expected)

    def test_invalid_bonus_is_rejected(self):
        for bonus in (-1, float("nan"), float("inf")):
            with self.subTest(bonus=bonus):
                with self.assertRaises(ValueError):
                    Scenario.from_config().tower_capacity_for_bonus(bonus)

    def test_oversized_housing_is_rejected_despite_its_bonuses(self):
        # Each 100-apartment program is within its use bound, but their combined
        # tower area exceeds 180,000 sqft. A floor-area refund cannot bypass it.
        with self.assertRaisesRegex(ValueError, "tower amenities exceed"):
            building_use.build_example(housing_units=100)

    def test_compact_example_retains_separate_podium_capacity(self):
        result = building_use.build_example()
        self.assertEqual(result["inputs"]["max_tower_stories"], 30)
        self.assertEqual(result["inputs"]["max_tower_capacity_sqft"], 180000)
        self.assertEqual(result["inputs"]["podium_capacity_sqft"], 20000)
        self.assertLessEqual(result["totals"]["tower_floor_equivalents"], 30)
        self.assertLessEqual(result["totals"]["tower_sqft"], result["totals"]["tower_capacity_sqft"])


if __name__ == "__main__":
    unittest.main()
