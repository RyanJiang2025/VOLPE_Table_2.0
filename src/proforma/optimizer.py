"""MILP solver with explicit programs and scenario; no configuration I/O or policy selection."""
import math
from time import perf_counter
from .finance import OBJECTIVES, completed_value, objective_contribution


def optimize(programs, scenario, required_quantities=None, time_limit=60.0,
             objective="annual-surplus", max_amenity_types=None, relative_gap=0.0):
    """Jointly choose programs and whole-unit placements; zero development is allowed.

    required_quantities maps program names to minimum unit quantities. A facility
    must be entirely in one zone; multiple whole facilities can occupy both zones.
    Square-foot programs can be divided continuously between zones.
    """
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp

    programs = list(programs)
    required_quantities = dict(required_quantities or {})
    if objective not in OBJECTIVES:
        raise ValueError(f"Unknown objective: {objective}")
    if not math.isfinite(scenario.capitalization_rate) or scenario.capitalization_rate <= 0:
        raise ValueError("capitalization_rate must be finite and positive")
    names = [p.name for p in programs]
    if not programs or len(set(names)) != len(names):
        raise ValueError("Programs must be nonempty and have unique names")
    if set(required_quantities) - set(names):
        raise ValueError("Required quantities contain an unknown program")
    if not math.isfinite(time_limit) or time_limit <= 0:
        raise ValueError("time_limit must be finite and positive")
    if not math.isfinite(relative_gap) or not 0 <= relative_gap <= 1:
        raise ValueError("relative_gap must be finite and in [0, 1]")
    for key, value in vars(scenario).items():
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError(f"{key} must be finite and nonnegative")
    if scenario.podium_footprint <= 0 or scenario.tower_footprint <= 0:
        raise ValueError("Footprints must be positive")
    for p in programs:
        if (not isinstance(p.bonus_block_units, int) or isinstance(p.bonus_block_units, bool)
                or p.bonus_block_units <= 0):
            raise ValueError("bonus_block_units must be a positive integer")
        if p.bonus_blocks and (not p.housing or p.continuous or p.bonus_far_per_unit):
            raise ValueError("Block bonuses require discrete housing and replace per-unit bonuses")
        if p.capitalization_rate is not None and (not math.isfinite(p.capitalization_rate)
                                                 or p.capitalization_rate <= 0):
            raise ValueError(f"{p.name} capitalization_rate must be finite and positive")
        values = (p.unit_sqft, p.minimum_sqft, p.maximum_sqft, p.noi_per_sqft,
                  p.podium_cost_per_sqft, p.tower_cost_per_sqft, p.bonus_far_per_unit)
        if not all(math.isfinite(v) for v in values):
            raise ValueError(f"{p.name} has nonfinite inputs")
        if (p.unit_sqft <= 0 or p.minimum_sqft <= 0 or p.maximum_sqft < p.minimum_sqft
                or min(p.podium_cost_per_sqft, p.tower_cost_per_sqft, p.bonus_far_per_unit) < 0):
            raise ValueError(f"{p.name} has invalid size, cost, or bonus bounds")
        required = required_quantities.get(p.name, 0)
        if not math.isfinite(required) or required < 0 or (not p.continuous and required != int(required)):
            raise ValueError(f"{p.name} required quantity must be nonnegative and respect whole units")

    n = len(programs)
    block_count = sum(len(p.bonus_blocks) for p in programs)
    size = 3 * n + 1 + block_count
    project = 3 * n
    # q_podium (outdoor quantity for outdoor programs), q_tower, selected, project.
    low, high = np.zeros(size), np.full(size, np.inf)
    integrality = np.zeros(size, dtype=int)
    high[2*n:] = 1
    integrality[2*n:] = 1
    noi, cost, bonus, podium, tower, outdoor, ground = (np.zeros(size) for _ in range(7))
    matrix, lower, upper = [], [], []

    def constrain(coeff, maximum=np.inf, minimum=-np.inf):
        matrix.append(coeff)
        lower.append(minimum)
        upper.append(maximum)

    if max_amenity_types is not None:
        if max_amenity_types < 0 or int(max_amenity_types) != max_amenity_types:
            raise ValueError("max_amenity_types must be a nonnegative integer")
        types = np.zeros(size)
        for i, p in enumerate(programs):
            types[2*n+i] = int(p.bonus_eligible or p.bonus_far_per_unit > 0 or bool(p.bonus_blocks))
        constrain(types, max_amenity_types)

    block_index = project + 1

    for i, p in enumerate(programs):
        unit = p.unit_sqft
        minimum = p.minimum_sqft / unit if p.continuous else math.ceil(p.minimum_sqft / unit)
        maximum_area = (scenario.podium_footprint * scenario.podium_stories
                        + scenario.tower_footprint * scenario.max_tower_stories
                        if p.unrestricted_nonhousing else p.maximum_sqft)
        maximum = maximum_area / unit if p.continuous else math.floor(maximum_area / unit)
        high[i] = high[n+i] = maximum
        if not p.continuous:
            integrality[i] = integrality[n+i] = 1
        noi[i] = noi[n+i] = p.noi_per_sqft * unit
        cost[i], cost[n+i] = p.podium_cost_per_sqft * unit, p.tower_cost_per_sqft * unit
        bonus[i] = bonus[n+i] = p.bonus_far_per_unit
        if p.bonus_blocks:
            earned = np.zeros(size)
            earned[i] = earned[n+i] = -1
            for j, increment in enumerate(p.bonus_blocks):
                if not math.isfinite(increment) or increment < 0:
                    raise ValueError("Block bonuses must be finite and nonnegative")
                index = block_index + j
                bonus[index] = increment
                earned[index] = p.bonus_block_units
                if j:
                    ordered = np.zeros(size)
                    ordered[index], ordered[index-1] = 1, -1
                    constrain(ordered, 0)
            constrain(earned, 0)
            block_index += len(p.bonus_blocks)
        selected = np.zeros(size)
        selected[i] = selected[n+i] = 1
        selected[2*n+i] = -maximum
        constrain(selected, 0)
        selected_min = selected.copy()
        selected_min[2*n+i] = -minimum
        constrain(selected_min, minimum=0)
        if required_quantities.get(p.name, 0):
            required = np.zeros(size)
            required[i] = required[n+i] = 1
            constrain(required, minimum=required_quantities[p.name])
        active = np.zeros(size)
        active[2*n+i], active[project] = 1, -1
        constrain(active, 0)
        if p.outdoor:
            high[n+i] = 0
            outdoor[i] = unit
            continue
        podium[i], tower[n+i] = unit, unit
        if p.ground_level:
            ground[i] = unit
            high[n+i] = 0
        elif not p.tower_allowed:
            high[n+i] = 0
        if not p.housing and not p.unrestricted_nonhousing:
            stories = np.zeros(size)
            stories[i] = unit / scenario.podium_footprint
            stories[n+i] = unit / scenario.tower_footprint
            constrain(stories, scenario.max_nonhousing_stories)

    # Do not charge land when nothing is selected; charge it exactly once otherwise.
    any_selected = np.zeros(size)
    any_selected[project] = 1
    any_selected[2*n:3*n] = -1
    constrain(any_selected, 0)
    cost[project] = scenario.land_cost
    podium_cap = scenario.podium_footprint * scenario.podium_stories
    tower_cap = scenario.tower_footprint * scenario.max_tower_stories
    constrain(podium, podium_cap)
    constrain(tower, tower_cap)
    constrain(outdoor, scenario.open_space)
    constrain(ground, scenario.podium_footprint)
    constrain(tower - bonus * scenario.tower_footprint,
              scenario.tower_footprint * scenario.base_tower_stories)
    if scenario.development_budget is not None:
        constrain(cost, scenario.development_budget)
    matrix = np.array(matrix)
    value = np.zeros(size)
    score = np.zeros(size)
    for i, p in enumerate(programs):
        rate = p.capitalization_rate if p.capitalization_rate is not None else scenario.capitalization_rate
        value[i] = value[n+i] = completed_value(noi[i], rate)
        for j in (i, n+i):
            score[j] = objective_contribution(objective, noi[j], cost[j],
                                              scenario.required_return, rate)
    score[project] = objective_contribution(objective, 0, cost[project],
                                            scenario.required_return, scenario.capitalization_rate)
    started = perf_counter()
    result = milp(-score, integrality=integrality, bounds=Bounds(low, high),
                  constraints=LinearConstraint(matrix, lower, upper),
                  options={"mip_rel_gap": relative_gap, "time_limit": time_limit})
    elapsed = perf_counter() - started
    report = {
        "status": "optimal" if result.status == 0 else "infeasible" if result.status == 2 else "limit" if result.status == 1 else "solver_error",
        "objective": objective,
        "scenario": vars(scenario),
        "required_quantities": required_quantities,
        "max_amenity_types": max_amenity_types,
        "solver": {"message": result.message, "solve_seconds": elapsed,
                   "nodes": int(result.mip_node_count) if getattr(result, "mip_node_count", None) is not None else None,
                   "relative_gap": float(result.mip_gap) if getattr(result, "mip_gap", None) is not None else None},
        "allocation": [], "totals": None,
        "limitations": "Stabilized model; provisional capitalization rates; negative NOI capitalized as an ongoing liability; simplified common area basis; no financing, vacancy, transaction costs, construction timing, floor-plan packing, or mechanical floors. Valuation is an estimate, not an additional cash receipt. Land excluded unless enabled. Objective choice remains provisional.",
    }
    if result.x is None:
        return report
    x = result.x.copy()
    integer = integrality == 1
    if np.any(np.abs(x[integer] - np.rint(x[integer])) > 1e-5):
        raise RuntimeError("Solver returned fractional whole units")
    x[integer] = np.rint(x[integer])
    if (np.any(x < low - 1e-5) or np.any(x > high + 1e-5)
            # Large area coefficients near break-even can accumulate sub-0.01
            # sqft solver rounding errors. Whole-unit checks above stay strict.
            or np.any(matrix @ x > np.array(upper) + 1e-2)
            or np.any(matrix @ x < np.array(lower) - 1e-2)):
        raise RuntimeError(f"Solver allocation failed independent feasibility checks: lower bound {float(np.max(low-x))}, upper bound {float(np.max(x-high))}, constraint upper {float(np.max(matrix @ x-np.array(upper)))}, constraint lower {float(np.max(np.array(lower)-matrix @ x))}")
    block_index = project + 1
    for i, p in enumerate(programs):
        qp, qt = float(x[i]), float(x[n+i])
        block_bonus = float(bonus[block_index:block_index+len(p.bonus_blocks)] @ x[block_index:block_index+len(p.bonus_blocks)])
        block_index += len(p.bonus_blocks)
        if qp + qt < 1e-7:
            continue
        area = (qp + qt) * p.unit_sqft
        construction = qp * cost[i] + qt * cost[n+i]
        annual_noi = area * p.noi_per_sqft
        rate = p.capitalization_rate if p.capitalization_rate is not None else scenario.capitalization_rate
        asset_value = completed_value(annual_noi, rate)
        report["allocation"].append({
            "amenity_type": p.name, "program_unit": p.program_unit, "quantity": qp + qt,
            "podium_quantity": 0.0 if p.outdoor else qp, "tower_quantity": qt,
            "area_sqft": area, "podium_sqft": 0.0 if p.outdoor else qp * p.unit_sqft,
            "tower_sqft": qt * p.unit_sqft, "outdoor_sqft": area if p.outdoor else 0.0,
            "bonus_far": (qp + qt) * p.bonus_far_per_unit + block_bonus,
            "annual_noi": annual_noi, "construction_cost": construction,
            "annual_surplus": annual_noi - scenario.required_return * construction,
            "capitalization_rate": rate, "completed_value": asset_value,
            "development_profit": asset_value - construction,
        })
    development_cost = float(cost @ x)
    annual_noi = float(noi @ x)
    earned_bonus = float(bonus @ x)
    podium_area, tower_area = float(podium @ x), float(tower @ x)
    uncapped_capacity = scenario.tower_footprint * (scenario.base_tower_stories + earned_bonus)
    effective_capacity = min(tower_cap, uncapped_capacity)
    report["decision"] = "develop" if x[project] > 0.5 else "no_development"
    report["totals"] = {
        "annual_noi": annual_noi, "construction_cost": development_cost - scenario.land_cost * x[project],
        "land_cost": float(scenario.land_cost * x[project]), "development_cost": development_cost,
        "annual_capital_charge": scenario.required_return * development_cost,
        "annual_surplus": annual_noi - scenario.required_return * development_cost,
        "yield_on_development_cost": annual_noi / development_cost if development_cost > 0 else None,
        "completed_value": float(value @ x),
        "development_profit": float(value @ x) - development_cost,
        "profit_on_cost": (float(value @ x) - development_cost) / development_cost if development_cost > 0 else None,
        "objective_value": float(score @ x),
        "bonus_far": earned_bonus, "podium_sqft": podium_area, "tower_sqft": tower_area,
        "indoor_sqft": podium_area + tower_area, "outdoor_sqft": float(outdoor @ x),
        "podium_floor_equivalents": podium_area / scenario.podium_footprint,
        "tower_floor_equivalents": tower_area / scenario.tower_footprint,
        "effective_tower_capacity_sqft": effective_capacity,
        "unused_authorized_tower_sqft": effective_capacity - tower_area,
        "bonus_capacity_blocked_by_height_cap_sqft": max(0.0, uncapped_capacity - tower_cap),
        "unused_podium_sqft": podium_cap - podium_area,
    }
    # Check exported accounting independently of solver coefficients.
    if not math.isclose(sum(p["annual_noi"] for p in report["allocation"]), annual_noi, abs_tol=1e-4):
        raise RuntimeError("Exported NOI does not reconcile")
    if not math.isclose(sum(p["construction_cost"] for p in report["allocation"]),
                        report["totals"]["construction_cost"], abs_tol=1e-4):
        raise RuntimeError("Exported construction costs do not reconcile")
    if not math.isclose(sum(p["completed_value"] for p in report["allocation"]),
                        report["totals"]["completed_value"], abs_tol=1e-4):
        raise RuntimeError("Exported completed values do not reconcile")
    return report

