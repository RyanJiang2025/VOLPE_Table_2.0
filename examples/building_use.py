"""Assemble the prescribed example building using the shared model inputs.

Run: python -m examples.building_use
"""
import argparse
import json
import math
from pathlib import Path
from proforma.catalog import build_catalog
from proforma.config import load_config
from proforma.models import Scenario
from proforma.pipeline import write_run


def build_example(config=None, housing_units=5) -> dict:
    config = config or load_config()
    scenario = Scenario.from_config(config)
    site = config.data["site"]
    PARCEL_AREA_SQFT = site["parcel_area_sqft"]
    OPEN_SPACE_AREA_SQFT = scenario.open_space
    PODIUM_FOOTPRINT_SQFT = scenario.podium_footprint
    TOWER_FOOTPRINT_SQFT = scenario.tower_footprint
    PODIUM_STORIES = scenario.podium_stories
    BASE_TOWER_STORIES = scenario.base_tower_stories
    MAX_TOWER_STORIES = scenario.max_tower_stories
    MAX_TOWER_CAPACITY_SQFT = scenario.maximum_tower_capacity
    BONUS_FAR_AREA_SQFT = scenario.tower_footprint
    EXAMPLE_HOUSING_UNITS = housing_units
    tower_capacity_for_bonus = scenario.tower_capacity_for_bonus
    catalog = build_catalog(config, scenario).set_index("amenity_type")
    FOR_PROFIT_USES = set(catalog.index[catalog["is_for_profit_use"]])
    inputs = {
        "parcel_sqft": PARCEL_AREA_SQFT,
        "open_space_sqft": OPEN_SPACE_AREA_SQFT,
        "podium_footprint_sqft": PODIUM_FOOTPRINT_SQFT,
        "tower_footprint_sqft": TOWER_FOOTPRINT_SQFT,
        "podium_stories": PODIUM_STORIES,
        "base_tower_stories": BASE_TOWER_STORIES,
        "max_tower_stories": MAX_TOWER_STORIES,
        "max_tower_capacity_sqft": MAX_TOWER_CAPACITY_SQFT,
        "podium_capacity_sqft": PODIUM_FOOTPRINT_SQFT * PODIUM_STORIES,
        "base_tower_capacity_sqft": TOWER_FOOTPRINT_SQFT * BASE_TOWER_STORIES,
        "tower_sqft_per_bonus_far": BONUS_FAR_AREA_SQFT,
    }
    # Compact scenario: explicit apartment counts, no full hospital.
    candidates = catalog.loc[[
        "mid_career_multifamily", "general_multifamily",
        "attainable_multifamily",
    ]]
    open_remaining = inputs["open_space_sqft"]
    programs = []

    def program(name: str, area: float, zone: str, role: str) -> dict:
        row = catalog.loc[name]
        if not row.minimum_program_sqft <= area <= row.maximum_program_sqft:
            raise ValueError(f"{name} violates program size bounds")
        if zone == "tower" and not row.tower_allowed:
            raise ValueError(f"{name} cannot be placed in the tower")
        quantity = area / row.default_unit_sqft
        if row.program_unit != "square_foot" and not math.isclose(quantity, round(quantity)):
            raise ValueError(f"{name} requires whole units")
        rate = row.plinth_total_cost_per_sqft if zone != "tower" else row.tower_total_cost_per_sqft
        scale = area / row.square_footage
        return {
            "amenity_type": name, "role": role, "location": zone,
            "program_unit": row.program_unit,
            "quantity": int(round(quantity)) if row.program_unit != "square_foot" else area,
            "area_sqft": area,
            "demand_far_bonus": float(row.demand_FAR_Bonus * scale),
            "footprint_refund_far": float(row.footprint_refund_FAR * scale),
            "far_bonus": float(row.FAR_Bonus * scale),
            "annual_noi": float((row.rent_per_sqft_yearly - row.upkeep_per_sqft_yearly) * area),
            "construction_cost": float(rate * area),
        }

    # The compact playground is one whole facility matching the open-space allotment.
    programs.append(program("playground", float(open_remaining), "open_space", "subsidized"))
    open_remaining = 0
    skipped_outdoor = ["park"]
    for name, row in candidates.iterrows():
        programs.append(program(name, EXAMPLE_HOUSING_UNITS * float(row.default_unit_sqft), "tower", "subsidized"))
    for name in ("cafe", "greengrocer"):
        programs.append(program(name, float(catalog.loc[name, "default_unit_sqft"]), "podium", "subsidized"))
    ground_area = sum(p["area_sqft"] for p in programs
                     if p["location"] == "podium" and catalog.loc[p["amenity_type"], "ground_level"])
    if ground_area > inputs["podium_footprint_sqft"]:
        raise ValueError("Cafe and grocery store exceed the ground-floor capacity")
    amenity_podium = sum(p["area_sqft"] for p in programs if p["location"] == "podium")

    bonus = sum(p["far_bonus"] for p in programs)
    uncapped_tower_capacity = inputs["base_tower_capacity_sqft"] + bonus * BONUS_FAR_AREA_SQFT
    tower_capacity = tower_capacity_for_bonus(bonus)
    selected_tower = sum(p["area_sqft"] for p in programs if p["location"] == "tower")
    if selected_tower > tower_capacity:
        raise ValueError("Selected tower amenities exceed the bonus or physical tower capacity")
    subsidized_indoor = sum(p["area_sqft"] for p in programs if p["location"] != "open_space")
    filler_area = inputs["podium_capacity_sqft"] + tower_capacity - subsidized_indoor
    if filler_area <= 0:
        raise ValueError("Selected amenities leave no room for the requested filler")
    # Respect each use cap; allowable capacity need not be fully occupied.
    lab_area = float(catalog.loc["lab", "square_footage"])
    luxury_area = EXAMPLE_HOUSING_UNITS * float(catalog.loc["luxury_multifamily", "default_unit_sqft"])
    office_area = min(float(catalog.loc["general_office", "maximum_program_sqft"]),
                      filler_area - lab_area - luxury_area)
    podium_office = min(inputs["podium_capacity_sqft"] - amenity_podium, office_area)
    programs.append(program("general_office", office_area, "tower", "for_profit"))
    office = programs[-1]
    office["location"] = "podium_and_tower"
    office["podium_area_sqft"] = podium_office
    office["tower_area_sqft"] = office_area - podium_office
    office["construction_cost"] = float(
        podium_office * catalog.loc["general_office", "plinth_total_cost_per_sqft"]
        + (office_area - podium_office) * catalog.loc["general_office", "tower_total_cost_per_sqft"]
    )
    programs.append(program("lab", lab_area, "tower", "for_profit"))
    programs.append(program("luxury_multifamily", luxury_area, "tower", "for_profit"))

    # Check totals after placing all uses, including both office locations.
    actual_tower = sum(p.get("tower_area_sqft", p["area_sqft"])
                       for p in programs if p["location"] in ("tower", "podium_and_tower"))
    actual_podium = podium_office + amenity_podium
    if actual_tower > tower_capacity or actual_podium > inputs["podium_capacity_sqft"]:
        raise ValueError("Allocation exceeds the podium or tower capacities")
    for name in {p["amenity_type"] for p in programs}:
        allocated = sum(p["area_sqft"] for p in programs if p["amenity_type"] == name)
        if allocated > catalog.loc[name, "maximum_program_sqft"]:
            raise ValueError(f"{name} exceeds its aggregate use cap")
    if any(p["far_bonus"] != 0 for p in programs if p["role"] == "for_profit"):
        raise ValueError("For-profit filler must not generate capacity")
    total_noi = sum(p["annual_noi"] for p in programs)
    cost = sum(p["construction_cost"] for p in programs)
    return {
        "status": "allocated", "inputs": inputs,
        "area_note": (f"Separate {PODIUM_FOOTPRINT_SQFT:g} sqft podium, "
                      f"{TOWER_FOOTPRINT_SQFT:g} sqft tower and {OPEN_SPACE_AREA_SQFT:g} sqft "
                      f"open-space footprints occupy a {PARCEL_AREA_SQFT:g} sqft parcel."),
        "bonus_rule": {
            "eligible_indoor": f"floor area / {BONUS_FAR_AREA_SQFT:g} + demand bonus",
            "outdoor": "demand bonus only",
            "zero_bonus_for_profit_uses": sorted(FOR_PROFIT_USES),
        },
        "allocation_policy": {
            "subsidized_amenities": f"{housing_units} mid-career, {housing_units} general and {housing_units} attainable apartments in the tower; one cafe and one greengrocer on the ground floor. Hospital excluded.",
            "outdoor": f"One playground using the full {OPEN_SPACE_AREA_SQFT:g} sqft open-space allotment.",
            "filler": f"One lab program, {housing_units} luxury apartments and office filler within available capacity; unused capacity is retained.",
            "grocery_store_catalog_use": "greengrocer",
        },
        "skipped_outdoor_uses": skipped_outdoor,
        "allocation": programs,
        "totals": {
            "subsidized_indoor_sqft": subsidized_indoor,
            "bonus_far": bonus, "podium_sqft": podium_office + amenity_podium,
            "tower_sqft": actual_tower, "indoor_sqft": actual_podium + actual_tower,
            "tower_capacity_sqft": tower_capacity,
            "uncapped_tower_capacity_sqft": uncapped_tower_capacity,
            "capacity_removed_by_height_cap_sqft": uncapped_tower_capacity - tower_capacity,
            "unused_tower_capacity_sqft": tower_capacity - actual_tower,
            "unused_podium_capacity_sqft": inputs["podium_capacity_sqft"] - actual_podium,
            "tower_floor_equivalents": actual_tower / TOWER_FOOTPRINT_SQFT,
            "podium_floor_equivalents": actual_podium / PODIUM_FOOTPRINT_SQFT,
            "for_profit_filler_sqft": office_area + lab_area + luxury_area,
            "unused_open_space_sqft": float(open_remaining),
            "annual_noi": total_noi, "construction_cost": cost,
            "yield_on_construction_cost": total_noi / cost,
        },
        "limitations": f"Synthetic floor-area allocation; fractional tower floors allowed. Construction cost includes hard and soft costs, excluding land and financing; tower area is capped at {MAX_TOWER_STORIES:g} stories independently of bonuses, with a separate {PODIUM_STORIES:g}-story podium.",
    }



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--housing-units", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = load_config(args.scenario).with_overrides(bonuses={"policy": "legacy"})
    result = build_example(config, args.housing_units)
    manifest = write_run({"building_example.json": result}, config, command="building-example", output=args.output,
                         metadata={"housing_units": args.housing_units, "bonus_policy": "legacy"})
    print(json.dumps(result["totals"], indent=2))
    print("Manifest:", manifest)
