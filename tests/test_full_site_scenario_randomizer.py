"""Financial dominance and genuine zero-tower regression checks."""
from dataclasses import replace
import unittest

from full_site_scenario_randomizer import (
    PAIRS, USES, financial_bounds, pair_config, scenario_config, site_layout,
)
from proforma.bonuses import calibrate
from proforma.catalog import catalog_programs
from proforma.config import load_config
from proforma.models import Scenario
from proforma.optimizer import optimize


class FullSiteTests(unittest.TestCase):
    def test_cost_reduction_can_hold_rents_fixed(self):
        current = load_config()
        self.assertEqual(current.data['finance']['tower_cost_multiplier'], 1.5)
        old = current.with_overrides(finance={'tower_cost_multiplier': 1.75})
        previous = financial_bounds(old)
        updated = financial_bounds(current, reference_bounds=previous)
        for name in USES:
            for level in ('lower', 'higher'):
                self.assertEqual(updated[name][level]['annual_rent_per_sqft'],
                                 previous[name][level]['annual_rent_per_sqft'])
                self.assertGreater(updated[name][level]['development_profit_per_sqft']['tower'],
                                   previous[name][level]['development_profit_per_sqft']['tower'])
            self.assertAlmostEqual(updated[name]['construction_cost_per_sqft']['tower'],
                                   previous[name]['construction_cost_per_sqft']['tower'] * 1.5 / 1.75)

    def test_five_story_base_spans_both_footprints_and_upper_tower_is_bonus_only(self):
        config = scenario_config(load_config(), 'test', 22, True)
        s = Scenario.from_config(config)
        self.assertEqual(s.podium_footprint, 5625)
        self.assertEqual(s.tower_footprint, 5625)
        self.assertEqual(s.podium_base_footprint, 11250)
        self.assertEqual(s.podium_capacity, 56250)
        self.assertEqual(s.base_tower_stories, 0)
        self.assertEqual(s.max_tower_stories, 25)
        self.assertEqual(s.tower_capacity_for_bonus(0), 0)
        self.assertEqual(s.tower_capacity_for_bonus(100), 140625)
        office = next(p for p in catalog_programs(config=config, scenario=s) if p.name == 'general_office')
        office = replace(office, noi_per_sqft=1000)
        base = optimize([office], s, objective='development-profit')
        self.assertEqual(base['totals']['podium_sqft'], 56250)
        self.assertEqual(base['totals']['tower_sqft'], 0)
        # Authorize the upper 25 stories to verify both area and zone pricing.
        full = optimize([office], replace(s, base_tower_stories=25), objective='development-profit')
        self.assertEqual(full['totals']['podium_sqft'], 56250)
        self.assertEqual(full['totals']['tower_sqft'], 140625)
        self.assertEqual(full['totals']['podium_floor_equivalents'], 5)
        self.assertAlmostEqual(full['totals']['construction_cost'],
                               56250 * office.podium_cost_per_sqft + 140625 * office.tower_cost_per_sqft)

    def test_rounding_conserves_land_for_every_layout(self):
        expected = {20: (2500, 5000, 5000), 22: (2500, 5625, 5625), 24: (3125, 5625, 6250)}
        for _, blocks in PAIRS:
            for tower in (False, True):
                s = site_layout(blocks, tower)
                self.assertEqual(s['open_space_sqft'] + s['podium_sqft'] + s['tower_sqft'], blocks * 625)
                self.assertTrue(all(v % 625 == 0 for v in s.values()))
                if tower:
                    self.assertEqual(tuple(s[k] for k in ('open_space_sqft', 'podium_sqft', 'tower_sqft')), expected[blocks])
                else:
                    self.assertEqual(s['tower_sqft'], 0)

    def test_each_high_use_wins_and_low_uses_do_not_infill(self):
        base = load_config()
        saved = base.resolved()
        bounds = financial_bounds(base)
        for winner in USES:
            paired = pair_config(base, base.weights, winner, bounds)
            for tower in (False, True):
                config = scenario_config(paired, 'test', 22, tower)
                s = Scenario.from_config(config)
                programs = [p for p in catalog_programs(config=config, scenario=s) if p.name in USES]
                for zone in ('podium', 'tower'):
                    profits = {p.name: p.noi_per_sqft / s.capitalization_rate
                               - getattr(p, zone + '_cost_per_sqft') for p in programs}
                    self.assertGreater(profits[winner], 0)
                    for name in set(USES) - {winner}:
                        self.assertLess(profits[name], 0)
                result = optimize(programs, s, objective='development-profit')
                self.assertEqual(result['status'], 'optimal')
                self.assertEqual({a['amenity_type'] for a in result['allocation']}, {winner})
                if not tower:
                    self.assertEqual(result['totals']['tower_sqft'], 0)
                    self.assertEqual(result['totals']['tower_floor_equivalents'], 0)
                # Both forms inherit the same randomized preferences and economics.
                self.assertEqual(config.weights, paired.weights)
                self.assertEqual(config.datasets['economics'], paired.datasets['economics'])
        self.assertEqual(base.resolved(), saved)

    def test_zero_tower_keeps_podium_amenities_but_cannot_award_capacity(self):
        base = load_config()
        config = scenario_config(base, 'test', 22, False)
        s = Scenario.from_config(config)
        programs = catalog_programs(config=config, scenario=s)
        office = next(p for p in programs if p.name == 'general_office')
        library = next(p for p in programs if p.name == 'library')
        office = replace(office, noi_per_sqft=1000)
        calibrated, rows, _ = calibrate(s, base.weights, [office, library], use_all_fillers=True)
        result = optimize(calibrated, s, objective='development-profit', required_quantities={'library': 1})
        self.assertEqual(result['status'], 'optimal')
        self.assertEqual(result['totals']['tower_sqft'], 0)
        self.assertEqual(result['totals']['bonus_far'], 0)
        self.assertTrue(all(r['incremental_bonus_far'] == 0 for r in rows))
        with self.assertRaisesRegex(ValueError, 'zero-footprint'):
            optimize([office], replace(s, max_tower_stories=1))
        with self.assertRaisesRegex(ValueError, 'zero-footprint'):
            config.with_overrides(site={'tower': {'footprint_sqft': 0, 'base_stories': 0, 'maximum_stories': 1}})
