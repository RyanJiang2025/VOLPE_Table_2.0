"""Read-only scenario comparison; does not alter production height assumptions."""
from dataclasses import replace
import json
import math
import sys
from pathlib import Path

from proforma.models import Scenario
from proforma.catalog import catalog_programs
from proforma.optimizer import optimize
from proforma.config import load_config
from proforma.pipeline import write_run


def analyze(config=None):
    config = config or load_config()
    # Nonbinding height ceiling; catalog quantity limits remain in force.
    scenario = replace(Scenario.from_config(config), max_tower_stories=1_000_000)
    programs = catalog_programs(config=config)
    luxury = next(p for p in programs if p.name == "luxury_multifamily")
    baseline = optimize([luxury], scenario, objective="development-profit", **config.solver_options)
    if baseline["status"] != "optimal":
        raise RuntimeError(baseline["status"])
    baseline_profit = baseline["totals"]["development_profit"]
    rows = []
    for p in programs:
        if p.bonus_far_per_unit <= 0:
            continue
        quantity = (p.minimum_sqft/p.unit_sqft if p.continuous else
                    math.ceil(p.minimum_sqft/p.unit_sqft))
        fixed = replace(p, minimum_sqft=quantity*p.unit_sqft,
                        maximum_sqft=quantity*p.unit_sqft)
        result = optimize([luxury, fixed], scenario,
                          required_quantities={p.name: quantity},
                          objective="development-profit", **config.solver_options)
        if result["status"] != "optimal":
            raise RuntimeError(f"{p.name}: {result['status']}")
        rows.append({"amenity": p.name, "bonus_far": quantity*p.bonus_far_per_unit,
                     "profit_change": result["totals"]["development_profit"]-baseline_profit,
                     "tower_stories": result["totals"]["tower_floor_equivalents"]})
    full = optimize(programs, scenario, objective="development-profit", **config.solver_options)
    if full["status"] != "optimal":
        raise RuntimeError(full["status"])
    return {"method": "Height cap made nonbinding; current bonuses, minimum single-amenity packages, luxury filler, developer-borne costs, and all other limits unchanged. Also includes unrestricted full-catalog optimization. Capitalization rate remains provisional at 4.5%.",
            "baseline": baseline, "individual_amenities": rows, "full_catalog": full}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--solver-path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.solver_path:
        sys.path.insert(0, str(args.solver_path.resolve()))
    config = load_config(args.scenario).with_overrides(bonuses={"policy": "legacy"})
    result = analyze(config)
    write_run({"uncapped_amenities.json": result}, config, command="uncapped-amenities", output=args.output,
              metadata={"bonus_policy": "legacy", "maximum_tower_stories_override": 1000000,
                        "catalog_bounds": "selected scenario before height override"})
    print(json.dumps(result["full_catalog"]["totals"], indent=2))
