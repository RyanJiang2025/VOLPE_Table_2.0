"""Immutable solver inputs and physical capacity relationships."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional


@dataclass(frozen=True)
class Program:
    name: str
    unit_sqft: float
    minimum_sqft: float
    maximum_sqft: float
    noi_per_sqft: float
    podium_cost_per_sqft: float
    tower_cost_per_sqft: float
    bonus_far_per_unit: float = 0.0
    continuous: bool = False
    housing: bool = False
    outdoor: bool = False
    ground_level: bool = False
    tower_allowed: bool = True
    program_unit: str = "facility"
    capitalization_rate: Optional[float] = None
    bonus_blocks: tuple = ()
    bonus_eligible: bool = False
    unrestricted_nonhousing: bool = False
    bonus_block_units: int = 5


@dataclass(frozen=True)
class Scenario:
    # None defaults are resolved lazily for callers constructing small test scenarios.
    # Production paths construct one fully explicit Scenario from a loaded config.
    required_return: float = None
    podium_footprint: float = None
    podium_stories: float = None
    tower_footprint: float = None
    base_tower_stories: float = None
    max_tower_stories: float = None
    open_space: float = None
    max_nonhousing_stories: float = None
    land_cost: float = 0.0
    development_budget: Optional[float] = None
    capitalization_rate: float = None

    def __post_init__(self):
        fields = ("required_return", "podium_footprint", "podium_stories", "tower_footprint",
                  "base_tower_stories", "max_tower_stories", "open_space", "max_nonhousing_stories",
                  "capitalization_rate")
        if any(getattr(self, name) is None for name in fields):
            defaults = type(self).from_config()
            for name in fields:
                if getattr(self, name) is None:
                    object.__setattr__(self, name, getattr(defaults, name))

    @classmethod
    def from_config(cls, config=None, required_return=None, include_land=None, development_budget=None):
        from .config import load_config
        config = config or load_config()
        site, finance, selection = (config.data[k] for k in ("site", "finance", "selection"))
        include_land = finance["include_land"] if include_land is None else include_land
        land_rate = config.datasets["economics"]["land_cost_per_parcel_sqft_usd"][finance["land_regime"]]
        return cls(
            required_return=finance["required_return"] if required_return is None else required_return,
            podium_footprint=site["podium"]["footprint_sqft"], podium_stories=site["podium"]["stories"],
            tower_footprint=site["tower"]["footprint_sqft"], base_tower_stories=site["tower"]["base_stories"],
            max_tower_stories=site["tower"]["maximum_stories"], open_space=site["open_space_sqft"],
            max_nonhousing_stories=selection["maximum_nonhousing_floor_equivalents"],
            land_cost=site["parcel_area_sqft"] * land_rate if include_land else 0.0,
            development_budget=finance["development_budget_usd"] if development_budget is None else development_budget,
            capitalization_rate=finance["capitalization_rate"],
        )

    @property
    def podium_capacity(self):
        return self.podium_footprint * self.podium_stories

    @property
    def maximum_tower_capacity(self):
        return self.tower_footprint * self.max_tower_stories

    def tower_capacity_for_bonus(self, bonus_far):
        if not math.isfinite(bonus_far) or bonus_far < 0:
            raise ValueError("bonus_far must be finite and nonnegative")
        return min(self.tower_footprint * self.base_tower_stories + bonus_far * self.tower_footprint,
                   self.maximum_tower_capacity)
