"""VOLPE 2.0 -- three-state, stabilized pro forma prototype.

This is a near-term demo artifact, not a full real-estate underwriting model.
It evaluates each parcel in one of three states: no build (``nothing``), a
podium only (``plinth``), or a podium plus tower (``plinth_tower``).

All market and construction values are deliberately provisional.  They are
centralized below so they can be replaced with sourced Boston/Cambridge data
without changing the pricing logic.  Land cost, parking, debt, phasing, DCF,
IRR, and dynamic-zoning/FAR sequencing are intentionally out of scope.
"""

from __future__ import annotations

import math
from itertools import product
from typing import Any


# ---------------------------------------------------------------------------
# 1. PARCEL GEOMETRY -- fixed site data
# ---------------------------------------------------------------------------

SQM_PER_GRID_SQUARE = 25 * 25
SQFT_PER_SQM = 10.7639

PARCELS = {
    "Red": 22,
    "Yellow": 22,
    "Green": 24,
    "Blue": 24,
    "Purple": 20,
}


def parcel_footprint_sqft(grid_squares: int) -> float:
    """Convert the CityScope grid-square count into parcel footprint area."""
    if grid_squares <= 0:
        raise ValueError("grid_squares must be positive")
    return grid_squares * SQM_PER_GRID_SQUARE * SQFT_PER_SQM


# ---------------------------------------------------------------------------
# 2. CONFIGURATION -- all financial values are placeholders
# ---------------------------------------------------------------------------

# The source/confidence metadata makes later substitution traceable without
# changing the calculation schema.
ASSUMPTION_METADATA = {
    "source": "PLACEHOLDER -- replace with published Boston/Cambridge market data",
    "confidence": "low",
}

FORM = {
    "podium_floors": 4,
    "podium_efficiency": 0.85,
    "tower_floors": 20,
    "tower_efficiency": 0.55,
}

PODIUM_USES = ("retail", "office")
TOWER_USES = ("office", "residential")

RENT_PER_SQFT_YR = {
    "retail": 45.0,
    "office": 65.0,
    "residential": 55.0,  # Annual $/sf equivalent for this prototype.
}

HARD_COST_PER_SQFT = {
    ("podium", "retail"): 350.0,
    ("podium", "office"): 380.0,
    ("tower", "office"): 480.0,
    ("tower", "residential"): 460.0,
}

SOFT_COST_PCT = 0.25
VACANCY_PCT = 0.08
OPEX_RATIO = 0.35
CAP_RATE = 0.065
DEVELOPER_SPREAD = 0.015
REQUIRED_YIELD = CAP_RATE + DEVELOPER_SPREAD
SCURVE_STEEPNESS = 40.0

SCENARIOS = ("nothing", "plinth", "plinth_tower")


def validate_assumptions() -> None:
    """Fail early when a configuration cannot describe a valid pro forma."""
    if not 0 <= SOFT_COST_PCT:
        raise ValueError("SOFT_COST_PCT cannot be negative")
    for name, value in {
        "VACANCY_PCT": VACANCY_PCT,
        "OPEX_RATIO": OPEX_RATIO,
        "CAP_RATE": CAP_RATE,
        "DEVELOPER_SPREAD": DEVELOPER_SPREAD,
    }.items():
        if not 0 <= value < 1:
            raise ValueError(f"{name} must be between 0 and 1")
    for name, value in FORM.items():
        if value <= 0:
            raise ValueError(f"FORM[{name!r}] must be positive")


# ---------------------------------------------------------------------------
# 3. BUILDING FORM
# ---------------------------------------------------------------------------

