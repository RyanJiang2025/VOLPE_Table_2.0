"""
VOLPE 2.0 — Simplest possible three-state pro forma prototype
================================================================

Purpose: get the STRUCTURE right (parcel -> scenario -> use mix -> profit ->
construction likelihood) with placeholder numbers. Every assumption tagged
PLACEHOLDER is made up and safe to overwrite once real market data lands
(CRE / CoStar / JLL-CBRE-Cushman reports / RSMeans).

Deliberately excluded from this version (see project on-horizon list):
  - Dynamic zoning / FAR bonus mechanic (amenities, incentive layer)
  - Build -> vote -> build sequencing (this models ONE static snapshot)
  - Land cost (excluded from the model per project standard)
  - Phasing, debt/leverage, depreciation, IRR

Two agency modes are both supported, since the demo needs both:
  - "developer": optimizer searches over use mix, picks the max-profit one
  - "puppet":    use mix is handed in externally; model only prices it out
"""

import math

# ----------------------------------------------------------------------
# 1. PARCEL GEOMETRY (from Matti's 2026-09-08 image — real data)
# ----------------------------------------------------------------------

SQM_PER_GRID_SQUARE = 25 * 25          # 625 sqm per grid square
SQFT_PER_SQM = 10.7639

PARCELS = {
    "Red":    22,
    "Yellow": 22,
    "Green":  24,
    "Blue":   24,
    "Purple": 20,
}

def parcel_footprint_sqft(n_squares: int) -> float:
    return n_squares * SQM_PER_GRID_SQUARE * SQFT_PER_SQM


# ----------------------------------------------------------------------
# 2. BUILDING FORM ASSUMPTIONS — ALL PLACEHOLDER
# ----------------------------------------------------------------------
# Podium and tower are each just: (number of floors) x (floor-plate
# efficiency, i.e. what fraction of the parcel footprint each floor uses).
# These stand in for the "plot geometry -> buildable sqft" step until
# Matti/Yasushi confirm actual plinth height / tower floorplate / max height.

FORM = {
    "podium_floors": 4,             # PLACEHOLDER
    "podium_efficiency": 0.85,      # PLACEHOLDER — coverage/efficiency ratio
    "tower_floors": 20,             # PLACEHOLDER
    "tower_efficiency": 0.55,       # PLACEHOLDER — slimmer floor plate than podium
}

def buildable_sqft(footprint_sqft: float, scenario: str) -> dict:
    """Returns {'podium': sqft, 'tower': sqft} buildable area for a scenario."""
    if scenario == "nothing":
        return {"podium": 0.0, "tower": 0.0}
    podium_sqft = footprint_sqft * FORM["podium_efficiency"] * FORM["podium_floors"]
    if scenario == "plinth":
        return {"podium": podium_sqft, "tower": 0.0}
    if scenario == "plinth_tower":
        tower_sqft = footprint_sqft * FORM["tower_efficiency"] * FORM["tower_floors"]
        return {"podium": podium_sqft, "tower": tower_sqft}
    raise ValueError(f"unknown scenario: {scenario}")


# ----------------------------------------------------------------------
# 3. USE-MIX OPTIONS — ALL PLACEHOLDER
# ----------------------------------------------------------------------
# Podium can be retail or office. Tower can be office or residential rental.
# (Article 14 ground-floor retail mandate is deliberately ignored in this
# v0 — that's a dynamic-zoning-layer concern, not this snapshot's.)

PODIUM_USES = ["retail", "office"]
TOWER_USES = ["office", "residential"]

# $/sqft/year market rent — PLACEHOLDER, order-of-magnitude Kendall-ish
RENT_PER_SQFT_YR = {
    "retail": 45,
    "office": 65,
    "residential": 55,   # residential quoted as if converted to $/sqft/yr equiv.
}

# Hard construction cost, $/sqft — PLACEHOLDER, podium vs. tower differ
# (tower construction is more expensive per sqft: structure, MEP, elevators)
HARD_COST_PER_SQFT = {
    ("podium", "retail"): 350,
    ("podium", "office"): 380,
    ("tower", "office"): 480,
    ("tower", "residential"): 460,
}

SOFT_COST_PCT = 0.25          # PLACEHOLDER — % of hard cost (design, fees, contingency)
VACANCY_PCT = 0.08            # PLACEHOLDER
OPEX_RATIO = 0.35             # PLACEHOLDER — % of effective gross income
CAP_RATE = 0.065              # PLACEHOLDER — stabilized exit cap rate
DEVELOPER_SPREAD = 0.015      # PLACEHOLDER — required yield-on-cost premium over cap rate
REQUIRED_YIELD = CAP_RATE + DEVELOPER_SPREAD

# S-curve steepness for construction-likelihood logistic (see step 6)
SCURVE_STEEPNESS = 40         # PLACEHOLDER — higher = sharper flip near threshold


# ----------------------------------------------------------------------
# 4. CORE PRO FORMA: given a scenario + a specific use mix, price it out
# ----------------------------------------------------------------------

