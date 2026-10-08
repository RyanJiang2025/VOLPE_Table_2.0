# Active input provenance

This reorganization preserves existing numerical inputs. It does not independently validate the source documents or promote synthetic estimates to market observations.

| Inputs | Existing provenance and treatment | Active location |
|---|---|---|
| Office and retail rent/expenses | User-supplied CoStar inputs. Office rent was supplied for Kendall Square; the expense and other rent inputs were described as Boston submarket values. | `config/economics.json` |
| Housing | User-selected synthetic rents, unit sizes, and expense assumptions. These supersede earlier generic housing conversions for the active model. | Economics groups and catalog unit sizes |
| Boston hard construction rates | Existing dataset attributes its high-cost rows to Rider Levett Bucknall's Q2 2026 North America report. Its original source URL, location, and units are retained in the JSON. | `config/construction_costs.json` |
| Cost proxies/blends/estimates | Direct category mappings, school average, and synthetic commercial/public/outdoor and housing estimates are retained and labeled separately from source rows. | Construction JSON mappings, blends, and estimates |
| Public upkeep | Synthetic annual per-area maintenance, with zero rent and developer-funded construction and operations. | Economics groups and use exceptions |
| Preference weights | Original 37-identifier cardinal snapshot, unchanged numerically and in order. | `config/preferences.json` |
| Parcel and program sizes | Synthetic compact scenario and preliminary use sizes. | Selected scenario and catalog |
| Cap rate, return, and bonus policy | Provisional/model-selected assumptions; not newly researched market rates or verified zoning rules. | Scenario finance/bonuses sections |

Every financial group and use exception has a `basis` note. Construction source rows remain separate from synthetic estimated hard costs. Original superseded observations are explicitly inactive in economics.

The complete prior source narratives are preserved in [root sources](history/root_sources.md) and [dummy sources](history/dummy_sources.md). They contain historical statements that may be superseded by current overrides, including older housing rent examples and government revenue assumptions. Consult active configuration for the actual values used today.

See [financial objective decision](decisions/financial_objective.md), [preference policy decision](decisions/preference_bonus.md), and [limitations](limitations.md).
