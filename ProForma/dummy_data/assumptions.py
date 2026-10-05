"""Editable financial assumptions for the active VOLPE pro forma."""

# User-provided rent inputs. All rents are annual; hospitality RevPAR is daily.
# Office and retail rents are USD per square foot per year.
office_rent_per_sqft_yearly = 91.0
retail_rent_per_sqft = 27.20
# Multifamily rent is USD per unit per year.
multifamily_rent_per_unit = 4045.0
multifamily_rent_period = "annual"
# Conversion denominator only: converts per-unit rent to per-square-foot rent.
# This does not set a unit size or allocated area in the catalog; see sources.md.
multifamily_average_unit_sqft = 995.0
multifamily_rent_per_sqft_yearly = (
    multifamily_rent_per_unit / multifamily_average_unit_sqft
)
hospitality_revpar = 223.0  # USD per available room per day.

# User-provided operating expenses as percentages of annual rent (40 means 40%).
# Office applies regardless of wood-frame or steel construction.
office_opex_percent = 31.95
retail_opex_percent = 40.0
residential_opex_percent = 40.0
# Student housing and hotels are not yet represented in the amenity catalogs.
student_opex_percent = 40.0
hospitality_opex_percent = 67.0
# Government uses share the office rent and operating expense assumptions.
government_rent_per_sqft_yearly = office_rent_per_sqft_yearly
government_opex_percent = office_opex_percent

# Soft costs are calculated as a fraction of hard construction costs.
SOFT_COST_FRACTION = 0.30

# Tower construction costs this multiple of the same use built in the plinth.
TOWER_COST_MULTIPLIER = 1.75

# Land acquisition cost per square foot of parcel land, by zoning regime.
PLINTH_ONLY_LAND_COST_PER_SQFT = 450.0
TOWER_PERMITTED_LAND_COST_PER_SQFT = 1340.0

# Synthetic inputs for this folder only; these are not market observations.
# Housing annual rent retains the original annual-period convention.
# Values: (unit area in sq ft, annual rent per unit, operating expense percent).
DUMMY_HOUSING = {
    "general_multifamily": (995, 4045, 40),
    "mid_career_multifamily": (1100, 4600, 38),
    "senior_multifamily": (800, 3600, 45),
    "attainable_multifamily": (750, 2800, 42),
    "luxury_multifamily": (1250, 6500, 35),
}

# Additional commercial annual rent per sq ft and expense percent.
DUMMY_COMMERCIAL = {
    "lab": (110, 35),
    "healthcare": (60, 50),
    "hospital": (75, 60),
    "clinic": (55, 45),
    "leisure_indoor": (35, 45),
    "food_drink": (40, 45),
    "fitness": (32, 45),
}

# Public/community facilities have no rent. Maintenance is USD/sq ft/year,
# independent of revenue. Outdoor rates apply to improved site area.
# FAR benefits are calculated from preference weights and annual NOI.
DUMMY_PUBLIC_UPKEEP_BY_GROUP = {
    "civic": 12,
    "education": 15,
    "school": 15,
    "higher_education_career_training": 18,
    "cultural_venue": 18,
    "leisure_outdoor": 3,
    "park": 3,
    "playground": 5,
    "outdoor_sports": 4,
}

# Amenity-level exceptions to shared civic rates, including government uses.
DUMMY_PUBLIC_UPKEEP_BY_USE = {
    "library": 12,
    "community_centre": 12,
    "government_operations": 12,
    "place_of_worship": 8,
    "post_office": 10,
    "government": 12,
    "townhall": 12,
    "fire_department": 15,
    "diplomatic": 12,
    "harbour_master": 10,
}

# Adjustable dummy subsidy calibration, not zoning rules.
# Bonuses are absolute FAR increments, with no eligibility cutoff or per-use cap.
# Scale is the bonus coefficient for a reference-sized program. NOI is USD/sq ft/year.
FAR_BONUS_SCALE = 2.0
FAR_BONUS_REFERENCE_AREA_SQFT = 10_000.0
FAR_BONUS_NOI_PER_SQFT_SCALE = 100.0
