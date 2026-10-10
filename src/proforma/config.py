"""Load one scenario and its four datasets, resolve paths, and validate relationships."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import hashlib
import json
import math
from pathlib import Path
import sysconfig
from types import MappingProxyType
from urllib.error import URLError
from urllib.request import urlopen

CHECKOUT_ROOT = Path(__file__).resolve().parents[2]
_data_candidates = (CHECKOUT_ROOT,
                    Path(__file__).resolve().parents[1] / "share" / "volpe-proforma",
                    Path(sysconfig.get_path("data")) / "share" / "volpe-proforma")
DATA_ROOT = next((path for path in _data_candidates if (path / "config" / "scenarios" / "default.json").is_file()), CHECKOUT_ROOT)
PROJECT_ROOT = CHECKOUT_ROOT if DATA_ROOT == CHECKOUT_ROOT else Path.cwd()
DEFAULT_SCENARIO = DATA_ROOT / "config" / "scenarios" / "default.json"
NORMALIZATION = "weight_divided_by_maximum_snapshot_weight"
PREFERENCE_ENDPOINT = "http://volpe.media.mit.edu:8123/api/amenities/pref_order"


def freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    return value


def thaw(value):
    if isinstance(value, Mapping):
        return {k: thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [thaw(v) for v in value]
    return value


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _keys(value, required, optional=(), label="configuration"):
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    missing, unknown = set(required) - set(value), set(value) - set(required) - set(optional)
    if missing or unknown:
        raise ValueError(f"{label}: missing fields {sorted(missing)}; unknown fields {sorted(unknown)}")


def _number(value, label, minimum=0, positive=False, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or value < minimum or (positive and value <= 0) or (integer and int(value) != value)):
        raise ValueError(f"{label} must be a finite {'positive' if positive else 'nonnegative'}"
                         f" {'integer' if integer else 'number'}")


def _boolean(value, label):
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be true or false")


def _version(data, label):
    if data.get("schema_version") != 1:
        raise ValueError(f"{label}: unsupported schema_version")


def _validate_scenario(data):
    _keys(data, ("schema_version", "name", "inputs", "site", "finance", "bonuses", "selection", "solver"))
    _version(data, "scenario")
    if not isinstance(data["name"], str) or not data["name"].strip():
        raise ValueError("Scenario name must be nonempty")
    _keys(data["inputs"], ("catalog", "economics", "construction_costs", "preferences"), label="inputs")
    for key, value in data["inputs"].items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"inputs.{key} must be a file path")
    site = data["site"]
    _keys(site, ("parcel_area_sqft", "podium", "tower", "open_space_sqft"), label="site")
    _keys(site["podium"], ("footprint_sqft", "stories"), label="site.podium")
    _keys(site["tower"], ("footprint_sqft", "base_stories", "maximum_stories"), label="site.tower")
    _number(site["parcel_area_sqft"], "parcel_area_sqft", positive=True)
    _number(site["open_space_sqft"], "open_space_sqft")
    for name in ("podium", "tower"):
        for key, value in site[name].items():
            _number(value, f"site.{name}.{key}", positive=key == "footprint_sqft")
    if site["tower"]["base_stories"] > site["tower"]["maximum_stories"]:
        raise ValueError("Base tower stories exceed maximum tower stories")
    if (site["podium"]["footprint_sqft"] + site["tower"]["footprint_sqft"]
            + site["open_space_sqft"] > site["parcel_area_sqft"] + 1e-8):
        raise ValueError("Separate footprints and open space exceed parcel area")
    finance = data["finance"]
    _keys(finance, ("objective", "capitalization_rate", "required_return", "include_land", "land_regime",
                    "development_budget_usd", "soft_cost_fraction", "tower_cost_multiplier"), label="finance")
    if finance["objective"] not in ("annual-surplus", "development-profit"):
        raise ValueError("Unknown financial objective")
    for key in ("capitalization_rate", "tower_cost_multiplier", "required_return", "soft_cost_fraction"):
        _number(finance[key], key, positive=key in ("capitalization_rate", "tower_cost_multiplier"))
    if finance["development_budget_usd"] is not None:
        _number(finance["development_budget_usd"], "development_budget_usd")
    _boolean(finance["include_land"], "include_land")
    if finance["land_regime"] not in ("plinth_only", "tower_permitted"):
        raise ValueError("Unknown land_regime")
    bonuses = data["bonuses"]
    _keys(bonuses, ("policy", "normalization", "threshold", "maximum_premium", "baseline",
                   "housing_block_units", "housing_premium_multipliers", "legacy"), label="bonuses")
    if bonuses["policy"] not in ("preference", "legacy"):
        raise ValueError("Unknown bonus policy")
    if bonuses["normalization"] != NORMALIZATION:
        raise ValueError("Unknown preference normalization")
    if bonuses["baseline"] not in ("luxury_only", "all_fillers"):
        raise ValueError("Unknown calibration baseline")
    _number(bonuses["threshold"], "threshold", positive=True)
    if bonuses["threshold"] >= 1:
        raise ValueError("Preference threshold must be less than one")
    _number(bonuses["maximum_premium"], "maximum_premium")
    _number(bonuses["housing_block_units"], "housing_block_units", positive=True, integer=True)
    if not isinstance(bonuses["housing_premium_multipliers"], (list, tuple)) or not bonuses["housing_premium_multipliers"]:
        raise ValueError("housing_premium_multipliers must be a nonempty array")
    for value in bonuses["housing_premium_multipliers"]:
        _number(value, "housing premium multiplier")
        if value > 1:
            raise ValueError("Housing premium multipliers must be in [0, 1]")
    _keys(bonuses["legacy"], ("scale", "reference_area_sqft", "noi_per_sqft_scale"), label="bonuses.legacy")
    for key, value in bonuses["legacy"].items():
        _number(value, f"legacy.{key}", positive=True)
    selection = data["selection"]
    _keys(selection, ("minimum_housing_units", "maximum_amenity_types", "one_package_per_nonhousing_use",
                     "package_limit_exemptions", "floor_limit_exemptions", "maximum_nonhousing_floor_equivalents"),
          label="selection")
    _number(selection["minimum_housing_units"], "minimum_housing_units", positive=True, integer=True)
    _number(selection["maximum_nonhousing_floor_equivalents"], "maximum_nonhousing_floor_equivalents")
    if selection["maximum_amenity_types"] is not None:
        _number(selection["maximum_amenity_types"], "maximum_amenity_types", integer=True)
    _boolean(selection["one_package_per_nonhousing_use"], "one_package_per_nonhousing_use")
    for key in ("package_limit_exemptions", "floor_limit_exemptions"):
        if (not isinstance(selection[key], (list, tuple))
                or any(not isinstance(v, str) for v in selection[key])
                or len(set(selection[key])) != len(selection[key])):
            raise ValueError(f"{key} must contain unique use identifiers")
    _keys(data["solver"], ("time_limit_seconds", "relative_gap"), label="solver")
    _number(data["solver"]["time_limit_seconds"], "time_limit_seconds", positive=True)
    _number(data["solver"]["relative_gap"], "relative_gap")
    if data["solver"]["relative_gap"] > 1:
        raise ValueError("relative_gap must be in [0, 1]")


def _validate_datasets(data, datasets):
    catalog, economics, costs, preferences = (datasets[k] for k in
                                             ("catalog", "economics", "construction_costs", "preferences"))
    for name, dataset in datasets.items():
        _version(dataset, name)
    _keys(catalog, ("schema_version", "description", "field_notes", "amenities", "excluded_amenity_types"), label="catalog")
    if not isinstance(catalog["amenities"], (list, tuple)) or not catalog["amenities"]:
        raise ValueError("Catalog amenities must be a nonempty array")
    names = set()
    required = ("amenity_type", "broad_amenity_category", "use_family", "financial_group", "program_unit",
                "default_unit_sqft", "minimum_program_sqft", "maximum_program_sqft", "ground_level",
                "example_area_sqft", "outdoor", "bonus_eligible")
    for row in catalog["amenities"]:
        _keys(row, required, ("program_description",), label="catalog row")
        name = row["amenity_type"]
        for key in ("amenity_type", "financial_group", "use_family", "broad_amenity_category"):
            if not isinstance(row[key], str) or not row[key]:
                raise ValueError(f"Catalog {key} must be a nonempty identifier")
        if name in names:
            raise ValueError(f"Duplicate catalog identifier: {name}")
        names.add(name)
        if row["program_unit"] not in ("dwelling_unit", "square_foot", "facility", "commercial_bay"):
            raise ValueError(f"Unknown program unit: {name}")
        for key in ("default_unit_sqft", "minimum_program_sqft", "example_area_sqft"):
            _number(row[key], f"{name}.{key}", positive=True)
        if row["maximum_program_sqft"] is not None:
            _number(row["maximum_program_sqft"], f"{name}.maximum_program_sqft", positive=True)
            if row["maximum_program_sqft"] < row["minimum_program_sqft"]:
                raise ValueError(f"{name}: maximum below minimum")
        elif name not in data["selection"]["floor_limit_exemptions"]:
            raise ValueError(f"{name}: null maximum requires a floor-limit exemption")
        for key in ("ground_level", "outdoor", "bonus_eligible"):
            _boolean(row[key], f"{name}.{key}")
    for key in ("package_limit_exemptions", "floor_limit_exemptions"):
        if set(data["selection"][key]) - names:
            raise ValueError(f"Unknown use in {key}")
    if set(catalog["excluded_amenity_types"]) & names:
        raise ValueError("Excluded catalog uses cannot also be active")
    _keys(preferences, ("schema_version", "description", "normalization", "weights"), label="preferences")
    if preferences["normalization"] != data["bonuses"]["normalization"]:
        raise ValueError("Preference snapshot and scenario normalization differ")
    weights = {}
    for pair in preferences["weights"]:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or not isinstance(pair[0], str):
            raise ValueError("Preference weights must be [identifier, weight] pairs")
        name, value = pair
        if name in weights:
            raise ValueError(f"Duplicate preference identifier: {name}")
        _number(value, f"weight.{name}")
        weights[name] = value
    if not weights or max(weights.values()) <= 0 or names - set(weights):
        raise ValueError("Positive preference snapshot must cover every active use")
    _keys(economics, ("schema_version", "currency", "financial_groups", "use_overrides", "reference_only_use_ids",
                      "land_cost_per_parcel_sqft_usd", "inactive_observations"), label="economics")
    if economics["currency"] != "USD":
        raise ValueError("Only USD economics are supported")
    groups = economics["financial_groups"]
    if {r["financial_group"] for r in catalog["amenities"]} - set(groups):
        raise ValueError("Catalog contains an unknown financial group")
    reference_only = economics["reference_only_use_ids"]
    if (not isinstance(reference_only, (list, tuple)) or any(not isinstance(v, str) for v in reference_only)
            or len(set(reference_only)) != len(reference_only) or set(reference_only) & names):
        raise ValueError("reference_only_use_ids must contain unique inactive identifiers")
    if set(economics["use_overrides"]) - names - set(reference_only):
        raise ValueError("Unknown use in economics overrides")
    for label, rows in (("financial_groups", groups), ("use_overrides", economics["use_overrides"])):
        for name, row in rows.items():
            _keys(row, ("basis",), ("annual_rent_per_sqft_usd", "annual_rent_per_unit_usd", "unit_size_from_use",
                                    "opex_fraction", "annual_maintenance_per_sqft_usd"), label=f"{label}.{name}")
            rent_fields = {"annual_rent_per_sqft_usd", "annual_rent_per_unit_usd"} & set(row)
            expense_fields = {"opex_fraction", "annual_maintenance_per_sqft_usd"} & set(row)
            if len(rent_fields) != 1 or len(expense_fields) != 1:
                raise ValueError(f"{name}: specify one rent basis and one expense basis")
            for key in rent_fields | expense_fields:
                _number(row[key], f"{name}.{key}")
            if row.get("opex_fraction", 0) > 1:
                raise ValueError(f"{name}: opex_fraction must be in [0, 1]")
            if "annual_rent_per_unit_usd" in row and row.get("unit_size_from_use") not in names:
                raise ValueError(f"{name}: unknown housing unit size reference")
    _keys(economics["land_cost_per_parcel_sqft_usd"], ("plinth_only", "tower_permitted"), label="land rates")
    for name, value in economics["land_cost_per_parcel_sqft_usd"].items():
        _number(value, f"land rate {name}")
    _keys(costs, ("schema_version", "description", "source", "location", "currency", "area_unit", "rows",
                  "financial_group_mapping", "financial_group_blends", "estimated_hard_cost_per_sqft",
                  "outdoor_financial_groups", "mapping_notes"), label="construction_costs")
    if costs["currency"] != "USD":
        raise ValueError("Only USD construction costs are supported")
    cost_types = set()
    for row in costs["rows"]:
        _keys(row, ("type", "hard_cost_high_per_sqft"), label="construction row")
        if row["type"] in cost_types:
            raise ValueError("Duplicate construction cost type")
        cost_types.add(row["type"])
        _number(row["hard_cost_high_per_sqft"], row["type"], positive=True)
    for cost_type in costs["financial_group_mapping"].values():
        if cost_type not in cost_types:
            raise ValueError(f"Unknown construction cost type: {cost_type}")
    for blend in costs["financial_group_blends"].values():
        if not blend or set(blend) - cost_types:
            raise ValueError("Invalid construction blend")
    for group, value in costs["estimated_hard_cost_per_sqft"].items():
        _number(value, f"construction estimate {group}", positive=True)
    if set(costs["outdoor_financial_groups"]) - set(groups):
        raise ValueError("Unknown outdoor financial group")
    for row in catalog["amenities"]:
        if row["outdoor"] != (row["financial_group"] in costs["outdoor_financial_groups"]):
            raise ValueError(f"{row['amenity_type']}: outdoor placement and construction group disagree")
    assigned = set(costs["financial_group_mapping"]) | set(costs["financial_group_blends"]) | set(costs["estimated_hard_cost_per_sqft"])
    if set(groups) - assigned or assigned - set(groups):
        raise ValueError("Every financial group must have a construction rate")


@dataclass(frozen=True)
class ModelConfig:
    scenario_path: Path
    data: Mapping
    datasets: Mapping
    source_hashes: Mapping

    @property
    def weights(self):
        return dict(self.datasets["preferences"]["weights"])

    @property
    def solver_options(self):
        return {"time_limit": self.data["solver"]["time_limit_seconds"],
                "relative_gap": self.data["solver"]["relative_gap"]}

    def resolved(self):
        return {"scenario": thaw(self.data), "datasets": thaw(self.datasets)}

    def with_overrides(self, **sections):
        """Explicit section overrides; unknown names and invalid relationships fail."""
        data = thaw(self.data)
        for section, values in sections.items():
            if section not in data or not isinstance(values, Mapping) or not isinstance(data[section], dict):
                raise ValueError(f"Unknown or non-object scenario section: {section}")
            if section == "inputs":
                raise ValueError("Select another scenario to change input paths")
            data[section].update(thaw(values))
        _validate_scenario(data)
        _validate_datasets(data, self.datasets)
        return replace(self, data=freeze(data))


def load_config(path=None, *, fetch_pref_order=False, sample=None):
    scenario_path = Path(path or DEFAULT_SCENARIO).resolve()
    hashes = {}

    def read(file_path):
        raw = file_path.read_bytes()
        hashes[str(file_path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_object)

    data = read(scenario_path)
    _validate_scenario(data)
    datasets = {name: read((scenario_path.parent / relative).resolve())
                for name, relative in data["inputs"].items()
                if name != "preferences" or not fetch_pref_order}
    if fetch_pref_order:
        if sample is not None:
            _number(sample, "sample", positive=True, integer=True)
        url = PREFERENCE_ENDPOINT + (f"?n={sample}" if sample is not None else "")
        try:
            with urlopen(url, timeout=15) as response:
                raw = response.read()
            weights = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_object)
        except (OSError, URLError, ValueError) as error:
            raise ValueError(f"Could not fetch preferences from {url}: {error}") from error
        if not isinstance(weights, list):
            raise ValueError("Remote preferences must be a list of [identifier, weight] pairs")
        datasets["preferences"] = {"schema_version": 1, "description": f"Fetched from {url}",
                                   "normalization": NORMALIZATION, "weights": weights}
        hashes[url] = hashlib.sha256(raw).hexdigest()
    _validate_datasets(data, datasets)
    return ModelConfig(scenario_path, freeze(data), freeze(datasets), freeze(hashes))
