"""Legacy bonus formula and preference compensation; the solver imports neither."""
from dataclasses import dataclass, replace
import math

from .config import load_config
from .optimizer import optimize


@dataclass(frozen=True)
class BonusPolicy:
    threshold: float
    maximum_premium: float
    housing_block_units: int
    housing_premium_multipliers: tuple
    one_package_per_nonhousing_use: bool
    package_limit_exemptions: tuple
    maximum_amenity_types: object
    baseline: str

    @classmethod
    def from_config(cls, config=None):
        data = (config or load_config()).data
        bonus, selection = data["bonuses"], data["selection"]
        return cls(bonus["threshold"], bonus["maximum_premium"], bonus["housing_block_units"],
                   tuple(bonus["housing_premium_multipliers"]), selection["one_package_per_nonhousing_use"],
                   tuple(selection["package_limit_exemptions"]), selection["maximum_amenity_types"], bonus["baseline"])


def far_bonus_for_use(preference_weight, noi_yearly, reference_weight, square_footage, *,
                      indoor=False, eligible=True, bonus_far_area_sqft=None, legacy=None):
    if legacy is None or bonus_far_area_sqft is None and indoor:
        config = load_config()
        legacy = legacy or config.data["bonuses"]["legacy"]
        bonus_far_area_sqft = bonus_far_area_sqft or config.data["site"]["tower"]["footprint_sqft"]
    values = (preference_weight, noi_yearly, reference_weight, square_footage, *legacy.values())
    if not all(math.isfinite(value) for value in values):
        raise ValueError("FAR bonus inputs must be finite")
    if reference_weight <= 0 or not 0 <= preference_weight <= reference_weight or square_footage < 0:
        raise ValueError("Invalid preference weight, reference weight, or program area")
    if min(legacy.values()) <= 0 or indoor and (not math.isfinite(bonus_far_area_sqft) or bonus_far_area_sqft <= 0):
        raise ValueError("FAR bonus scales must be positive")
    if not square_footage or not eligible:
        return 0.0
    scaled_noi = (noi_yearly / square_footage) / legacy["noi_per_sqft_scale"]
    if scaled_noi >= 0:
        decay = math.exp(-scaled_noi)
        subsidy_factor = decay / (1 + decay)
    else:
        subsidy_factor = 1 / (1 + math.exp(scaled_noi))
    demand = legacy["scale"] * (preference_weight / reference_weight) * (square_footage / legacy["reference_area_sqft"]) * subsidy_factor
    return demand + (square_footage / bonus_far_area_sqft if indoor else 0.0)


def bonus_factor(preference, premium_multiplier=1.0, *, policy=None):
    policy = policy or BonusPolicy.from_config()
    if not 0 <= preference <= 1 or not 0 <= premium_multiplier <= 1:
        raise ValueError("Preference and premium multiplier must be in [0, 1]")
    t = policy.threshold
    if not 0 < t < 1 or policy.maximum_premium < 0:
        raise ValueError("Invalid preference policy")
    return min(1, (preference / t) ** 2) + policy.maximum_premium * premium_multiplier * max(0, (preference - t) / (1 - t))


def apply_quantity_limits(programs, *, policy=None):
    policy = policy or BonusPolicy.from_config()
    return [replace(p, maximum_sqft=max(p.minimum_sqft, p.unit_sqft))
            if policy.one_package_per_nonhousing_use and not p.housing and p.name not in policy.package_limit_exemptions
            else p for p in programs]


def search_break_even(solve, upper, target, *, iterations, tolerance=0.01):
    """Shared search; callers decide how infeasible trials are represented."""
    maximum = solve(upper)
    if not maximum or maximum["totals"]["development_profit"] < target - tolerance:
        return None, maximum
    lower = 0.0
    for _ in range(iterations):
        middle = (lower + upper) / 2
        trial = solve(middle)
        if trial and trial["totals"]["development_profit"] >= target - tolerance:
            upper = middle
        else:
            lower = middle
    return upper, maximum


def calibrate(scenario, weights, programs, *, policy=None, use_all_fillers=False, solver_options=None, threshold_cache=None):
    policy = policy or BonusPolicy.from_config()
    solver_options = dict(solver_options or {})
    programs = apply_quantity_limits(programs, policy=policy)
    weights = dict(weights)
    if not weights or any(not math.isfinite(v) or v < 0 for v in weights.values()) or max(weights.values()) <= 0:
        raise ValueError("Preference weights must be finite, nonnegative, and have positive total")
    if set(p.name for p in programs) - set(weights):
        raise ValueError("Preference weights must cover the active catalog")
    reference = max(weights.values())
    if use_all_fillers or policy.baseline == "all_fillers":
        fillers = [p for p in programs if p.bonus_far_per_unit <= 0]
    else:
        fillers = [next(p for p in programs if p.name == "luxury_multifamily")]
    baseline = optimize(fillers, scenario, objective="development-profit", **solver_options)
    if baseline["status"] != "optimal":
        raise RuntimeError("Baseline not optimal")
    target = baseline["totals"]["development_profit"]
    calibrated, rows = [], []
    for p in programs:
        if p.bonus_far_per_unit <= 0:
            calibrated.append(p)
            continue
        d = weights[p.name] / reference
        minimum = p.minimum_sqft / p.unit_sqft if p.continuous else math.ceil(p.minimum_sqft / p.unit_sqft)
        quantities = [policy.housing_block_units * (j + 1) for j in range(len(policy.housing_premium_multipliers))] if p.housing else [minimum]
        increments, previous = [], 0.0
        for j, quantity in enumerate(quantities):
            fixed = replace(p, minimum_sqft=quantity * p.unit_sqft, maximum_sqft=quantity * p.unit_sqft)

            def solve(bonus):
                result = optimize(fillers + [replace(fixed, bonus_far_per_unit=bonus / quantity)], scenario,
                                  required_quantities={p.name: quantity}, objective="development-profit", **solver_options)
                if result["status"] == "infeasible":
                    return None
                if result["status"] != "optimal":
                    raise RuntimeError(f"Calibration failed: {p.name}")
                return result

            # Preferences affect the award, not the financial threshold. A complete
            # immutable key prevents reuse after scenario or profitability changes.
            key = (tuple(fillers), fixed, scenario, tuple(sorted(solver_options.items())), target, 27, 0.01)
            if threshold_cache is not None and key in threshold_cache:
                threshold = threshold_cache[key]
            else:
                threshold, _ = search_break_even(solve, max(0, scenario.max_tower_stories - scenario.base_tower_stories),
                                                  target, iterations=27)
                if threshold_cache is not None:
                    threshold_cache[key] = threshold
            increment = 0 if threshold is None else max(0, threshold - previous)
            multiplier = policy.housing_premium_multipliers[j] if p.housing else 1
            awarded = increment * bonus_factor(d, multiplier, policy=policy)
            increments.append(awarded)
            rows.append(dict(amenity=p.name, quantity=quantity, preference=d,
                             break_even_total_bonus_far=threshold, incremental_bonus_far=awarded,
                             feasible=threshold is not None))
            if threshold is None:
                break
            previous = threshold
        candidate = replace(p, bonus_far_per_unit=0, bonus_eligible=True, bonus_block_units=policy.housing_block_units)
        candidate = replace(candidate, bonus_blocks=tuple(increments)) if p.housing else replace(candidate, bonus_far_per_unit=increments[0] / minimum)
        calibrated.append(candidate)
    return calibrated, rows, baseline
