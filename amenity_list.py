"""Amenity assumptions for the VOLPE pro forma.

All financial and physical assumptions are placeholders until sourced data is available.
"""
from __future__ import annotations

import pandas as pd


# Shared underwriting assumptions. Update one row to update every amenity
# assigned to that financial group.
amenity_financials = pd.DataFrame(
    {
        "financial_group": ['civic', 'education', 'grocery', 'healthcare', 'leisure_indoor', 'leisure_outdoor', 'shopping', 'office', 'lab'],
        "construction_cost_per_sqft": [0, 0, 0, 0, 0, 0, 0, 0, 0],
        "rent_per_sqft_yearly": [0, 0, 0, 0, 0, 0, 0, 0, 0],
        "upkeep_per_sqft_yearly": [0, 0, 0, 0, 0, 0, 0, 0, 0],
    }
)


# One list per amenity_list column; each position is one amenity type.
data = {
    'amenity_type': ['accountant', 'acting_school', 'adoption_agency', 'advertising_agency', 'architect', 'association', 'bakery', 'bank', 'bar', 'barber', 'butcher', 'cafe', 'Charlie Company', 'childcare', 'cinema', 'clinic', 'clothes', 'clothes;toys', 'clothes;toys;books;games', 'college', 'commercial', 'community_centre', 'company', 'construction', 'consulting', 'convenience', 'coworking', 'dentist', 'department_store', 'design', 'digital_media', 'diplomatic', 'doctors', 'educational_institution', 'electronics', 'employment_agency', 'energy_supplier', 'engineer', 'estate_agent', 'fast_food', 'financial', 'financial_advisor', 'fire_department', 'fitness_centre', 'foundation', 'gift', 'government', 'graphic_design', 'greengrocer', 'guide', 'harbour_master', 'healthcare', 'hospital', 'insurance', 'investment', 'it', 'jewelry', 'lawyer', 'library', 'library_dropoff', 'mall', 'marketplace', 'medical', 'mortgage', 'moving_company', 'museum', 'newspaper', 'ngo', 'Nonprofit', 'park', 'peak', 'pharmacy', 'pitch', 'place_of_worship', 'playground', 'playground;park', 'post_office', 'property_management', 'psychic', 'pub', 'public_bookcase', 'rectory', 'religion', 'research', 'restaurant', 'school', 'shoes', 'sports', 'sports_centre', 'startup incubator', 'supermarket', 'tax_advisor', 'telecommunication', 'theatre', 'therapist', 'towing', 'townhall', 'travel_agent', 'tutoring', 'union', 'university', 'vacant', 'venture_capital', 'water_utility', 'general_office', 'youth_services'],
    'broad_amenity_category': ['work', 'work', 'work', 'work', 'work', 'work', 'grocery', 'civic', 'leisure_indoor', 'leisure_indoor', 'grocery', 'leisure_indoor', 'work', 'education', 'leisure_indoor', 'healthcare', 'shopping', 'shopping', 'shopping', 'education', 'work', 'civic', 'work', 'work', 'work', 'grocery', 'work', 'healthcare', 'shopping', 'work', 'work', 'work', 'healthcare', 'work', 'shopping', 'work', 'work', 'work', 'work', 'leisure_indoor', 'work', 'work', 'work', 'leisure_indoor', 'work', 'shopping', 'work', 'work', 'grocery', 'work', 'work', 'work', 'healthcare', 'work', 'work', 'work', 'shopping', 'work', 'education', 'education', 'shopping', 'grocery', 'work', 'work', 'work', 'leisure_indoor', 'work', 'work', 'work', 'leisure_outdoor', 'leisure_outdoor', 'healthcare', 'leisure_outdoor', 'civic', 'leisure_outdoor', 'leisure_outdoor', 'civic', 'work', 'work', 'leisure_indoor', 'leisure_indoor', 'work', 'work', 'work', 'leisure_indoor', 'education', 'shopping', 'shopping', 'leisure_indoor', 'work', 'grocery', 'work', 'work', 'leisure_indoor', 'work', 'work', 'civic', 'work', 'work', 'work', 'education; work', 'work', 'work', 'work', 'work', 'work'],
    'financial_group': ['office', 'office', 'office', 'office', 'office', 'office', 'grocery', 'civic', 'leisure_indoor', 'leisure_indoor', 'grocery', 'leisure_indoor', 'office', 'education', 'leisure_indoor', 'healthcare', 'shopping', 'shopping', 'shopping', 'education', 'office', 'civic', 'office', 'office', 'office', 'grocery', 'office', 'healthcare', 'shopping', 'office', 'office', 'office', 'healthcare', 'office', 'shopping', 'office', 'office', 'office', 'office', 'leisure_indoor', 'office', 'office', 'office', 'leisure_indoor', 'office', 'shopping', 'office', 'office', 'grocery', 'office', 'office', 'office', 'healthcare', 'office', 'office', 'office', 'shopping', 'office', 'education', 'education', 'shopping', 'grocery', 'office', 'office', 'office', 'leisure_indoor', 'office', 'office', 'office', 'leisure_outdoor', 'leisure_outdoor', 'healthcare', 'leisure_outdoor', 'civic', 'leisure_outdoor', 'leisure_outdoor', 'civic', 'office', 'office', 'leisure_indoor', 'leisure_indoor', 'office', 'office', 'lab', 'leisure_indoor', 'education', 'shopping', 'shopping', 'leisure_indoor', 'office', 'grocery', 'office', 'office', 'leisure_indoor', 'office', 'office', 'civic', 'office', 'office', 'office', 'education', 'office', 'office', 'office', 'office', 'office'],
    'square_footage': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    'ground_level': [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False],
    'FAR_Bonus': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
}

amenity_list = pd.DataFrame(data).merge(
    amenity_financials,
    on="financial_group",
    how="left",
    validate="many_to_one",
)
amenity_list["construction_cost"] = (
    amenity_list["construction_cost_per_sqft"] * amenity_list["square_footage"]
)
amenity_list["rent_yearly"] = (
    amenity_list["rent_per_sqft_yearly"] * amenity_list["square_footage"]
)
amenity_list["upkeep_yearly"] = (
    amenity_list["upkeep_per_sqft_yearly"] * amenity_list["square_footage"]
)
amenity_list["NOI_yearly"] = amenity_list["rent_yearly"] - amenity_list["upkeep_yearly"]

