"""Random preference stress tests; python -m experiments.preference_monte_carlo.

Independent Dirichlet(alpha=1) draws are uniform on the fixed-total simplex.
This explores hypothetical preferences, not uncertainty in the voting system.
The source preference file is never modified. Each trial recalibrates bonuses.
Use --winner general_office or --winner lab to raise that use's NOI enough to
beat luxury development profit/sqft by at least 10% in both building zones.
Those scenarios calibrate against the best mix of all bonus-ineligible uses.
Office/lab have no per-use upper area or floor-equivalent limits.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import random
import statistics
import sys
from dataclasses import replace

from proforma.bonuses import BonusPolicy, calibrate
from proforma.catalog import catalog_programs
from proforma.config import load_config
from proforma.models import Scenario
from proforma.optimizer import optimize
from proforma.pipeline import write_run


def random_weights(original, rng, alpha=1.0):
    if not math.isfinite(alpha) or alpha <= 0:
        raise ValueError("alpha must be positive and finite")
    total = math.fsum(original.values())
    draws = [rng.gammavariate(alpha, 1.0) for _ in original]
    scale = total/math.fsum(draws)
    values = [v*scale for v in draws]
    largest = max(range(len(values)), key=values.__getitem__)
    values[largest] += total-math.fsum(values)
    result = dict(zip(original, values))
    if not math.isclose(math.fsum(result.values()), total, abs_tol=1e-14, rel_tol=0):
        raise RuntimeError("Randomized weights changed the total")
    return result


def profit_override(programs, scenario, winner):
    """Raise winner NOI to beat luxury profit/sqft by at least 10% in both zones."""
    luxury = next(p for p in programs if p.name == "luxury_multifamily")
    candidate = next(p for p in programs if p.name == winner)
    luxury_rate = luxury.capitalization_rate or scenario.capitalization_rate
    rate = candidate.capitalization_rate or scenario.capitalization_rate
    required_noi = max(rate * (getattr(candidate, zone+'_cost_per_sqft') +
                        1.10*(luxury.noi_per_sqft/luxury_rate-getattr(luxury, zone+'_cost_per_sqft')))
                       for zone in ('podium', 'tower'))
    new_noi = max(candidate.noi_per_sqft, required_noi)
    changed = replace(candidate, noi_per_sqft=new_noi)
    comparisons = {zone: dict(luxury_profit_per_sqft=luxury.noi_per_sqft/luxury_rate-getattr(luxury, zone+'_cost_per_sqft'),
                             winner_profit_per_sqft=new_noi/rate-getattr(candidate, zone+'_cost_per_sqft'))
                   for zone in ('podium', 'tower')}
    return [changed if p.name == winner else p for p in programs], dict(
        winner=winner, original_noi_per_sqft=candidate.noi_per_sqft,
        scenario_noi_per_sqft=new_noi, comparisons=comparisons,
        method="Increase net rent/NOI only; construction costs and cap rates unchanged. Minimum 10% profit/sqft advantage in both zones.")


def run(trials=10, seed=20261008, alpha=1.0, output=None, winner=None, config=None):
    if trials <= 0:
        raise ValueError("trials must be positive")
    config = config or load_config()
    policy = BonusPolicy.from_config(config)
    original = config.weights
    rng = random.Random(seed)
    scenario = Scenario.from_config(config)
    inputs, override = catalog_programs(config=config, scenario=scenario), None
    threshold_cache = {}
    if winner:
        inputs, override = profit_override(inputs, scenario, winner)
    results, frequency = [], Counter()
    for number in range(1, trials+1):
        weights = random_weights(original, rng, alpha)
        programs, schedule, baseline = calibrate(scenario, weights=weights, programs=inputs,
                                                 use_all_fillers=bool(winner), policy=policy, solver_options=config.solver_options, threshold_cache=threshold_cache)
        result = optimize(programs, scenario, objective="development-profit",
                          max_amenity_types=policy.maximum_amenity_types, **config.solver_options)
        if result["status"] != "optimal":
            raise RuntimeError(f"Trial {number}: {result['status']}")
        eligible = {p.name for p in programs if p.bonus_eligible}
        selected = [p["amenity_type"] for p in result["allocation"] if p["amenity_type"] in eligible]
        frequency.update(selected)
        results.append(dict(trial=number, weights=weights, weight_total=math.fsum(weights.values()),
                            schedule=schedule, selected_amenity_types=selected,
                            baseline=baseline,
                            profit_gain_vs_no_amenities=result["totals"]["development_profit"]-baseline["totals"]["development_profit"],
                            result=result))
        allocation = ", ".join(f"{p['amenity_type']}={p['quantity']:g}" for p in result["allocation"])
        print(f"{number:2}: profit ${result['totals']['development_profit']:,.0f}; tower {result['totals']['tower_floor_equivalents']:.2f}; {allocation}", flush=True)
    profits = [r["result"]["totals"]["development_profit"] for r in results]
    report = dict(seed=seed, trials=trials, financial_override=override,
                  calibration_baseline="All bonus-ineligible profitable uses" if winner or policy.baseline == "all_fillers" else "Luxury only",
                  distribution=f"Dirichlet with common alpha={alpha}",
                  original_weight_total=math.fsum(original.values()),
                  randomized_scope="All identifiers in the saved snapshot, including inactive and bonus-ineligible uses; normalization remains weight/max(snapshot).",
                  policy=dict(max_types=policy.maximum_amenity_types,
                              one_unit_per_nonhousing_use=policy.one_package_per_nonhousing_use,
                              exemptions=policy.package_limit_exemptions,
                              unrestricted_nonhousing_uses=config.data["selection"]["floor_limit_exemptions"],
                              threshold=policy.threshold, max_premium=policy.maximum_premium,
                              housing_premiums=policy.housing_premium_multipliers),
                  scenario=vars(scenario),
                  summary=dict(mean_profit=statistics.mean(profits), minimum_profit=min(profits),
                               maximum_profit=max(profits), selection_frequency=dict(frequency.most_common())),
                  runs=results)
    write_run({"monte_carlo.json": report}, config, command="preference-monte-carlo", output=output,
              metadata={"seed": seed, "trials": trials, "alpha": alpha, "winner": winner,
                        "calibration_baseline": report["calibration_baseline"]})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--solver-path", type=Path)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20261008)
    parser.add_argument("--alpha", type=float, default=1.0, help="Larger values produce more equal weights")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--winner", choices=("general_office", "lab"))
    args = parser.parse_args()
    if args.solver_path:
        sys.path.insert(0, str(args.solver_path.resolve()))
    run(args.trials, args.seed, args.alpha, args.output, args.winner, config=load_config(args.scenario))
