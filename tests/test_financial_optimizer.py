"""Small financial problems with independently checkable answers."""
from dataclasses import replace
import unittest

from proforma.models import Program, Scenario
from proforma.catalog import catalog_programs
from proforma.optimizer import optimize


def program(name="housing", **kwargs):
    fields = dict(name=name, unit_sqft=1, minimum_sqft=5, maximum_sqft=100,
                  noi_per_sqft=10, podium_cost_per_sqft=0, tower_cost_per_sqft=0,
                  housing=True)
    fields.update(kwargs)
    return Program(**fields)


class FinancialOptimizerTests(unittest.TestCase):
    def test_valuation_can_build_tower_rejected_by_annual_objective(self):
        scenario = Scenario(required_return=0.06, capitalization_rate=0.045,
                            podium_stories=0, tower_footprint=1250,
                            base_tower_stories=5, max_tower_stories=30)
        housing = program(unit_sqft=1250, minimum_sqft=6250, maximum_sqft=500000,
                          noi_per_sqft=54.6, tower_cost_per_sqft=1092)
        annual = optimize([housing], scenario, objective="annual-surplus")
        valuation = optimize([housing], scenario, objective="development-profit")
        self.assertEqual(annual["decision"], "no_development")
        self.assertEqual(valuation["totals"]["tower_sqft"], 6250)
        self.assertAlmostEqual(valuation["totals"]["development_profit"], 6250*(54.6/.045-1092))
        self.assertLess(valuation["totals"]["annual_surplus"], 0)

    def test_valuation_accounts_for_amenity_maintenance_and_land(self):
        scenario = Scenario(capitalization_rate=.05, podium_footprint=10,
                            podium_stories=1, tower_footprint=10,
                            base_tower_stories=0, max_tower_stories=1, land_cost=10)
        amenity = program("amenity", minimum_sqft=1, maximum_sqft=1,
                          noi_per_sqft=-1, podium_cost_per_sqft=2,
                          ground_level=True, housing=False, bonus_far_per_unit=1)
        housing = program("housing", minimum_sqft=1, maximum_sqft=10,
                          noi_per_sqft=10, podium_cost_per_sqft=300,
                          tower_cost_per_sqft=100)
        result = optimize([amenity, housing], scenario, objective="development-profit")
        self.assertEqual({p["amenity_type"] for p in result["allocation"]}, {"amenity", "housing"})
        self.assertAlmostEqual(result["totals"]["completed_value"], 1980)
        self.assertAlmostEqual(result["totals"]["development_profit"], 968)
        self.assertAlmostEqual(result["totals"]["objective_value"], 968)

    def test_valuation_rate_override_and_invalid_rates(self):
        scenario = Scenario(podium_stories=0, tower_footprint=10, base_tower_stories=1,
                            max_tower_stories=1, capitalization_rate=.1)
        housing = program(capitalization_rate=.05, tower_cost_per_sqft=150)
        result = optimize([housing], scenario, objective="development-profit")
        self.assertAlmostEqual(result["totals"]["development_profit"], 500)
        for rate in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                optimize([housing], replace(scenario, capitalization_rate=rate))
        with self.assertRaises(ValueError):
            optimize([replace(housing, capitalization_rate=0)], scenario)
        with self.assertRaises(ValueError):
            optimize([housing], scenario, objective="unknown")

    def setUp(self):
        self.scenario = Scenario(required_return=0.1, podium_footprint=10,
                                 podium_stories=0, tower_footprint=10,
                                 base_tower_stories=1, max_tower_stories=1,
                                 open_space=0)

    def test_matches_brute_force_integer_financial_optimum(self):
        programs = [program("A", unit_sqft=3, minimum_sqft=6, maximum_sqft=30,
                            noi_per_sqft=5, tower_cost_per_sqft=2),
                    program("B", unit_sqft=2, minimum_sqft=4, maximum_sqft=10,
                            noi_per_sqft=6, tower_cost_per_sqft=10)]
        candidates = [(3*a*(5-0.1*2) + 2*b*(6-0.1*10), a, b)
                      for a in [0] + list(range(2, 11))
                      for b in [0] + list(range(2, 6)) if 3*a+2*b <= 10]
        best, _, _ = max(candidates)
        result = optimize(programs, self.scenario)
        self.assertEqual(result["status"], "optimal")
        self.assertAlmostEqual(result["totals"]["annual_surplus"], best)

    def test_amenity_is_selected_only_when_enabled_income_pays_for_it(self):
        scenario = replace(self.scenario, base_tower_stories=0)
        amenity = program("amenity", minimum_sqft=1, maximum_sqft=1,
                          noi_per_sqft=-1, bonus_far_per_unit=1, housing=False)
        filler = program("filler", minimum_sqft=1, maximum_sqft=9,
                         noi_per_sqft=10, continuous=True, housing=False)
        result = optimize([amenity, filler], scenario)
        self.assertEqual({p["amenity_type"] for p in result["allocation"]}, {"amenity", "filler"})
        self.assertAlmostEqual(result["totals"]["annual_surplus"], 89)
        self.assertAlmostEqual(result["totals"]["tower_sqft"], 10)

    def test_no_development_when_capital_charge_exceeds_noi(self):
        result = optimize([program(noi_per_sqft=1, tower_cost_per_sqft=20)], self.scenario)
        self.assertEqual(result["decision"], "no_development")
        self.assertEqual(result["totals"]["annual_surplus"], 0)

    def test_land_is_charged_once_and_can_prevent_development(self):
        scenario = replace(self.scenario, land_cost=100)
        result = optimize([program()], scenario)
        self.assertEqual(result["totals"]["land_cost"], 100)
        self.assertAlmostEqual(result["totals"]["annual_surplus"], 90)
        result = optimize([program()], replace(scenario, land_cost=2000))
        self.assertEqual(result["decision"], "no_development")
        self.assertEqual(result["totals"]["land_cost"], 0)

    def test_whole_apartments_in_each_zone_and_five_unit_minimum(self):
        scenario = replace(self.scenario, podium_stories=1, tower_footprint=7,
                           podium_footprint=7)
        result = optimize([program(unit_sqft=3, minimum_sqft=15, maximum_sqft=30)], scenario)
        self.assertEqual(result["decision"], "no_development")  # Only four whole apartments fit.
        scenario = replace(scenario, podium_footprint=9)
        result = optimize([program(unit_sqft=3, minimum_sqft=15, maximum_sqft=30)], scenario)
        allocation = result["allocation"][0]
        self.assertEqual(allocation["quantity"], 5)
        self.assertEqual(allocation["podium_quantity"], 3)
        self.assertEqual(allocation["tower_quantity"], 2)

    def test_bonus_cannot_bypass_height_cap(self):
        result = optimize([program(bonus_far_per_unit=100)], self.scenario)
        self.assertEqual(result["totals"]["tower_sqft"], 10)
        self.assertGreater(result["totals"]["bonus_capacity_blocked_by_height_cap_sqft"], 0)

    def test_required_program_and_budget_can_be_infeasible(self):
        p = program(tower_cost_per_sqft=20)
        result = optimize([p], replace(self.scenario, development_budget=50),
                          required_quantities={"housing": 5})
        self.assertEqual(result["status"], "infeasible")
        self.assertIsNone(result["totals"])

    def test_ground_floor_and_outdoor_shared_limits(self):
        scenario = replace(self.scenario, podium_stories=5, open_space=2)
        programs = [program("shop", minimum_sqft=1, maximum_sqft=100,
                            ground_level=True, continuous=True, housing=False),
                    program("park", minimum_sqft=2, maximum_sqft=2, outdoor=True),
                    program("playground", minimum_sqft=2, maximum_sqft=2, outdoor=True,
                            noi_per_sqft=5)]
        result = optimize(programs, scenario)
        self.assertEqual(result["totals"]["podium_sqft"], 10)
        self.assertEqual(result["totals"]["outdoor_sqft"], 2)
        self.assertEqual({p["amenity_type"] for p in result["allocation"]}, {"shop", "park"})

    def test_high_bonus_does_not_make_a_loss_making_amenity_desirable(self):
        amenity = program("amenity", minimum_sqft=1, maximum_sqft=1,
                          noi_per_sqft=-100, bonus_far_per_unit=1000, housing=False)
        result = optimize([amenity, program()], self.scenario)
        self.assertEqual([p["amenity_type"] for p in result["allocation"]], ["housing"])

    def test_facility_cannot_be_split_fractionally_across_zones(self):
        scenario = replace(self.scenario, podium_footprint=4, podium_stories=1,
                           tower_footprint=4)
        p = program("facility", unit_sqft=6, minimum_sqft=6, maximum_sqft=6,
                    housing=False)
        result = optimize([p], scenario)
        self.assertEqual(result["decision"], "no_development")

    def test_more_expensive_tower_placement_is_not_forced(self):
        scenario = replace(self.scenario, podium_stories=1)
        p = program(podium_cost_per_sqft=1, tower_cost_per_sqft=200)
        result = optimize([p], scenario)
        self.assertEqual(result["totals"]["podium_sqft"], 10)
        self.assertEqual(result["totals"]["tower_sqft"], 0)

    def test_budget_includes_land_once(self):
        scenario = replace(self.scenario, land_cost=100, development_budget=150)
        result = optimize([program(tower_cost_per_sqft=10)], scenario)
        self.assertEqual(result["allocation"][0]["quantity"], 5)
        self.assertEqual(result["totals"]["development_cost"], 150)
        self.assertAlmostEqual(result["totals"]["annual_surplus"], 35)

    def test_two_story_limit_aggregates_repeated_facilities(self):
        scenario = replace(self.scenario, podium_stories=5, max_tower_stories=30,
                           base_tower_stories=30)
        p = program("facility", unit_sqft=10, minimum_sqft=10, maximum_sqft=100,
                    housing=False)
        result = optimize([p], scenario)
        self.assertEqual(result["allocation"][0]["quantity"], 2)

    def test_catalog_refunds_follow_overridden_tower_footprint(self):
        original = {p.name: p for p in catalog_programs(6000)}
        changed = {p.name: p for p in catalog_programs(8000)}
        p = original["general_multifamily"]
        self.assertAlmostEqual(p.bonus_far_per_unit - changed[p.name].bonus_far_per_unit,
                               p.unit_sqft / 6000 - p.unit_sqft / 8000)
        self.assertEqual(changed["luxury_multifamily"].bonus_far_per_unit, 0)


if __name__ == "__main__":
    unittest.main()
