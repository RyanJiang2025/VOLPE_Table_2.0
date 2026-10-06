"""Regenerate the finite dummy building program from the active catalog."""
from __future__ import annotations

import json
import math
from pathlib import Path

if __package__:
    from .amenity_list import (
        BONUS_FAR_AREA_SQFT, FOR_PROFIT_USES, OUTDOOR_USES,
        buildable_use_catalog,
    )
else:
    from amenity_list import (
        BONUS_FAR_AREA_SQFT, FOR_PROFIT_USES, OUTDOOR_USES,
        buildable_use_catalog,
    )


def build_example() -> dict:
    catalog = buildable_use_catalog.set_index("amenity_type")
    inputs = {
        "parcel_sqft": 12_500,
        "open_space_sqft": 2_500,
        "podium_footprint_sqft": 4_000,
        "tower_footprint_sqft": 4_000,
        "podium_stories": 5,
        "base_tower_stories": 5,
        "podium_capacity_sqft": 20_000,
        "base_tower_capacity_sqft": 20_000,
        "tower_sqft_per_bonus_far": BONUS_FAR_AREA_SQFT,
    }
    # Preserve the selected amenities except for the user-requested senior swap.
    candidates = catalog.loc[[
        "hospital", "mid_career_multifamily", "general_multifamily",
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
        resized_playground = name == "playground" and zone == "open_space"
        if row.program_unit != "square_foot" and not resized_playground and not math.isclose(quantity, round(quantity)):
            raise ValueError(f"{name} requires whole units")
        rate = row.plinth_total_cost_per_sqft if zone != "tower" else row.tower_total_cost_per_sqft
        scale = area / row.square_footage
        return {
            "amenity_type": name, "role": role, "location": zone,
            "program_unit": row.program_unit,
            "quantity": 1 if resized_playground else (
                int(round(quantity)) if row.program_unit != "square_foot" else area
            ),
            "area_sqft": area,
            "demand_far_bonus": float(row.demand_FAR_Bonus * scale),
            "footprint_refund_far": float(row.footprint_refund_FAR * scale),
            "far_bonus": float(row.FAR_Bonus * scale),
            "annual_noi": float((row.rent_per_sqft_yearly - row.upkeep_per_sqft_yearly) * area),
            "construction_cost": float(rate * area),
        }

    # The user explicitly selected one playground resized to the site allotment.
    programs.append(program("playground", float(open_remaining), "open_space", "subsidized"))
    open_remaining = 0
    skipped_outdoor = ["park", "outdoor_sports"]
    for name, row in candidates.iterrows():
        programs.append(program(name, float(row.square_footage), "tower", "subsidized"))
    for name in ("cafe", "greengrocer"):
        programs.append(program(name, float(catalog.loc[name, "default_unit_sqft"]), "podium", "subsidized"))
    ground_area = sum(p["area_sqft"] for p in programs
                     if p["location"] == "podium" and catalog.loc[p["amenity_type"], "ground_level"])
    if ground_area > inputs["podium_footprint_sqft"]:
        raise ValueError("Cafe and grocery store exceed the ground-floor capacity")
    amenity_podium = sum(p["area_sqft"] for p in programs if p["location"] == "podium")

    bonus = sum(p["far_bonus"] for p in programs)
    tower_capacity = inputs["base_tower_capacity_sqft"] + bonus * BONUS_FAR_AREA_SQFT
    subsidized_indoor = sum(p["area_sqft"] for p in programs if p["location"] != "open_space")
    filler_area = inputs["podium_capacity_sqft"] + tower_capacity - subsidized_indoor
    if filler_area <= 0:
        raise ValueError("Selected amenities leave no room for the requested filler")
    # Keep the established lab and luxury allocations; office takes the remainder.
    lab_area = 60_280.993524182064
    luxury_area = 48 * float(catalog.loc["luxury_multifamily", "default_unit_sqft"])
    office_area = filler_area - lab_area - luxury_area
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
    if not math.isclose(actual_tower, tower_capacity) or podium_office + amenity_podium != 20_000:
        raise ValueError("Allocation does not fill the podium and tower capacities")
    if any(p["far_bonus"] != 0 for p in programs if p["role"] == "for_profit"):
        raise ValueError("For-profit filler must not generate capacity")
    total_noi = sum(p["annual_noi"] for p in programs)
    cost = sum(p["construction_cost"] for p in programs)
    return {
        "status": "allocated", "inputs": inputs,
        "area_note": "The stated 4000 sqft footprints each equal 32% of the parcel; 2000 sqft of land is unassigned.",
        "bonus_rule": {
            "eligible_indoor": "floor area / 4000 + demand bonus",
            "outdoor": "demand bonus only",
            "zero_bonus_for_profit_uses": sorted(FOR_PROFIT_USES),
        },
        "allocation_policy": {
            "subsidized_amenities": "Hospital and mid-career, general, and attainable housing remain in tower; senior housing is replaced by one cafe and one greengrocer grocery store on the ground floor.",
            "outdoor": "One playground resized to 2500 sqft, occupying the full open-space allotment as requested.",
            "filler": "Preserve 60280.993524182064 sqft of lab and 48 luxury apartments; office fills all remaining indoor capacity after recomputing amenity bonuses.",
            "grocery_store_catalog_use": "greengrocer",
        },
        "skipped_outdoor_uses": skipped_outdoor,
        "allocation": programs,
        "totals": {
            "subsidized_indoor_sqft": subsidized_indoor,
            "bonus_far": bonus, "podium_sqft": podium_office + amenity_podium,
            "tower_sqft": tower_capacity, "indoor_sqft": podium_office + amenity_podium + tower_capacity,
            "for_profit_filler_sqft": filler_area,
            "unused_open_space_sqft": float(open_remaining),
            "annual_noi": total_noi, "construction_cost": cost,
            "yield_on_construction_cost": total_noi / cost,
        },
        "limitations": "Synthetic floor-area allocation; fractional tower floors allowed. Construction cost includes hard and soft costs, excluding land and financing; no separate physical height cap is specified.",
    }


if __name__ == "__main__":
    result = build_example()
    destination = Path(__file__).with_suffix(".json")
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result["totals"], indent=2))
