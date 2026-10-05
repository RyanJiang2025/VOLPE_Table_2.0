"""Amenity assumptions for the VOLPE pro forma.

Synthetic working copy: typical example programs, dummy financial additions,
and zero-revenue public uses. See sources.md for overrides and baseline notes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

if __package__:
    from .assumptions import (
        DUMMY_HOUSING, DUMMY_COMMERCIAL,
        DUMMY_PUBLIC_UPKEEP_BY_GROUP, DUMMY_PUBLIC_UPKEEP_BY_USE,
        FAR_BONUS_SCALE, FAR_BONUS_REFERENCE_AREA_SQFT, FAR_BONUS_NOI_PER_SQFT_SCALE,
    )
else:
    from assumptions import (
        DUMMY_HOUSING, DUMMY_COMMERCIAL,
        DUMMY_PUBLIC_UPKEEP_BY_GROUP, DUMMY_PUBLIC_UPKEEP_BY_USE,
        FAR_BONUS_SCALE, FAR_BONUS_REFERENCE_AREA_SQFT, FAR_BONUS_NOI_PER_SQFT_SCALE,
    )

if __package__:
    from .assumptions import (
        multifamily_rent_per_sqft_yearly,
        office_rent_per_sqft_yearly,
        retail_rent_per_sqft,
        government_rent_per_sqft_yearly,
        office_opex_percent,
        retail_opex_percent,
        residential_opex_percent,
        government_opex_percent,
        PLINTH_ONLY_LAND_COST_PER_SQFT,
        SOFT_COST_FRACTION,
        TOWER_COST_MULTIPLIER,
        TOWER_PERMITTED_LAND_COST_PER_SQFT,
    )
else:
    from assumptions import (
        multifamily_rent_per_sqft_yearly,
        office_rent_per_sqft_yearly,
        retail_rent_per_sqft,
        government_rent_per_sqft_yearly,
        office_opex_percent,
        retail_opex_percent,
        residential_opex_percent,
        government_opex_percent,
        PLINTH_ONLY_LAND_COST_PER_SQFT,
        SOFT_COST_FRACTION,
        TOWER_COST_MULTIPLIER,
        TOWER_PERMITTED_LAND_COST_PER_SQFT,
    )


# Shared underwriting assumptions. Update one row to update every amenity
# assigned to that financial group.
_financial_groups = [
    "civic", "education", "school", "higher_education_career_training",
    "grocery", "healthcare", "hospital", "leisure_indoor", "leisure_outdoor",
    "shopping", "office", "lab", "general_multifamily",
    "mid_career_multifamily", "senior_multifamily", "attainable_multifamily",
    "luxury_multifamily", "supermarket", "food_retail", "clinic", "pharmacy",
    "food_drink", "fitness", "cultural_venue", "park", "playground",
    "outdoor_sports",
]
financial_assumptions = pd.DataFrame(
    {
        "financial_group": _financial_groups,
        "construction_cost_per_sqft": [0.0] * len(_financial_groups),
        "rent_per_sqft_yearly": [0.0] * len(_financial_groups),
        "upkeep_per_sqft_yearly": [0.0] * len(_financial_groups),
    }
)

financial_assumptions.loc[
    financial_assumptions["financial_group"] == "office", "rent_per_sqft_yearly"
] = office_rent_per_sqft_yearly

_retail_groups = ("shopping", "grocery", "supermarket", "food_retail", "pharmacy")
financial_assumptions.loc[
    financial_assumptions["financial_group"].isin(_retail_groups),
    "rent_per_sqft_yearly",
] = retail_rent_per_sqft

_multifamily_groups = (
    "general_multifamily", "mid_career_multifamily", "senior_multifamily",
    "attainable_multifamily", "luxury_multifamily",
)
financial_assumptions.loc[
    financial_assumptions["financial_group"].isin(_multifamily_groups),
    "rent_per_sqft_yearly",
] = multifamily_rent_per_sqft_yearly

# Map operating allowances independently of construction-cost categories.
_opex_percent_by_group = {
    "office": office_opex_percent,
    **dict.fromkeys(
        _retail_groups,
        retail_opex_percent,
    ),
    **dict.fromkeys(
        _multifamily_groups,
        residential_opex_percent,
    ),
}
financial_assumptions["upkeep_fraction_of_rent"] = (
    financial_assumptions["financial_group"].map(_opex_percent_by_group) / 100
)
_opex_mask = financial_assumptions["upkeep_fraction_of_rent"].notna()
financial_assumptions.loc[_opex_mask, "upkeep_per_sqft_yearly"] = (
    financial_assumptions.loc[_opex_mask, "rent_per_sqft_yearly"]
    * financial_assumptions.loc[_opex_mask, "upkeep_fraction_of_rent"]
)

# Fill synthetic rates before attaching them to either catalog. Public upkeep
# is a direct area allowance, so a percentage of zero revenue is inapplicable.
for _group, (_unit_sqft, _annual_rent, _opex_percent) in DUMMY_HOUSING.items():
    _mask = financial_assumptions["financial_group"] == _group
    financial_assumptions.loc[_mask, "rent_per_sqft_yearly"] = _annual_rent / _unit_sqft
    financial_assumptions.loc[_mask, "upkeep_fraction_of_rent"] = _opex_percent / 100
    financial_assumptions.loc[_mask, "upkeep_per_sqft_yearly"] = (
        _annual_rent / _unit_sqft * _opex_percent / 100
    )
for _group, (_rent, _opex_percent) in DUMMY_COMMERCIAL.items():
    _mask = financial_assumptions["financial_group"] == _group
    financial_assumptions.loc[_mask, "rent_per_sqft_yearly"] = _rent
    financial_assumptions.loc[_mask, "upkeep_fraction_of_rent"] = _opex_percent / 100
    financial_assumptions.loc[_mask, "upkeep_per_sqft_yearly"] = _rent * _opex_percent / 100
for _group, _upkeep in DUMMY_PUBLIC_UPKEEP_BY_GROUP.items():
    _mask = financial_assumptions["financial_group"] == _group
    financial_assumptions.loc[_mask, "rent_per_sqft_yearly"] = 0.0
    financial_assumptions.loc[_mask, "upkeep_fraction_of_rent"] = float("nan")
    financial_assumptions.loc[_mask, "upkeep_per_sqft_yearly"] = _upkeep

# Apply direct mappings and synthetic estimates from the copied Boston table. The table
# retains hard and soft costs separately; this legacy field uses their sum.
_cost_data = json.loads(
    (Path(__file__).with_name("boston_construction_costs.json")).read_text(encoding="utf-8")
)
_cost_rows = {row["type"]: row for row in _cost_data["rows"]}
_hard_cost_by_group = {
    group: _cost_rows[cost_type]["hard_cost_high_per_sqft"]
    for group, cost_type in _cost_data["financial_group_mapping"].items()
}
for _group, _cost_types in _cost_data["financial_group_blends"].items():
    _hard_cost_by_group[_group] = sum(
        _cost_rows[cost_type]["hard_cost_high_per_sqft"] for cost_type in _cost_types
    ) / len(_cost_types)
_hard_cost_by_group.update(_cost_data["estimated_hard_cost_per_sqft"])
financial_assumptions["tower_allowed"] = ~financial_assumptions["financial_group"].isin(
    _cost_data["outdoor_financial_groups"]
)
for _form in ("plinth", "tower"):
    for _part in ("hard", "soft", "total"):
        financial_assumptions[f"{_form}_{_part}_cost_per_sqft"] = 0.0
# Preserve these fields for existing consumers; they represent plinth rates.
financial_assumptions["construction_hard_cost_per_sqft"] = 0.0
financial_assumptions["construction_soft_cost_per_sqft"] = 0.0
for _group, _base_hard in _hard_cost_by_group.items():
    _mask = financial_assumptions["financial_group"] == _group
    for _form, _multiplier in (("plinth", 1.0), ("tower", TOWER_COST_MULTIPLIER)):
        _hard = _base_hard * _multiplier
        _soft = _hard * SOFT_COST_FRACTION
        financial_assumptions.loc[_mask, f"{_form}_hard_cost_per_sqft"] = _hard
        financial_assumptions.loc[_mask, f"{_form}_soft_cost_per_sqft"] = _soft
        financial_assumptions.loc[_mask, f"{_form}_total_cost_per_sqft"] = _hard + _soft
    financial_assumptions.loc[_mask, "construction_hard_cost_per_sqft"] = _base_hard
    financial_assumptions.loc[_mask, "construction_soft_cost_per_sqft"] = _base_hard * SOFT_COST_FRACTION
    financial_assumptions.loc[_mask, "construction_cost_per_sqft"] = _base_hard * (1 + SOFT_COST_FRACTION)


def construction_cost_for_area(
    financial_group: str, plinth_sqft: float = 0.0, tower_sqft: float = 0.0
) -> float:
    """Price separately allocated plinth and tower area, including soft costs."""
    if any(not math.isfinite(area) or area < 0 for area in (plinth_sqft, tower_sqft)):
        raise ValueError("plinth_sqft and tower_sqft must be finite and nonnegative")
    matching = financial_assumptions.set_index("financial_group")
    if financial_group not in matching.index:
        raise ValueError(f"unknown financial group: {financial_group!r}")
    rates = matching.loc[financial_group]
    if (plinth_sqft or tower_sqft) and not rates["plinth_total_cost_per_sqft"]:
        raise ValueError(f"construction cost not yet set for {financial_group!r}")
    if tower_sqft and not rates["tower_allowed"]:
        raise ValueError(f"tower area is not allowed for {financial_group!r}")
    return (
        plinth_sqft * rates["plinth_total_cost_per_sqft"]
        + tower_sqft * rates["tower_total_cost_per_sqft"]
    )


def land_cost_for_parcel(parcel_land_sqft: float, zoning_regime: str) -> float:
    """Price a whole parcel once using its permitted zoning regime."""
    if not math.isfinite(parcel_land_sqft) or parcel_land_sqft < 0:
        raise ValueError("parcel_land_sqft must be finite and nonnegative")
    rates = {
        "plinth_only": PLINTH_ONLY_LAND_COST_PER_SQFT,
        "tower_permitted": TOWER_PERMITTED_LAND_COST_PER_SQFT,
    }
    if zoning_regime not in rates:
        raise ValueError(f"unknown zoning regime: {zoning_regime!r}")
    return parcel_land_sqft * rates[zoning_regime]


# Column-oriented data from the normalized POI amenity taxonomy.
poi_amenity_type_data = {
    'amenity_type': ['accountant', 'acting_school', 'adoption_agency', 'advertising_agency', 'architect', 'association', 'bakery', 'bank', 'bar', 'barber', 'butcher', 'cafe', 'Charlie Company', 'childcare', 'cinema', 'clinic', 'clothes', 'clothes;toys', 'clothes;toys;books;games', 'college', 'commercial', 'community_centre', 'company', 'construction', 'consulting', 'convenience', 'coworking', 'dentist', 'department_store', 'design', 'digital_media', 'diplomatic', 'doctors', 'educational_institution', 'electronics', 'employment_agency', 'energy_supplier', 'engineer', 'estate_agent', 'fast_food', 'financial', 'financial_advisor', 'fire_department', 'fitness_centre', 'foundation', 'gift', 'government', 'graphic_design', 'greengrocer', 'guide', 'harbour_master', 'healthcare', 'hospital', 'insurance', 'investment', 'it', 'jewelry', 'lawyer', 'library', 'library_dropoff', 'mall', 'marketplace', 'medical', 'mortgage', 'moving_company', 'museum', 'newspaper', 'ngo', 'Nonprofit', 'park', 'peak', 'pharmacy', 'pitch', 'place_of_worship', 'playground', 'playground;park', 'post_office', 'property_management', 'psychic', 'pub', 'public_bookcase', 'rectory', 'religion', 'research', 'restaurant', 'school', 'shoes', 'sports', 'sports_centre', 'startup incubator', 'supermarket', 'tax_advisor', 'telecommunication', 'theatre', 'therapist', 'towing', 'townhall', 'travel_agent', 'tutoring', 'union', 'university', 'vacant', 'venture_capital', 'water_utility', 'general_office', 'youth_services'],
    'broad_amenity_category': ['work', 'work', 'work', 'work', 'work', 'work', 'grocery', 'civic', 'leisure_indoor', 'leisure_indoor', 'grocery', 'leisure_indoor', 'work', 'education', 'leisure_indoor', 'healthcare', 'shopping', 'shopping', 'shopping', 'education', 'work', 'civic', 'work', 'work', 'work', 'grocery', 'work', 'healthcare', 'shopping', 'work', 'work', 'work', 'healthcare', 'work', 'shopping', 'work', 'work', 'work', 'work', 'leisure_indoor', 'work', 'work', 'work', 'leisure_indoor', 'work', 'shopping', 'work', 'work', 'grocery', 'work', 'work', 'work', 'healthcare', 'work', 'work', 'work', 'shopping', 'work', 'education', 'education', 'shopping', 'grocery', 'work', 'work', 'work', 'leisure_indoor', 'work', 'work', 'work', 'leisure_outdoor', 'leisure_outdoor', 'healthcare', 'leisure_outdoor', 'civic', 'leisure_outdoor', 'leisure_outdoor', 'civic', 'work', 'work', 'leisure_indoor', 'leisure_indoor', 'work', 'work', 'work', 'leisure_indoor', 'education', 'shopping', 'shopping', 'leisure_indoor', 'work', 'grocery', 'work', 'work', 'leisure_indoor', 'work', 'work', 'civic', 'work', 'work', 'work', 'education; work', 'work', 'work', 'work', 'work', 'work'],
    'financial_group': ['office', 'office', 'office', 'office', 'office', 'office', 'grocery', 'civic', 'leisure_indoor', 'leisure_indoor', 'grocery', 'leisure_indoor', 'office', 'education', 'leisure_indoor', 'healthcare', 'shopping', 'shopping', 'shopping', 'education', 'office', 'civic', 'office', 'office', 'office', 'grocery', 'office', 'healthcare', 'shopping', 'office', 'office', 'office', 'healthcare', 'office', 'shopping', 'office', 'office', 'office', 'office', 'leisure_indoor', 'office', 'office', 'office', 'leisure_indoor', 'office', 'shopping', 'office', 'office', 'grocery', 'office', 'office', 'office', 'healthcare', 'office', 'office', 'office', 'shopping', 'office', 'education', 'education', 'shopping', 'grocery', 'office', 'office', 'office', 'leisure_indoor', 'office', 'office', 'office', 'leisure_outdoor', 'leisure_outdoor', 'healthcare', 'leisure_outdoor', 'civic', 'leisure_outdoor', 'leisure_outdoor', 'civic', 'office', 'office', 'leisure_indoor', 'leisure_indoor', 'office', 'office', 'lab', 'leisure_indoor', 'education', 'shopping', 'shopping', 'leisure_indoor', 'office', 'grocery', 'office', 'office', 'leisure_indoor', 'office', 'office', 'civic', 'office', 'office', 'office', 'education', 'office', 'office', 'office', 'office', 'office'],
    'square_footage': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    'ground_level': [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False],
    'FAR_Bonus': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
}


# Residential uses are manually defined pro forma archetypes rather than POI
# types sourced from raw_amenity_pref_order.json.
residential_archetype_data = {
    "amenity_type": [
        "general_multifamily",
        "mid_career_multifamily",
        "senior_multifamily",
        "attainable_multifamily",
        "luxury_multifamily",
    ],
    "broad_amenity_category": ["residential"] * 5,
    "financial_group": [
        "general_multifamily",
        "mid_career_multifamily",
        "senior_multifamily",
        "attainable_multifamily",
        "luxury_multifamily",
    ],
    "square_footage": [0] * 5,
    "ground_level": [False] * 5,
    "FAR_Bonus": [0] * 5,
}

for column, values in residential_archetype_data.items():
    poi_amenity_type_data[column].extend(values)

# The detailed reference catalog retains generic POI types but assigns
# specific costs where a POI is unambiguous.
for _amenity, _group in (("hospital", "hospital"), ("school", "school"), ("university", "higher_education_career_training")):
    _index = poi_amenity_type_data["amenity_type"].index(_amenity)
    poi_amenity_type_data["financial_group"][_index] = _group


def _apply_financial_assumptions(catalog: pd.DataFrame) -> pd.DataFrame:
    """Attach shared underwriting assumptions and calculated annual values."""
    catalog = catalog.copy()
    catalog = catalog.merge(
        financial_assumptions,
        on="financial_group",
        how="left",
        validate="many_to_one",
    )
    # Civic also contains banks and other nongovernment uses; assign government
    # rent and expenses by amenity instead of applying them to the entire civic group.
    if "amenity_type" in catalog:
        _public_mask = catalog["amenity_type"].isin(DUMMY_PUBLIC_UPKEEP_BY_USE)
        catalog.loc[_public_mask, "rent_per_sqft_yearly"] = 0.0
        catalog.loc[_public_mask, "upkeep_fraction_of_rent"] = float("nan")
        catalog.loc[_public_mask, "upkeep_per_sqft_yearly"] = (
            catalog.loc[_public_mask, "amenity_type"].map(DUMMY_PUBLIC_UPKEEP_BY_USE)
        )
        _bank_mask = catalog["amenity_type"].isin(("bank", "bank_financial_services"))
        catalog.loc[_bank_mask, "rent_per_sqft_yearly"] = retail_rent_per_sqft
        catalog.loc[_bank_mask, "upkeep_fraction_of_rent"] = retail_opex_percent / 100
    # Recalculate percentage-based upkeep from the current rent assumptions.
    _percentage_mask = catalog["upkeep_fraction_of_rent"].notna()
    catalog.loc[_percentage_mask, "upkeep_per_sqft_yearly"] = (
        catalog.loc[_percentage_mask, "rent_per_sqft_yearly"]
        * catalog.loc[_percentage_mask, "upkeep_fraction_of_rent"]
    )
    catalog["construction_cost"] = (
        catalog["construction_cost_per_sqft"] * catalog["square_footage"]
    )
    catalog["rent_yearly"] = (
        catalog["rent_per_sqft_yearly"] * catalog["square_footage"]
    )
    catalog["upkeep_yearly"] = (
        catalog["upkeep_per_sqft_yearly"] * catalog["square_footage"]
    )
    catalog["NOI_yearly"] = catalog["rent_yearly"] - catalog["upkeep_yearly"]
    # Annual unlevered operating yield; construction_cost includes soft costs.
    # Land and FAR benefits are excluded. Zero-cost/unallocated programs have
    # no defined yield, rather than a misleading zero return.
    catalog["yield_on_cost"] = catalog["NOI_yearly"] / catalog[
        "construction_cost"
    ].where(catalog["construction_cost"] > 0)
    return catalog


# Full 111-row reference catalog: 106 normalized POI types plus five manually
# defined residential archetypes. Keep this for traceability and future mapping
# work; it is intentionally not the optimizer's active choice set.
detailed_buildable_use_catalog = _apply_financial_assumptions(
    pd.DataFrame(poi_amenity_type_data)
)


# Active demo choice set for the development optimizer. Each row is a specific
# buildable use (rather than merely a voting category), so a building program
# can contain, for example, a supermarket and a barber as separate uses.
# use_family is the coarser category that will eventually receive synthpop
# support scores and dynamically updated FAR bonuses.
_demo_rows = json.loads(
    Path(__file__).with_name("demo_buildable_use_data.json").read_text(encoding="utf-8")
)["amenities"]
demo_buildable_use_data = {
    key: [row[key] for row in _demo_rows]
    for key in (
        "amenity_type", "broad_amenity_category", "use_family",
        "financial_group", "program_unit", "square_footage",
        "default_unit_sqft", "minimum_program_sqft", "maximum_program_sqft",
        "ground_level", "FAR_Bonus",
    )
}

# This dummy catalog uses typical example program areas and synthetic rates.
# Public uses have maintenance but no rent.
buildable_use_catalog = _apply_financial_assumptions(
    pd.DataFrame(demo_buildable_use_data)
)


def far_bonus_for_use(preference_weight: float, noi_yearly: float,
                      reference_weight: float, square_footage: float) -> float:
    """Scale FAR with program area and demand, reducing it with NOI per sq ft.

    The reference weight is fixed to the largest weight in the copied snapshot.
    Holding demand and NOI per sq ft fixed, bonus is proportional to program area.
    There is no minimum eligibility area; zero area earns zero bonus.
    """
    if not all(math.isfinite(value) for value in (
        preference_weight, noi_yearly, reference_weight, square_footage,
        FAR_BONUS_SCALE, FAR_BONUS_REFERENCE_AREA_SQFT, FAR_BONUS_NOI_PER_SQFT_SCALE,
    )):
        raise ValueError("FAR bonus inputs must be finite")
    if reference_weight <= 0 or not 0 <= preference_weight <= reference_weight:
        raise ValueError("preference weight must be between zero and the reference weight")
    if square_footage < 0:
        raise ValueError("Program area must be nonnegative")
    if min(FAR_BONUS_SCALE, FAR_BONUS_REFERENCE_AREA_SQFT, FAR_BONUS_NOI_PER_SQFT_SCALE) <= 0:
        raise ValueError("FAR bonus calibration values must be positive")
    if square_footage == 0:
        return 0.0
    # Normalize economics independently of size to avoid penalizing large profitable uses.
    scaled_noi = (noi_yearly / square_footage) / FAR_BONUS_NOI_PER_SQFT_SCALE
    if scaled_noi >= 0:
        decay = math.exp(-scaled_noi)
        subsidy_factor = decay / (1 + decay)
    else:
        subsidy_factor = 1 / (1 + math.exp(scaled_noi))
    return (FAR_BONUS_SCALE * (preference_weight / reference_weight)
            * (square_footage / FAR_BONUS_REFERENCE_AREA_SQFT) * subsidy_factor)


_vote_pairs = json.loads(
    Path(__file__).with_name("amenity_pref_order_votes.json").read_text(encoding="utf-8")
)
_preference_weights = dict(_vote_pairs)
if len(_preference_weights) != len(_vote_pairs):
    raise ValueError("Duplicate amenity preference identifiers")
if set(_preference_weights) != set(buildable_use_catalog["amenity_type"]):
    raise ValueError("Preference snapshot must match the active dummy catalog")
_reference_weight = max(_preference_weights.values())
buildable_use_catalog["amenity_pref_order"] = (
    buildable_use_catalog["amenity_type"].map(_preference_weights)
)
buildable_use_catalog["FAR_Bonus"] = [
    far_bonus_for_use(row.amenity_pref_order, row.NOI_yearly, _reference_weight,
                      row.square_footage)
    for row in buildable_use_catalog.itertuples()
]