def buildable_sqft(footprint_sqft: float, scenario: str) -> dict[str, float]:
    """Return component areas for a supported parcel state."""
    if footprint_sqft <= 0:
        raise ValueError("footprint_sqft must be positive")
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario!r}; expected one of {SCENARIOS}")

    if scenario == "nothing":
        return {"podium": 0.0, "tower": 0.0}

    podium_sqft = footprint_sqft * FORM["podium_efficiency"] * FORM["podium_floors"]
    tower_sqft = 0.0
    if scenario == "plinth_tower":
        tower_sqft = footprint_sqft * FORM["tower_efficiency"] * FORM["tower_floors"]
    return {"podium": podium_sqft, "tower": tower_sqft}


def _validate_use_mix(scenario: str, podium_use: str, tower_use: str) -> None:
    areas = buildable_sqft(1.0, scenario)
    if areas["podium"] and podium_use not in PODIUM_USES:
        raise ValueError(f"unsupported podium use: {podium_use!r}")
    if areas["tower"] and tower_use not in TOWER_USES:
        raise ValueError(f"unsupported tower use: {tower_use!r}")


# ---------------------------------------------------------------------------
# 4. CORE PRO FORMA -- stabilized, unlevered economics
# ---------------------------------------------------------------------------

def price_use_mix(
    footprint_sqft: float,
    scenario: str,
    podium_use: str = "retail",
    tower_use: str = "office",
) -> dict[str, Any]:
    """Price a specified form and program; this is the puppet-mode engine."""
    _validate_use_mix(scenario, podium_use, tower_use)
    areas = buildable_sqft(footprint_sqft, scenario)

    hard_cost = 0.0
    potential_gross_revenue = 0.0
    component_results: dict[str, dict[str, Any]] = {}

    for component, use in (("podium", podium_use), ("tower", tower_use)):
        area = areas[component]
        if not area:
            continue
        component_hard_cost = area * HARD_COST_PER_SQFT[(component, use)]
        component_revenue = area * RENT_PER_SQFT_YR[use]
        hard_cost += component_hard_cost
        potential_gross_revenue += component_revenue
        component_results[component] = {
            "use": use,
            "sqft": area,
            "hard_cost": component_hard_cost,
            "potential_gross_revenue": component_revenue,
        }

    soft_cost = hard_cost * SOFT_COST_PCT
    total_cost = hard_cost + soft_cost
    effective_gross_income = potential_gross_revenue * (1 - VACANCY_PCT)
    operating_expenses = effective_gross_income * OPEX_RATIO
    noi = effective_gross_income - operating_expenses
    yield_on_cost = noi / total_cost if total_cost else 0.0
    profit_margin = yield_on_cost - REQUIRED_YIELD if total_cost else 0.0

    # A transparent annual dollar proxy for excess/shortfall against the
    # required yield; it is not an exit value, NPV, or developer profit.
    annual_surplus = noi - total_cost * REQUIRED_YIELD
    is_viable = total_cost > 0 and profit_margin >= 0

    return {
        "scenario": scenario,
        "podium_use": podium_use if areas["podium"] else "-",
        "tower_use": tower_use if areas["tower"] else "-",
        "podium_sqft": areas["podium"],
        "tower_sqft": areas["tower"],
        "components": component_results,
        "hard_cost": hard_cost,
        "soft_cost": soft_cost,
        "total_cost": total_cost,
        "potential_gross_revenue": potential_gross_revenue,
        "effective_gross_income": effective_gross_income,
        "operating_expenses": operating_expenses,
        "noi": noi,
        "required_yield": REQUIRED_YIELD,
        "yield_on_cost": yield_on_cost,
        "profit_margin": profit_margin,
        "annual_surplus": annual_surplus,
        "is_viable": is_viable,
    }


# ---------------------------------------------------------------------------
# 5. AGENCY MODES
# ---------------------------------------------------------------------------

def candidate_use_mixes(footprint_sqft: float, scenario: str) -> list[dict[str, Any]]:
    """Return every allowed program, enabling transparent developer choices."""
    if scenario == "nothing":
        return [price_use_mix(footprint_sqft, scenario)]
    podium_choices = PODIUM_USES
    tower_choices = TOWER_USES if scenario == "plinth_tower" else ("office",)
    return [
        price_use_mix(footprint_sqft, scenario, podium_use, tower_use)
        for podium_use, tower_use in product(podium_choices, tower_choices)
    ]


