"""Maximize earned bonus FAR with whole programs and shared parcel limits.

Requires scipy. Run from the repository root:
python -m dummy_data.stress_test --output dummy_data/stress_test_results.json
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


def run_stress_tests():
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from . import assumptions as a
    from .amenity_list import (
        buildable_use_catalog, far_bonus_for_use, FOR_PROFIT_USES, OUTDOOR_USES,
    )

    # Zero-bonus filler cannot improve this objective and consumes scarce area.
    rows = list(buildable_use_catalog.loc[
        ~buildable_use_catalog.amenity_type.isin(FOR_PROFIT_USES)
    ].itertuples())
    n = len(rows)
    snapshot = dict(json.loads(Path(__file__).with_name(
        "amenity_pref_order_votes.json").read_text(encoding="utf-8")))
    reports = []
    for equal_weights in (False, True):
        reference = 1.0 if equal_weights else max(snapshot.values())
        bonus_per_unit = np.array([
            far_bonus_for_use(
                reference if equal_weights else snapshot[r.amenity_type],
                (r.rent_per_sqft_yearly - r.upkeep_per_sqft_yearly) * r.default_unit_sqft,
                reference, r.default_unit_sqft,
                indoor=r.amenity_type not in OUTDOOR_USES,
                amenity_type=r.amenity_type,
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
                    stories[i] = unit / a.PODIUM_FOOTPRINT_SQFT
                    stories[n + i] = 1 / a.TOWER_FOOTPRINT_SQFT - 1 / a.PODIUM_FOOTPRINT_SQFT
                    constrain(stories, a.MAX_NONHOUSING_STORIES_PER_USE)
            constrain(podium, a.PODIUM_FOOTPRINT_SQFT * a.PODIUM_STORIES)
            constrain(outdoor, a.OPEN_SPACE_AREA_SQFT)
            constrain(ground, a.PODIUM_FOOTPRINT_SQFT)
            authorization = tower.copy()
            authorization[:n] -= bonus_per_unit * a.BONUS_FAR_AREA_SQFT
            constrain(authorization, a.TOWER_FOOTPRINT_SQFT * a.BASE_TOWER_STORIES)
            if capped:
                constrain(tower, a.MAX_TOWER_CAPACITY_SQFT)

            matrix = np.array(constraints)
            objective = np.zeros(2 * n)
            objective[:n] = -bonus_per_unit
            started = perf_counter()
            result = milp(objective, integrality=integrality,
                          bounds=Bounds(low, high),
                          constraints=LinearConstraint(matrix, lower, upper),
                          options={"mip_rel_gap": 0.0, "time_limit": 60})
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
                "tower_floor_equivalents": tower_area / a.TOWER_FOOTPRINT_SQFT,
                "uncapped_authorized_tower_sqft": a.TOWER_FOOTPRINT_SQFT * a.BASE_TOWER_STORIES + bonus * a.BONUS_FAR_AREA_SQFT,
                "effective_authorized_tower_sqft": a.tower_capacity_for_bonus(bonus) if capped else a.TOWER_FOOTPRINT_SQFT * a.BASE_TOWER_STORIES + bonus * a.BONUS_FAR_AREA_SQFT,
                "allocation": allocation,
            })
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver-path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.solver_path:
        sys.path.insert(0, str(args.solver_path))
    reports = run_stress_tests()
    if args.output:
        args.output.write_text(json.dumps(reports, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps([{k: v for k, v in report.items() if k != "allocation"}
                      for report in reports], indent=2))
