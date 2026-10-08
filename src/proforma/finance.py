"""Alternative financial measures using a shared development allocation."""
OBJECTIVES = ("annual-surplus", "development-profit")


def completed_value(annual_noi, capitalization_rate):
    # Negative NOI represents an ongoing maintenance liability, not free space.
    return annual_noi / capitalization_rate


def objective_contribution(objective, annual_noi, development_cost,
                           required_return, capitalization_rate):
    if objective == "annual-surplus":
        return annual_noi - required_return * development_cost
    if objective == "development-profit":
        return completed_value(annual_noi, capitalization_rate) - development_cost
    raise ValueError(f"Unknown objective: {objective}")


def financial_rates(config):
    """Resolve shared rates once; housing size is owned by the active catalog."""
    economics, costs = config.datasets["economics"], config.datasets["construction_costs"]
    uses = {row["amenity_type"]: row for row in config.datasets["catalog"]["amenities"]}
    source_costs = {row["type"]: row["hard_cost_high_per_sqft"] for row in costs["rows"]}
    hard_costs = {group: source_costs[cost_type] for group, cost_type in costs["financial_group_mapping"].items()}
    hard_costs.update({group: sum(source_costs[t] for t in blend) / len(blend)
                       for group, blend in costs["financial_group_blends"].items()})
    hard_costs.update(costs["estimated_hard_cost_per_sqft"])
    finance = config.data["finance"]
    result = {}
    for group, row in economics["financial_groups"].items():
        rent, upkeep, fraction = operating_rates(row, uses)
        hard = hard_costs[group]
        rate = {"financial_group": group, "rent_per_sqft_yearly": rent,
                "upkeep_per_sqft_yearly": upkeep, "upkeep_fraction_of_rent": fraction,
                "tower_allowed": group not in costs["outdoor_financial_groups"],
                "construction_cost_per_sqft": hard * (1 + finance["soft_cost_fraction"]),
                "construction_hard_cost_per_sqft": hard,
                "construction_soft_cost_per_sqft": hard * finance["soft_cost_fraction"]}
        for form, multiplier in (("plinth", 1.0), ("tower", finance["tower_cost_multiplier"])):
            base = hard * multiplier
            soft = base * finance["soft_cost_fraction"]
            rate.update({f"{form}_hard_cost_per_sqft": base, f"{form}_soft_cost_per_sqft": soft,
                         f"{form}_total_cost_per_sqft": base + soft})
        result[group] = rate
    return result


def operating_rates(row, uses):
    if "annual_rent_per_unit_usd" in row:
        rent = row["annual_rent_per_unit_usd"] / uses[row["unit_size_from_use"]]["default_unit_sqft"]
    else:
        rent = row["annual_rent_per_sqft_usd"]
    fraction = row.get("opex_fraction")
    upkeep = rent * fraction if fraction is not None else row["annual_maintenance_per_sqft_usd"]
    return rent, upkeep, fraction


def construction_cost_for_area(financial_group, plinth_sqft=0.0, tower_sqft=0.0, *, config=None):
    import math
    from .config import load_config
    if any(not math.isfinite(area) or area < 0 for area in (plinth_sqft, tower_sqft)):
        raise ValueError("Construction areas must be finite and nonnegative")
    rates = financial_rates(config or load_config())
    if financial_group not in rates:
        raise ValueError(f"Unknown financial group: {financial_group}")
    rate = rates[financial_group]
    if tower_sqft and not rate["tower_allowed"]:
        raise ValueError(f"Tower placement is not allowed: {financial_group}")
    return plinth_sqft * rate["plinth_total_cost_per_sqft"] + tower_sqft * rate["tower_total_cost_per_sqft"]


def land_cost_for_parcel(parcel_land_sqft, zoning_regime, *, config=None):
    import math
    from .config import load_config
    if not math.isfinite(parcel_land_sqft) or parcel_land_sqft < 0:
        raise ValueError("Parcel area must be finite and nonnegative")
    rates = (config or load_config()).datasets["economics"]["land_cost_per_parcel_sqft_usd"]
    if zoning_regime not in rates:
        raise ValueError(f"Unknown zoning regime: {zoning_regime}")
    return parcel_land_sqft * rates[zoning_regime]
