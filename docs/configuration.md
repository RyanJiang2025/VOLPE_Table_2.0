# Configuration and data flow

## Start with a scenario

`config/scenarios/default.json` is the entry point. Its four input paths are resolved **relative to the scenario file**, independently of the shell's working directory. To make another scenario, copy this file, give it a descriptive name, and keep shared datasets referenced unless that scenario needs different underlying data.

| File | Owns | Relationships |
|---|---|---|
| `catalog.json` | Active use IDs, categories, financial groups, unit areas, intrinsic bounds, placement, example areas, bonus eligibility | `financial_group` points to economics/costs; `amenity_type` joins to preferences |
| `economics.json` | Annual rents, expense bases, public maintenance, use exceptions, land prices | Per-unit housing rent references its catalog use for unit area |
| `construction_costs.json` | Source cost rows, group mappings/blends, synthetic estimates, outdoor cost groups | Every financial group resolves to a hard-cost rate |
| `preferences.json` | Complete saved identifier/weight pairs and normalization | Every active use must have a weight; inactive weights remain part of normalization |
| `scenarios/default.json` | Input selection, parcel geometry, objective, financial parameters, bonus policy, selection rules, solver settings | Applies scenario constraints to the shared inputs |

## Units and ownership

- Areas use square feet. Indoor costs apply to gross floor area; outdoor costs and maintenance apply to improved site area.
- Rents and operating expenses are annual USD. Housing rent is per dwelling; commercial rent is per square foot.
- `opex_fraction` is a decimal fraction (`0.40` means 40%). Public uses instead have `annual_maintenance_per_sqft_usd`; zero rent does not imply zero maintenance.
- Unit size is stored once in the catalog. Housing annual rent per unit is divided by that catalog size.
- Construction data contain hard costs. Scenario `soft_cost_fraction` and `tower_cost_multiplier` produce total podium and tower costs at runtime.
- Land prices are per square foot of parcel land. Land is charged once for development when enabled.
- `example_area_sqft` is a descriptive example, not a selected allocation or a required quantity.
- NOI, total costs, capacity, yields, and awarded bonuses are derived and are not editable catalog fields.

The historical model treats one bonus FAR increment as one tower footprint of extra area. This differs from conventional parcel-area FAR and is preserved explicitly by the tower-capacity relationship. This migration does not reinterpret its units or zoning validity.

## Groups, exceptions, and inactive observations

Shared financial groups are resolved first. `use_overrides` then supply complete rent and expense bases for explicit exceptions, including public uses and retail bank economics. Inactive reference exceptions are named in `reference_only_use_ids`; they do not add active choices. `inactive_observations` preserves earlier inputs and unused hospitality/student assumptions without applying them to the active catalog.

Explicit scenario settings override model-wide defaults through the selected scenario. CLI overrides are applied to that scenario and validated before a run. Dataset input paths cannot be changed with the Python `with_overrides` helper: select a different scenario to select different files.

## Size and policy bounds

The catalog records intrinsic use bounds. Housing minimum area is the greater of its intrinsic minimum and scenario minimum units times unit area. Other nonhousing uses are bounded by their catalog limit and applicable outdoor, ground-floor, or floor-equivalent capacity. A use whose minimum cannot fit is excluded from the effective choice set for that scenario.

Office and lab have a null intrinsic maximum and explicit floor-limit exemptions. Their finite solver bounds follow the physical envelope. Package-limit exemptions are a separate rule even though the same two uses currently appear in both lists.

Under preference policy, a nonhousing use is limited to one facility/bay or its minimum square-foot package unless exempt. This limit is applied during calibration, not to the raw legacy catalog.

Housing bonuses are earned in complete blocks. `housing_block_units` defaults to five, and the solver receives that block size explicitly with each calibrated program. The declining premium multipliers define the supported compensation blocks, not a hard limit on all housing construction.

## Preferences

Keep all **37** identifiers, including the four excluded active choices (`hospital`, `outdoor_sports`, `school`, `supermarket`). The maximum saved weight belongs to inactive `supermarket`. Normalization is cardinal weight divided by the maximum across the complete snapshot; it is not ordinal rank or resident-support percentage. Removing inactive weights would change results.

`baseline: "luxury_only"` preserves current calibration. `all_fillers` explicitly enables all bonus-ineligible filler uses. Changing office/lab profitability in experiments also selects the all-filler baseline. Financial threshold reuse is limited to identical programs, baseline fillers, scenario, search settings, and solver settings; changed economics invalidate it.

## Execution

```text
scenario + selected datasets
    → validate and freeze inputs
    → resolve rates and build active programs
    → select legacy or calibrated preference policy
    → solve explicit programs and scenario
    → independently check feasibility and accounting
    → write report(s) and manifest
```

Loading `proforma` does not build either catalog or import the solver dependencies. Production runs load one configuration and pass it through the pipeline. The 111-row reference taxonomy is read only by `reference_catalog()`.

Invalid schemas, unknown fields, duplicate IDs, incomplete preference coverage, missing cost mappings, inconsistent outdoor placement, nonfinite values, and invalid unit/rate bounds are rejected before solving. Use `load_config(path).with_overrides(finance={...})` for explicit validated programmatic overrides.

The package is designed for editable use in this checkout. Distribution builds include the same default JSON files as data; installed runs can select external scenarios with `--scenario` and produce results in their working directory.