def developer_mode(footprint_sqft: float, scenario: str) -> dict[str, Any]:
    """Choose the allowed program with the highest stabilized profit margin."""
    candidates = candidate_use_mixes(footprint_sqft, scenario)
    chosen = max(candidates, key=lambda result: result["profit_margin"])
    return {**chosen, "candidates": candidates}


def puppet_mode(
    footprint_sqft: float, scenario: str, podium_use: str, tower_use: str
) -> dict[str, Any]:
    """Price an externally supplied program without optimizing it."""
    return price_use_mix(footprint_sqft, scenario, podium_use, tower_use)


# ---------------------------------------------------------------------------
# 6. CONSTRUCTION LIKELIHOOD AND RUNNER
# ---------------------------------------------------------------------------

def construction_likelihood(profit_margin: float, has_development: bool = True) -> float:
    """Map a development's profit spread to a continuous construction chance."""
    if not has_development:
        return 0.0
    exponent = max(-700.0, min(700.0, -SCURVE_STEEPNESS * profit_margin))
    return 1 / (1 + math.exp(exponent))


def run_all() -> list[dict[str, Any]]:
    """Run developer-agency mode for every fixed parcel and every state."""
    validate_assumptions()
    rows = []
    for parcel, grid_squares in PARCELS.items():
        footprint = parcel_footprint_sqft(grid_squares)
        for scenario in SCENARIOS:
            result = developer_mode(footprint, scenario)
            rows.append({
                "parcel": parcel,
                "grid_squares": grid_squares,
                "footprint_sqft": footprint,
                **result,
                "likelihood": construction_likelihood(
                    result["profit_margin"], has_development=result["total_cost"] > 0
                ),
            })
    return rows


def print_table(rows: list[dict[str, Any]]) -> None:
    """Present the machine-readable run results as a compact demo table."""
    header = (
        f"{'Parcel':<8}{'Scenario':<15}{'Podium':<9}{'Tower':<13}"
        f"{'Cost ($M)':<11}{'NOI ($k)':<11}{'YoC':<8}{'Margin':<9}"
        f"{'Viable':<8}{'P(build)':<9}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        yield_text = f"{row['yield_on_cost'] * 100:.2f}%"
        margin_text = f"{row['profit_margin'] * 100:.2f}%"
        likelihood_text = f"{row['likelihood'] * 100:.1f}%"
        print(
            f"{row['parcel']:<8}{row['scenario']:<15}{row['podium_use']:<9}"
            f"{row['tower_use']:<13}{row['total_cost'] / 1e6:<11.2f}"
            f"{row['noi'] / 1e3:<11.1f}{yield_text:<8}{margin_text:<9}"
            f"{str(row['is_viable']):<8}{likelihood_text:<9}"
        )


if __name__ == "__main__":
    rows = run_all()
    print_table(rows)

    print("\nPuppet-mode example -- Green, plinth+tower, forced office/office:")
    footprint = parcel_footprint_sqft(PARCELS["Green"])
    puppet_result = puppet_mode(footprint, "plinth_tower", "office", "office")
    likelihood = construction_likelihood(
        puppet_result["profit_margin"], has_development=puppet_result["total_cost"] > 0
    )
    print(
        f"  Cost: ${puppet_result['total_cost'] / 1e6:.2f}M  "
        f"NOI: ${puppet_result['noi'] / 1e3:.1f}k  "
        f"YoC: {puppet_result['yield_on_cost'] * 100:.2f}%  "
        f"Margin: {puppet_result['profit_margin'] * 100:.2f}%  "
        f"Viable: {puppet_result['is_viable']}  "
        f"P(build): {likelihood * 100:.1f}%"
    )
