"""Build the active choice set; the larger reference taxonomy is loaded on request."""
from dataclasses import replace
import json
import math

from .config import DATA_ROOT, load_config, thaw
from .finance import financial_rates, operating_rates
from .models import Program, Scenario


def _attach_rates(rows, config):
    rates = financial_rates(config)
    uses = {r["amenity_type"]: r for r in config.datasets["catalog"]["amenities"]}
    exceptions = config.datasets["economics"]["use_overrides"]
    attached = []
    for source in rows:
        row = dict(source)
        row.update(rates[row["financial_group"]])
        if row["amenity_type"] in exceptions:
            rent, upkeep, fraction = operating_rates(exceptions[row["amenity_type"]], uses)
            row.update(rent_per_sqft_yearly=rent, upkeep_per_sqft_yearly=upkeep,
                       upkeep_fraction_of_rent=fraction)
        area = row["square_footage"]
        row["construction_cost"] = row["construction_cost_per_sqft"] * area
        row["rent_yearly"] = row["rent_per_sqft_yearly"] * area
        row["upkeep_yearly"] = row["upkeep_per_sqft_yearly"] * area
        row["NOI_yearly"] = row["rent_yearly"] - row["upkeep_yearly"]
        row["yield_on_cost"] = row["NOI_yearly"] / row["construction_cost"] if row["construction_cost"] else None
        attached.append(row)
    return attached


def build_catalog(config=None, scenario=None):
    import pandas as pd
    from .bonuses import far_bonus_for_use
    config = config or load_config()
    scenario = scenario or Scenario.from_config(config)
    selection = config.data["selection"]
    rows = thaw(config.datasets["catalog"]["amenities"])
    for row in rows:
        row["square_footage"] = row.pop("example_area_sqft")
        if row["amenity_type"] in selection["floor_limit_exemptions"]:
            row["maximum_program_sqft"] = scenario.podium_capacity + scenario.maximum_tower_capacity
        elif row["program_unit"] == "dwelling_unit":
            row["minimum_program_sqft"] = max(row["minimum_program_sqft"],
                selection["minimum_housing_units"] * row["default_unit_sqft"])
        else:
            cap = (scenario.open_space if row["outdoor"] else scenario.podium_footprint if row["ground_level"]
                   else scenario.tower_footprint * scenario.max_nonhousing_stories)
            row["maximum_program_sqft"] = min(row["maximum_program_sqft"], cap)
    # Examples are descriptive, not constraints. Small scenarios may exclude a use.
    rows = _attach_rates([r for r in rows if r["minimum_program_sqft"] <= r["maximum_program_sqft"]], config)
    weights = config.weights
    reference = max(weights.values())  # Includes inactive uses deliberately.
    for row in rows:
        row["amenity_pref_order"] = weights[row["amenity_type"]]
        row["demand_FAR_Bonus"] = far_bonus_for_use(
            row["amenity_pref_order"], row["NOI_yearly"], reference, row["square_footage"],
            eligible=row["bonus_eligible"], legacy=config.data["bonuses"]["legacy"])
        row["footprint_refund_FAR"] = (row["square_footage"] / scenario.tower_footprint
                                      if row["bonus_eligible"] and not row["outdoor"] else 0.0)
        row["FAR_Bonus"] = row["demand_FAR_Bonus"] + row["footprint_refund_FAR"]
        row["is_for_profit_use"] = not row["bonus_eligible"]
    return pd.DataFrame(rows)


def catalog_programs(tower_footprint=None, *, config=None, scenario=None):
    config = config or load_config()
    scenario = scenario or Scenario.from_config(config)
    if tower_footprint is not None:
        if not math.isfinite(tower_footprint) or tower_footprint <= 0:
            raise ValueError("Tower footprint must be finite and positive")
        scenario = replace(scenario, tower_footprint=tower_footprint)
    catalog = build_catalog(config, scenario)
    return [Program(
        name=r.amenity_type, unit_sqft=float(r.default_unit_sqft),
        minimum_sqft=float(r.minimum_program_sqft), maximum_sqft=float(r.maximum_program_sqft),
        noi_per_sqft=float(r.rent_per_sqft_yearly - r.upkeep_per_sqft_yearly),
        podium_cost_per_sqft=float(r.plinth_total_cost_per_sqft),
        tower_cost_per_sqft=float(r.tower_total_cost_per_sqft),
        bonus_far_per_unit=float(r.demand_FAR_Bonus * r.default_unit_sqft / r.square_footage
            + (r.default_unit_sqft / scenario.tower_footprint if r.bonus_eligible and not r.outdoor else 0.0)),
        continuous=r.program_unit == "square_foot", housing=r.program_unit == "dwelling_unit",
        outdoor=bool(r.outdoor), ground_level=bool(r.ground_level), tower_allowed=bool(r.tower_allowed),
        program_unit=r.program_unit,
        unrestricted_nonhousing=r.amenity_type in config.data["selection"]["floor_limit_exemptions"],
        bonus_block_units=config.data["bonuses"]["housing_block_units"],
    ) for r in catalog.itertuples()]


def reference_catalog(config=None, path=None):
    """Reference only: avoid building 111 unused rows during normal optimization."""
    import pandas as pd
    config = config or load_config()
    data = json.loads((path or DATA_ROOT / "reference" / "poi_taxonomy.json").read_text(encoding="utf-8"))
    rows = [dict(row, square_footage=0, FAR_Bonus=0) for row in data["amenities"]]
    return pd.DataFrame(_attach_rates(rows, config))
