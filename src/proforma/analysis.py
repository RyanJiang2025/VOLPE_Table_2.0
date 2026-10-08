"""Financial break-even and preference diagnostics; output writing is separate."""
from dataclasses import replace
import math

from .bonuses import BonusPolicy, calibrate, search_break_even
from .catalog import catalog_programs
from .config import load_config
from .models import Scenario
from .optimizer import optimize


def break_even_report(config=None, scenario=None):
    config = config or load_config()
    scenario = scenario or Scenario.from_config(config)
    programs = catalog_programs(config=config, scenario=scenario)
    luxury = next(p for p in programs if p.name == "luxury_multifamily")
    baseline = optimize([luxury], scenario, objective="development-profit", **config.solver_options)
    if baseline["status"] != "optimal":
        raise RuntimeError("Break-even baseline not optimal")
    baseline_profit = baseline["totals"]["development_profit"]
    rows = []
    for p in programs:
        if p.bonus_far_per_unit <= 0:
            continue
        quantity = p.minimum_sqft / p.unit_sqft if p.continuous else math.ceil(p.minimum_sqft / p.unit_sqft)
        p = replace(p, minimum_sqft=quantity * p.unit_sqft, maximum_sqft=quantity * p.unit_sqft)
        current_bonus = quantity * p.bonus_far_per_unit

        def solve(total_bonus):
            candidate = replace(p, bonus_far_per_unit=total_bonus / quantity)
            result = optimize([luxury, candidate], scenario, required_quantities={p.name: quantity},
                              objective="development-profit", **config.solver_options)
            if result["status"] != "optimal":
                raise RuntimeError(f"{p.name}: {result['status']}")
            return result

        current = solve(current_bonus)
        threshold, maximum = search_break_even(solve, 100.0, baseline_profit, iterations=30)
        own = next(item for item in current["allocation"] if item["amenity_type"] == p.name)
        rows.append({
            "amenity": p.name, "quantity": quantity, "area_sqft": quantity * p.unit_sqft,
            "current_total_bonus_far": current_bonus,
            "profit_change_vs_no_amenity": current["totals"]["development_profit"] - baseline_profit,
            "construction_cost": own["construction_cost"], "annual_noi": own["annual_noi"],
            "podium_sqft": own["podium_sqft"], "tower_sqft": own["tower_sqft"],
            "break_even_total_bonus_far": threshold,
            "additional_bonus_far_needed": None if threshold is None else max(0, threshold - current_bonus),
            "bonus_multiplier_needed": None if threshold is None else threshold / current_bonus,
            "best_profit_change_at_full_capacity": maximum["totals"]["development_profit"] - baseline_profit,
        })
    return {
        "scenario": vars(scenario), "baseline": baseline["totals"], "amenities": rows,
        "method": (
            "Exactly the minimum package of one amenity plus luxury housing; whole units and optimal placement. "
            "Break-even means matching the no-amenity development profit. Total bonus includes existing area refund. "
            "Other amenities excluded. Negative NOI capitalized as developer liability; no city subsidy. "
            f"{scenario.capitalization_rate:.1%} capitalization rate provisional. No changes to bonus assumptions."
        ),
    }


def preference_report(config=None, scenario=None):
    config = config or load_config()
    scenario = scenario or Scenario.from_config(config)
    policy = BonusPolicy.from_config(config)
    programs, schedule, baseline = calibrate(
        scenario, config.weights, catalog_programs(config=config, scenario=scenario),
        policy=policy, solver_options=config.solver_options)
    result = optimize(programs, scenario, objective="development-profit",
                      max_amenity_types=policy.maximum_amenity_types, **config.solver_options)
    result["bonus_policy"] = "preference"
    if policy.baseline == "all_fillers":
        fillers = [p for p in programs if not p.bonus_eligible]
    else:
        fillers = [next(p for p in programs if p.name == "luxury_multifamily")]
    isolated = []
    for p in programs:
        if not p.bonus_eligible:
            continue
        quantity = p.minimum_sqft / p.unit_sqft if p.continuous else math.ceil(p.minimum_sqft / p.unit_sqft)
        fixed = replace(p, maximum_sqft=quantity * p.unit_sqft)
        trial = optimize(fillers + [fixed], scenario, required_quantities={p.name: quantity},
                         objective="development-profit", **config.solver_options)
        isolated.append({
            "amenity": p.name, "status": trial["status"],
            "profit_change": None if trial["totals"] is None else
                trial["totals"]["development_profit"] - baseline["totals"]["development_profit"],
        })
    portfolio_checks = []
    for item in result["allocation"]:
        name = item["amenity_type"]
        if not next(p for p in programs if p.name == name).bonus_eligible:
            continue
        without = optimize([p for p in programs if p.name != name], scenario,
                           objective="development-profit", max_amenity_types=policy.maximum_amenity_types,
                           **config.solver_options)
        portfolio_checks.append({
            "amenity": name, "status": without["status"],
            "profit_advantage_over_reoptimized_project_without_type": None if without["totals"] is None else
                result["totals"]["development_profit"] - without["totals"]["development_profit"],
        })
    return {
        "policy": {
            "threshold": policy.threshold, "max_premium": policy.maximum_premium,
            "max_types": policy.maximum_amenity_types,
            "one_unit_per_nonhousing_use": policy.one_package_per_nonhousing_use,
            "nonhousing_unit_limit_exemptions": policy.package_limit_exemptions,
            "normalization": "cardinal weight / largest weight in saved snapshot",
            "housing_premium_multipliers": policy.housing_premium_multipliers,
        },
        "schedule": schedule, "isolated_checks": isolated, "portfolio_checks": portfolio_checks,
        "baseline": baseline, "result": result,
    }
