import unittest
from dataclasses import replace
from proforma.models import Program, Scenario
from proforma.optimizer import optimize
from proforma.bonuses import bonus_factor, apply_quantity_limits


class PreferenceBonusTests(unittest.TestCase):
    def test_one_facility_across_zones_with_housing_office_lab_exempt(self):
        facility = Program("pharmacy", 10, 10, 40, 10, 0, 0)
        housing = replace(facility, name="housing", housing=True)
        office = replace(facility, name="general_office", continuous=True)
        lab = replace(office, name="lab")
        capped = apply_quantity_limits([facility, housing, office, lab])
        s = Scenario(podium_stories=1)
        result = optimize(capped, s)
        quantities = {p["amenity_type"]: p["quantity"] for p in result["allocation"]}
        self.assertEqual(quantities["pharmacy"], 1)
        for name in ("housing", "general_office", "lab"):
            self.assertEqual(quantities[name], 4)

    def test_no_default_type_limit(self):
        from proforma.bonuses import BonusPolicy
        policy = BonusPolicy.from_config()
        self.assertIsNone(policy.maximum_amenity_types)
        ps = [Program(str(i), 1, 1, 1, 10, 0, 0, bonus_eligible=True) for i in range(8)]
        result = optimize(ps, Scenario(), max_amenity_types=policy.maximum_amenity_types)
        self.assertEqual(len(result["allocation"]), 8)

    def test_preference_gate_and_declining_premium(self):
        self.assertAlmostEqual(bonus_factor(.3), .25)
        self.assertAlmostEqual(bonus_factor(.6), 1)
        self.assertAlmostEqual(bonus_factor(1), 1.15)
        self.assertAlmostEqual(bonus_factor(1, .25), 1.0375)

    def test_complete_blocks_and_subsidy_ceiling(self):
        p = Program("housing", 1, 1, 30, 10, 0, 0, housing=True,
                    bonus_blocks=(1, 1, 1, 1), bonus_eligible=True)
        s = Scenario(podium_footprint=1, podium_stories=0, tower_footprint=1,
                     base_tower_stories=26, max_tower_stories=30)
        result = optimize([p], s, objective="development-profit")
        self.assertEqual(result["allocation"][0]["quantity"], 30)
        self.assertEqual(result["totals"]["bonus_far"], 4)
        result = optimize([replace(p, maximum_sqft=4)], s, objective="development-profit")
        self.assertEqual(result["totals"]["bonus_far"], 0)

    def test_type_cap_and_required_quantities(self):
        p = Program("a", 1, 1, 1, 10, 0, 0, housing=True, bonus_eligible=True)
        q = replace(p, name="b")
        s = Scenario(podium_stories=1)
        result = optimize([p, q], s, max_amenity_types=1)
        self.assertEqual(len(result["allocation"]), 1)
        result = optimize([p, q], s, max_amenity_types=1, required_quantities={"a": 1, "b": 1})
        self.assertEqual(result["status"], "infeasible")