def price_use_mix(footprint_sqft: float, scenario: str,
                   podium_use: str, tower_use: str) -> dict:
    sqft = buildable_sqft(footprint_sqft, scenario)

    hard_cost = 0.0
    revenue = 0.0

    if sqft["podium"] > 0:
        hard_cost += sqft["podium"] * HARD_COST_PER_SQFT[("podium", podium_use)]
        revenue += sqft["podium"] * RENT_PER_SQFT_YR[podium_use]

    if sqft["tower"] > 0:
        hard_cost += sqft["tower"] * HARD_COST_PER_SQFT[("tower", tower_use)]
        revenue += sqft["tower"] * RENT_PER_SQFT_YR[tower_use]

    total_cost = hard_cost * (1 + SOFT_COST_PCT)   # land cost excluded

    egi = revenue * (1 - VACANCY_PCT)
    noi = egi * (1 - OPEX_RATIO)

    if total_cost == 0:
        yield_on_cost = 0.0
        profit_margin = 0.0
    else:
        yield_on_cost = noi / total_cost
        profit_margin = yield_on_cost - REQUIRED_YIELD

    return {
        "podium_use": podium_use if sqft["podium"] > 0 else "-",
        "tower_use": tower_use if sqft["tower"] > 0 else "-",
        "podium_sqft": sqft["podium"],
        "tower_sqft": sqft["tower"],
        "total_cost": total_cost,
        "noi": noi,
        "yield_on_cost": yield_on_cost,
        "profit_margin": profit_margin,
    }


# ----------------------------------------------------------------------
# 5. AGENCY MODES
# ----------------------------------------------------------------------

def developer_mode(footprint_sqft: float, scenario: str) -> dict:
    """Optimizer: search over all use-mix combos, return the best one."""
    if scenario == "nothing":
        return price_use_mix(footprint_sqft, scenario, PODIUM_USES[0], TOWER_USES[0])

    best = None
    for p_use in PODIUM_USES:
        for t_use in TOWER_USES:
            result = price_use_mix(footprint_sqft, scenario, p_use, t_use)
            if best is None or result["profit_margin"] > best["profit_margin"]:
                best = result
    return best


def puppet_mode(footprint_sqft: float, scenario: str,
                 podium_use: str, tower_use: str) -> dict:
    """User has already picked the use mix; just price it out."""
    return price_use_mix(footprint_sqft, scenario, podium_use, tower_use)


# ----------------------------------------------------------------------
# 6. CONSTRUCTION LIKELIHOOD — logistic S-curve on profit margin
# ----------------------------------------------------------------------

def construction_likelihood(profit_margin: float) -> float:
    """profit_margin == 0 -> 50% likely; scales with SCURVE_STEEPNESS."""
    return 1 / (1 + math.exp(-SCURVE_STEEPNESS * profit_margin))


# ----------------------------------------------------------------------
# 7. RUN: developer-agency mode across all 5 parcels x 3 scenarios
# ----------------------------------------------------------------------

def run_all():
    scenarios = ["nothing", "plinth", "plinth_tower"]
    rows = []
    for name, n_squares in PARCELS.items():
        footprint = parcel_footprint_sqft(n_squares)
        for scenario in scenarios:
            result = developer_mode(footprint, scenario)
            likelihood = construction_likelihood(result["profit_margin"])
            rows.append({
                "parcel": name,
                "scenario": scenario,
                **result,
                "likelihood": likelihood,
            })
    return rows


def print_table(rows):
    header = (f"{'Parcel':<8}{'Scenario':<14}{'Podium':<9}{'Tower':<13}"
              f"{'Cost ($M)':<11}{'NOI ($k)':<11}{'YoC':<8}{'Margin':<9}{'P(build)':<9}")
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['parcel']:<8}{r['scenario']:<14}{r['podium_use']:<9}{r['tower_use']:<13}"
              f"{r['total_cost']/1e6:<11.2f}{r['noi']/1e3:<11.1f}"
              f"{r['yield_on_cost']*100:<7.2f}%{r['profit_margin']*100:<8.2f}%{r['likelihood']*100:<8.1f}%")


if __name__ == "__main__":
    rows = run_all()
    print_table(rows)

    # Example of puppet mode: user has picked "office everywhere" on the
    # Green parcel at plinth+tower, model just tells them what that's worth.
    print("\nPuppet-mode example — Green, plinth+tower, forced office/office:")
    footprint = parcel_footprint_sqft(PARCELS["Green"])
    puppet_result = puppet_mode(footprint, "plinth_tower", "office", "office")
    likelihood = construction_likelihood(puppet_result["profit_margin"])
    print(f"  Cost: ${puppet_result['total_cost']/1e6:.2f}M  "
          f"NOI: ${puppet_result['noi']/1e3:.1f}k  "
          f"YoC: {puppet_result['yield_on_cost']*100:.2f}%  "
          f"Margin: {puppet_result['profit_margin']*100:.2f}%  "
          f"P(build): {likelihood*100:.1f}%")
