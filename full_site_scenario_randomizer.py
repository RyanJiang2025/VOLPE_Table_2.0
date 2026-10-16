"""Run five matched pairs of randomized full-site pro forma scenarios.

From ProForma: python full_site_scenario_randomizer.py
Use --seed INTEGER to reproduce a batch; otherwise a fresh seed is generated.
Financial bounds are synthetic stress assumptions derived from saved inputs,
not market estimates. Shared configuration files are never modified.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
import math
from pathlib import Path
import random
import secrets
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from experiments.preference_monte_carlo import random_weights
from proforma.bonuses import BonusPolicy, calibrate
from proforma.catalog import catalog_programs
from proforma.config import freeze, load_config, thaw
from proforma.finance import operating_rates
from proforma.models import Scenario
from proforma.optimizer import optimize
from proforma.pipeline import write_run

BLOCK_SQFT = 625
PAIRS = (("red", 22), ("green", 24), ("yellow", 22), ("blue", 24), ("purple", 20))
USES = ("lab", "luxury_multifamily", "general_office")
ZONES = ("podium", "tower")


def site_layout(blocks, tower_allowed):
    """Round open space first; split remaining blocks, tower receiving odd block."""
    open_blocks = math.floor(0.2 * blocks + 0.5)
    built = blocks - open_blocks
    podium = built // 2 if tower_allowed else built
    return dict(parcel_area_sqft=blocks * BLOCK_SQFT,
                open_space_sqft=open_blocks * BLOCK_SQFT,
                podium_sqft=podium * BLOCK_SQFT,
                tower_sqft=(built - podium) * BLOCK_SQFT)


def financial_bounds(config, reference_bounds=None):
    """Hold costs/cap rates/expense fractions fixed and derive two NOI settings.

    Low = min(80% of saved NOI, 90% of the cheaper zone's break-even NOI).
    High >= 120% of saved NOI, and gives >= 110% of the best saved indoor
    development profit/sqft (or $1/sqft) in EACH zone. Thus any selected high
    use is profitable in both zones; the other two cannot profitably infill.
    """
    scenario = Scenario.from_config(config)
    programs = catalog_programs(config=config, scenario=scenario)
    catalog = {p.name: p for p in programs}
    source_rows = {r["amenity_type"]: r for r in config.datasets["catalog"]["amenities"]}
    economics = config.datasets["economics"]
    best_profit = {zone: max(1.0, *(p.noi_per_sqft / (p.capitalization_rate or scenario.capitalization_rate)
                                  - getattr(p, zone + "_cost_per_sqft") for p in programs if not p.outdoor))
                   for zone in ZONES}
    bounds = {}
    for name in USES:
        p = catalog[name]
        cap = p.capitalization_rate or scenario.capitalization_rate
        costs = {zone: getattr(p, zone + "_cost_per_sqft") for zone in ZONES}
        low = min(0.8 * p.noi_per_sqft, 0.9 * cap * min(costs.values()))
        high = max(1.2 * p.noi_per_sqft,
                   *(cap * (costs[zone] + 1.1 * best_profit[zone]) for zone in ZONES))
        if reference_bounds is not None:
            # Isolate construction-cost changes without silently changing rents.
            low = reference_bounds[name]["lower"]["annual_noi_per_sqft"]
            high = reference_bounds[name]["higher"]["annual_noi_per_sqft"]
        if low < 0:
            raise ValueError(f"{name}: this bound method requires nonnegative saved NOI")
        group = source_rows[name]["financial_group"]
        row = economics["use_overrides"].get(name, economics["financial_groups"][group])
        rent, upkeep, fraction = operating_rates(row, source_rows)
        if fraction == 1:
            raise ValueError(f"{name}: cannot vary NOI with a 100% expense fraction")

        def metrics(noi):
            implied_rent = noi / (1 - fraction) if fraction is not None else noi + upkeep
            return dict(annual_noi_per_sqft=noi, annual_rent_per_sqft=implied_rent,
                        annual_expenses_per_sqft=implied_rent - noi,
                        annual_noi_per_unit=noi * p.unit_sqft if p.housing else None,
                        annual_rent_per_unit=implied_rent * p.unit_sqft if p.housing else None,
                        development_profit_per_sqft={zone: noi / cap - costs[zone] for zone in ZONES})

        bounds[name] = dict(unit_sqft=p.unit_sqft, program_unit=p.program_unit,
                            capitalization_rate=cap, construction_cost_per_sqft=costs,
                            expense_fraction=fraction,
                            original=metrics(rent - upkeep), lower=metrics(low), higher=metrics(high))
    return bounds


def pair_config(config, weights, winner, bounds):
    datasets = thaw(config.datasets)
    datasets["preferences"]["weights"] = list(weights.items())
    uses = {r["amenity_type"]: r for r in datasets["catalog"]["amenities"]}
    economics = datasets["economics"]
    for name in USES:
        level = "higher" if name == winner else "lower"
        settings = bounds[name][level]
        group = uses[name]["financial_group"]
        source = economics["use_overrides"].get(name, economics["financial_groups"][group])
        row = dict(source)
        if "annual_rent_per_unit_usd" in row:
            row["annual_rent_per_unit_usd"] = settings["annual_rent_per_unit"]
        else:
            row["annual_rent_per_sqft_usd"] = settings["annual_rent_per_sqft"]
        row["basis"] = f"Synthetic full-site randomizer {level} bound derived from saved inputs."
        economics["use_overrides"][name] = row
    # Validate the modified datasets as well as the scenario sections.
    return replace(config, datasets=freeze(datasets)).with_overrides(
        finance={"objective": "development-profit"},
        bonuses={"policy": "preference", "baseline": "all_fillers"})


def scenario_config(config, color, blocks, tower_allowed):
    layout = site_layout(blocks, tower_allowed)
    site = thaw(config.data["site"])
    site.update(parcel_area_sqft=layout["parcel_area_sqft"], open_space_sqft=layout["open_space_sqft"])
    site["podium"]["footprint_sqft"] = layout["podium_sqft"]
    site["podium"]["stories"] = 5
    site["podium_extends_under_tower"] = True
    site["tower"]["footprint_sqft"] = layout["tower_sqft"]
    # The first five stories beneath the tower are now in the podium zone.
    # Additional stories are awarded through amenity FAR, capped at 25 above it.
    site["tower"].update(base_stories=0, maximum_stories=25 if tower_allowed else 0)
    current = config.with_overrides(site=site)
    return replace(current, data=freeze({**thaw(current.data),
                   "name": f"{color}_{'mixed' if tower_allowed else 'podium_only'}"}))


def run(seed=None, config=None, output_dir=None, compare_to=None, financial_inputs_from=None):
    config = config or load_config()
    seed = secrets.randbits(64) if seed is None else seed
    rng = random.Random(seed)
    reference = None
    if financial_inputs_from is not None:
        reference = json.loads(Path(financial_inputs_from).read_text(encoding="utf-8"))
    bounds = financial_bounds(config, reference["financial_bounds"] if reference else None)
    print(f"Seed: {seed}", flush=True)
    runs = []
    for color, blocks in PAIRS:
        weights = random_weights(config.weights, rng)
        winner = rng.choice(USES)
        paired = pair_config(config, weights, winner, bounds)
        for tower_allowed in (False, True):
            current = scenario_config(paired, color, blocks, tower_allowed)
            scenario = Scenario.from_config(current)
            policy = BonusPolicy.from_config(current)
            inputs = catalog_programs(config=current, scenario=scenario)
            print(f"Solving {current.data['name']}: profitable use {winner}", flush=True)
            programs, schedule, baseline = calibrate(
                scenario, weights, inputs, policy=policy, use_all_fillers=True,
                solver_options=current.solver_options)
            result = optimize(programs, scenario, objective="development-profit",
                              max_amenity_types=policy.maximum_amenity_types, **current.solver_options)
            if result["status"] != "optimal":
                raise RuntimeError(f"{current.data['name']}: solver status {result['status']}")
            eligible = {p.name for p in programs if p.bonus_eligible}
            fillers = [a for a in result["allocation"] if a["amenity_type"] not in eligible]
            core_fillers = [a for a in fillers if a["amenity_type"] in USES]
            if not core_fillers or any(a["amenity_type"] != winner for a in core_fillers):
                raise RuntimeError(f"{current.data['name']}: unexpected lab/luxury/office allocation")
            if not tower_allowed and (result["totals"]["tower_sqft"] or result["totals"]["bonus_far"]):
                raise RuntimeError("Podium-only scenario used tower capacity or earned usable FAR")
            record = dict(scenario_id=current.data["name"], color=color, profitable_use=winner,
                          tower_allowed=tower_allowed, weights=weights,
                          preference_ranking=sorted(weights, key=weights.get, reverse=True),
                          financial_levels={name: "higher" if name == winner else "lower" for name in USES},
                          other_nonbonus_infill=[a for a in fillers if a["amenity_type"] not in USES],
                          footprint=site_layout(blocks, tower_allowed),
                          resolved_configuration=current.resolved(),
                          calibrated_programs=[vars(p) for p in programs],
                          schedule=schedule, baseline=baseline, result=result)
            runs.append(record)
            print(f"  Optimal: profit ${result['totals']['development_profit']:,.0f}; "
                  f"podium {result['totals']['podium_sqft']:,.0f} sqft; "
                  f"tower {result['totals']['tower_sqft']:,.0f} sqft", flush=True)
    report = dict(seed=seed, scenario_count=len(runs), financial_bounds=bounds,
                  geometry="Five podium-priced stories across podium + tower land footprints; zero base tower stories; up to 25 amenity-bonus tower-priced stories above the podium (30 stories total).",
                  financial_method=financial_bounds.__doc__,
                  preference_method="Independent Dirichlet(alpha=1) weights per color; preserve all identifiers and total; normalize by full snapshot maximum.",
                  pairing="Preferences, financial bounds, and profitable use identical within each color pair.",
                  rounding="Nearest 625 sqft for open space; split remainder evenly, odd block to tower.",
                  limitations="Synthetic financial stress bounds, not market estimates. Existing unit/package limits retained. Whole apartments can leave unused floor area. Bonus-eligible uses may also occupy base floor area under the existing optimizer; FAR is not tracked by floor or use.",
                  summary=[dict(scenario_id=r["scenario_id"], profitable_use=r["profitable_use"],
                                **{key: r["result"]["totals"][key] for key in (
                                    "development_profit", "podium_sqft", "tower_sqft", "bonus_far",
                                    "unused_podium_sqft", "unused_authorized_tower_sqft")}) for r in runs],
                  runs=runs)
    report["pair_comparisons"] = []
    if reference is not None:
        report["financial_inputs_from"] = str(Path(financial_inputs_from).resolve())
        report["financial_method"] = "Lower/higher annual NOI retained from financial_inputs_from; construction costs and profit metrics recalculated using current configuration. Implied rents retain current expense assumptions."
    for podium, mixed in zip(runs[::2], runs[1::2]):
        podium_profit = podium["result"]["totals"]["development_profit"]
        mixed_profit = mixed["result"]["totals"]["development_profit"]
        report["pair_comparisons"].append(dict(
            color=podium["color"], profitable_use=podium["profitable_use"],
            podium_only_profit=podium_profit, mixed_profit=mixed_profit,
            mixed_profit_advantage=mixed_profit - podium_profit,
            remaining_gap_to_podium_only=max(0, podium_profit - mixed_profit),
            mixed_profit_advantage_percent=100 * (mixed_profit - podium_profit) / podium_profit if podium_profit else None))
    if compare_to is not None:
        previous_path = Path(compare_to).resolve()
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        if previous["seed"] != seed or previous["financial_bounds"] != bounds:
            raise ValueError("Comparison batch must have the same seed and financial bounds")
        old_runs = {r["scenario_id"]: r for r in previous["runs"]}
        comparisons = []
        for current in runs:
            old = old_runs[current["scenario_id"]]
            if old["weights"] != current["weights"] or old["profitable_use"] != current["profitable_use"]:
                raise ValueError("Comparison batch preferences/profitable uses differ")
            before = old["result"]["totals"]["development_profit"]
            after = current["result"]["totals"]["development_profit"]
            comparisons.append(dict(scenario_id=current["scenario_id"],
                                    previous_profit=before, current_profit=after,
                                    change_in_profit=after - before))
        report["previous_layout_comparison"] = dict(source=str(previous_path), runs=comparisons)
    manifest = write_run({"full_site_scenarios.json": report}, config,
                         command="full-site-scenario-randomizer", output_dir=output_dir,
                         metadata={"seed": seed, "scenario_count": len(runs)})
    print(f"Results: {manifest.parent / 'full_site_scenarios.json'}", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--solver-path", type=Path)
    parser.add_argument("--output-dir", type=Path, help="New directory for report and provenance manifest")
    parser.add_argument("--compare-to", type=Path, help="Previous JSON batch with matching seed and financial bounds")
    parser.add_argument("--financial-inputs-from", type=Path,
                        help="Retain a previous batch's low/high NOI when testing different construction costs")
    args = parser.parse_args()
    if args.solver_path:
        sys.path.insert(0, str(args.solver_path.resolve()))
    run(seed=args.seed, config=load_config(args.scenario), output_dir=args.output_dir,
        compare_to=args.compare_to, financial_inputs_from=args.financial_inputs_from)
