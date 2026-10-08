"""Maximize earned bonus FAR with whole programs and shared parcel limits.

Requires scipy. Run from the repository root:
python -m experiments.stress_test
An optional --solver-path can point to an isolated scipy installation.
This is a bonus stress test, not a financial optimizer.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from time import perf_counter


def run_stress_tests(config=None):
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from proforma.bonuses import far_bonus_for_use
    from proforma.catalog import build_catalog
    from proforma.config import load_config
    from proforma.models import Scenario
    config = config or load_config()
    scenario = Scenario.from_config(config)
    buildable_use_catalog = build_catalog(config, scenario)
    FOR_PROFIT_USES = set(buildable_use_catalog.loc[buildable_use_catalog.is_for_profit_use, "amenity_type"])
    OUTDOOR_USES = set(buildable_use_catalog.loc[buildable_use_catalog.outdoor, "amenity_type"])

    # Zero-bonus filler cannot improve this objective and consumes scarce area.
    rows = list(buildable_use_catalog.loc[
        ~buildable_use_catalog.amenity_type.isin(FOR_PROFIT_USES)
    ].itertuples())
    n = len(rows)
    snapshot = config.weights
    reports = []
    for equal_weights in (False, True):
        reference = 1.0 if equal_weights else max(snapshot.values())
        bonus_per_unit = np.array([
            far_bonus_for_use(
                reference if equal_weights else snapshot[r.amenity_type],
                (r.rent_per_sqft_yearly - r.upkeep_per_sqft_yearly) * r.default_unit_sqft,
                reference, r.default_unit_sqft,
                indoor=r.amenity_type not in OUTDOOR_USES,
                eligible=r.amenity_type not in FOR_PROFIT_USES,
                bonus_far_area_sqft=scenario.tower_footprint, legacy=config.data["bonuses"]["legacy"],
            ) for r in rows
        ])
        for capped in (False, True):
            # First n variables are whole units/facilities, or zero if absent.
            # Last n variables allocate each program's area to the tower;
            # remaining indoor area is allocated to the separate podium.
            low = np.zeros(2 * n)
            high = np.full(2 * n, np.inf)
            integrality = np.zeros(2 * n, dtype=int)
            constraints, lower, upper = [], [], []

            def constrain(coefficients, maximum, minimum=-np.inf):
                constraints.append(coefficients)
                lower.append(minimum)
                upper.append(maximum)

            podium, outdoor, ground, tower = (np.zeros(2 * n) for _ in range(4))
            for i, r in enumerate(rows):
                unit = r.default_unit_sqft
                low[i] = math.ceil(r.minimum_program_sqft / unit)
                high[i] = math.floor(r.maximum_program_sqft / unit)
                integrality[i] = 3  # Semi-integer: zero or within selected bounds.
                if r.amenity_type in OUTDOOR_USES:
                    high[n + i] = 0
                    outdoor[i] = unit
                    continue
                podium[i], podium[n + i] = unit, -1
                tower[n + i] = 1
                allocation = np.zeros(2 * n)
                allocation[i], allocation[n + i] = -unit, 1
                constrain(allocation, 0)
                if r.ground_level:
                    high[n + i] = 0
                    ground[i] = unit
                elif not r.tower_allowed:
                    high[n + i] = 0
                if r.program_unit != "dwelling_unit":
                    # Respect two floor equivalents even on the narrower podium.
                    stories = np.zeros(2 * n)
                    stories[i] = unit / scenario.podium_footprint
                    stories[n + i] = 1 / scenario.tower_footprint - 1 / scenario.podium_footprint
                    constrain(stories, scenario.max_nonhousing_stories)
            constrain(podium, scenario.podium_footprint * scenario.podium_stories)
            constrain(outdoor, scenario.open_space)
            constrain(ground, scenario.podium_footprint)
            authorization = tower.copy()
            authorization[:n] -= bonus_per_unit * scenario.tower_footprint
            constrain(authorization, scenario.tower_footprint * scenario.base_tower_stories)
            if capped:
                constrain(tower, scenario.maximum_tower_capacity)

            matrix = np.array(constraints)
            objective = np.zeros(2 * n)
            objective[:n] = -bonus_per_unit
            started = perf_counter()
            result = milp(objective, integrality=integrality,
                          bounds=Bounds(low, high),
                          constraints=LinearConstraint(matrix, lower, upper),
                          options={"mip_rel_gap": config.data["solver"]["relative_gap"], "time_limit": config.data["solver"]["time_limit_seconds"]})
            elapsed = perf_counter() - started
            if not result.success:
                raise RuntimeError(result.message)
            # Independently verify feasibility rather than trusting status alone.
            x = result.x
            assert np.all(matrix @ x <= np.array(upper) + 1e-5)
            for i in range(n):
                assert abs(x[i] - round(x[i])) < 1e-5
                assert x[i] < 1e-5 or low[i] - 1e-5 <= x[i] <= high[i] + 1e-5
            bonus = float(bonus_per_unit @ x[:n])
            tower_area, podium_area = float(tower @ x), float(podium @ x)
            allocation = []
            for i, r in enumerate(rows):
                quantity = int(round(x[i]))
                if not quantity:
                    continue
                area = quantity * r.default_unit_sqft
                allocation.append({
                    "amenity_type": r.amenity_type, "quantity": quantity,
                    "area_sqft": area, "tower_sqft": float(x[n + i]),
                    "podium_sqft": 0.0 if r.amenity_type in OUTDOOR_USES else float(area - x[n + i]),
                    "bonus_far": float(quantity * bonus_per_unit[i]),
                })
            reports.append({
                "vote_scenario": "equal maximum ratios" if equal_weights else "current snapshot",
                "tower_cap_enforced": capped, "optimal": bool(result.success),
                "solve_seconds": elapsed, "solver_nodes": int(result.mip_node_count),
                "optimality_gap": float(result.mip_gap), "bonus_far": bonus,
                "tower_sqft": tower_area, "podium_sqft": podium_area,
                "indoor_sqft": tower_area + podium_area,
                "outdoor_sqft": float(outdoor @ x),
                "tower_floor_equivalents": tower_area / scenario.tower_footprint,
                "uncapped_authorized_tower_sqft": scenario.tower_footprint * scenario.base_tower_stories + bonus * scenario.tower_footprint,
                "effective_authorized_tower_sqft": scenario.tower_capacity_for_bonus(bonus) if capped else scenario.tower_footprint * scenario.base_tower_stories + bonus * scenario.tower_footprint,
                "allocation": allocation,
            })
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--solver-path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.solver_path:
        sys.path.insert(0, str(args.solver_path))
    from proforma.config import load_config
    from proforma.pipeline import write_run
    config = load_config(args.scenario).with_overrides(bonuses={"policy": "legacy"})
    reports = run_stress_tests(config)
    write_run({"stress_test.json": reports}, config, command="bonus-stress-test", output=args.output,
              metadata={"bonus_policy": "legacy", "objective": "maximum_bonus_far"})
    print(json.dumps([{k: v for k, v in report.items() if k != "allocation"}
                      for report in reports], indent=2))
