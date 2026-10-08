# ProForma sources and assumptions

## Current model promoted from the test bed

The root model now includes the functional inputs and optimizer developed in
`dummy_data/`. The provenance sections below retain the original supplied data;
the active synthetic overrides listed here take precedence over those baseline
values. These overrides are scenario assumptions, not new market observations.

- The active catalog has 33 populated uses, with whole apartment/facility sizes,
  minimum areas, placement rules, and developer-funded public maintenance.
- Housing inputs are: general 995 sqft, $48,000 annual rent, 40% opex;
  mid-career 1,100 sqft, $60,000, 38%; senior 800 sqft, $21,600, 45%;
  attainable 750 sqft, $24,000, 42%; luxury 1,250 sqft, $105,000, 35%.
- Housing hard costs per sqft are respectively $390, $410, $420, $350, and $480.
  The synthetic housing-specific costs replace the shared multifamily baseline.
  Office and lab construction cost inputs remain unchanged.
- Default office NOI remains $61.9255/sqft/year and lab NOI $71.50/sqft/year.
  Boosted incomes from the Monte Carlo scenarios are not production defaults.
- Development profit is the provisional CLI objective, using a 4.5% cap rate.
  Annual surplus at a 6% required return is also available. Land is excluded by
  default. See [financial objective notes](FINANCIAL_OBJECTIVE_DECISION.md).
- Preference bonuses cover financially calibrated costs, gated at a relative
  preference threshold of 0.60, with a maximum 15% extra FAR premium. Housing
  earns bonuses in up to four five-apartment blocks with declining premiums.
- There is no amenity-type limit. Nonhousing uses are limited to one facility,
  bay, or minimum square-foot package, with housing, office and lab exempt.
  Office and lab have no per-use upper area or floor limit. The five-story
  podium and 30-story tower capacities remain. Other nonhousing uses retain
  their size and placement limits. See [policy notes](PREFERENCE_BONUS_DECISION.md).

Run the current model from this folder:

```powershell
python -m financial_optimizer --output financial_optimizer_result.json
python -m preference_bonus
python -m financial_optimizer --bonus-policy legacy --output legacy_optimizer_result.json
```

The root optimizer defaults to calibrated preference bonuses. Its raw catalog
and manually configured building example retain historical bonus fields for
comparison; those fields are replaced before a default optimization run.
Default compensation is frozen against a luxury-only no-amenity baseline,
matching the test bed. The calibration API supports all bonus-ineligible filler
uses when explicitly requested for alternative financial scenarios.
Public construction and ongoing costs
remain entirely with the developer. The existing voting snapshot is unchanged.
Monte Carlo runners, stress-test scripts, and their saved results remain in
`dummy_data/`; they are not imported by the root model. Regression tests are
in `tests/`. No files from the nested `ProForma/dummy_data/` copy are used.

## Original input provenance

This file records where the current rent, operating expense, construction, land, and vote inputs came
from. The model rates are in [assumptions.py](assumptions.py), and the Boston
hard-cost inputs are in [boston_construction_costs.json](boston_construction_costs.json).

## Rents and operating expenses (opex/upkeep)

**Source:** CoStar, as supplied by the user. All rent/revenue and operating
expense inputs below were gathered at the **Boston submarket** level, except
for **office rent**, which was gathered at the **Kendall Square Office
submarket** level. Office rent was the only input CoStar gathered at that
level of granularity; office opex uses the Boston submarket.

The following uses currently have both rent/revenue and opex inputs in
[assumptions.py](assumptions.py). Opex is expressed as a percentage of annual
rent/revenue; rent periods and units below follow the current model inputs.

| Building use | Rent/revenue input | Opex | Rent/revenue submarket | Opex submarket |
|---|---:|---:|---|---|
| Office | $91.00/sq ft/year | 31.95% | Kendall Square Office | Boston |
| Retail | $27.20/sq ft/year | 40% | Boston | Boston |
| Multifamily housing | $4,045/unit/year | 40% | Boston | Boston |
| Hospitality/hotel | $223/available room/day (RevPAR) | 67% | Boston | Boston |

In the active catalog, the office inputs apply to `general_office`,
`coworking`, and `commercial_services`. The multifamily inputs apply to
`general_multifamily`, `mid_career_multifamily`, `senior_multifamily`,
`attainable_multifamily`, and `luxury_multifamily`.

Retail rent and opex inputs apply to `general_retail`,
`barber`, `supermarket`, `convenience_store`, `bakery`, `butcher`,
`greengrocer`, `marketplace`, `pharmacy`, and `bank_financial_services`.
Hospitality inputs are recorded but hotels are not yet represented in the
catalog.

Government uses reuse office rent of **$91.00/sq ft/year** and office opex
of **31.95%**, applied to `government_operations` and `post_office` in the
active catalog. This is a model proxy using the CoStar Kendall Square Office
rent and Boston office opex inputs, rather than a separate government market
observation.

Student housing has an opex-only input of **40%** (CoStar, Boston submarket).
It is not yet represented in the catalog and has no separate rent input.

## Multifamily apartment size and annual revenue

The user selected **995 sq ft per apartment** on 2026-10-03, citing
[ApartmentAdvisor's Boston market report](https://www.apartmentadvisor.com/market-reports/boston-ma?ref=elplaneta.com).
The page retrieved during implementation reported 1,043 sq ft; 995 remains
the explicit model input supplied by the user, rather than a verified current
value from that page.

All five multifamily archetypes use 995 sq ft only as the denominator for
converting per-unit rent to per-square-foot rent. Their allocated area and
default unit size remain zero placeholders. With the current **annual** rent input of $4,045 per unit,
annual rent per apartment sq ft is `4045 / 995 = 4.0653266332`. The existing
40% residential operating allowance gives annual upkeep of approximately
$1.6261 per sq ft and annual NOI of $2.4392 per sq ft, before any vacancy
adjustment. Calculations retain full precision.

These rates derive from `multifamily_average_unit_sqft` in
[assumptions.py](assumptions.py), solely as a conversion denominator. Apartment
area is the denominator; no conversion to gross building area or common-area
allowance is included. Allocated program areas remain scenario inputs.

## Construction costs

**Source:** Rider Levett Bucknall (RLB), [North America Quarterly Construction
Cost Report, Q2 2026](https://www.rlb.com/wp-content/uploads/sites/4/2026/06/Q2-2026-QCR_7.7.2026.pdf),
indicative construction-cost tables on PDF pages 10–11. We use the **high**
Boston estimate as a proxy for Kendall Square. RLB states that U.S. values are
hard construction costs in USD per square foot of **gross floor area**. Site,
specification, and market conditions can change actual costs.

| Model use | RLB Boston category | Hard cost ($/gross sq ft) | Treatment |
|---|---|---:|---|
| Office | Prime office, high | 725 | Direct proxy |
| Civic | Prime office, high | 725 | Uses office cost for simplicity |
| Shopping | Retail shopping center, high | 400 | Direct proxy |
| Multifamily housing | Multifamily, high | 390 | Shared by five housing archetypes |
| Hospital | General hospital, high | 1,200 | Hospital only; excludes clinics and pharmacies |
| School | Elementary, high: 750; high school, high: 850 | 800 | Simple average: (750 + 850) / 2 |
| Higher education/career training | University, high | 950 | University cost used as a proxy for the combined use |

### Estimates for the remaining active uses

The following **hard-cost estimates** complete the active 37-use catalog.
They are model judgments, not RLB quotes for those uses. Building rates are
USD per square foot of gross floor area. Outdoor rates are USD per square
foot of **improved site area**. All are preliminary Kendall Square proxies.

| Active use(s) | Hard cost ($/sq ft) | Basis for estimate |
|---|---:|---|
| Lab | 1,100 | Prime office 725 × 1.5 = 1,087.50, rounded to 1,100 for more demanding lab systems and fit-out. The 1.5 factor is a model judgment. |
| Childcare | 750 | RLB elementary-school high cost; similar classroom and child-serving space. |
| Library | 725 | Prime-office/civic high cost; assumes an urban enclosed public building. |
| Clinic | 850 | Prime office 725 + 125 for medical rooms and building systems. The $125 increment is a model judgment; the hospital's 1,200 would overstate a small clinic. |
| Pharmacy | 400 | RLB retail shopping-center high cost; excludes specialized pharmacy equipment and inventory. |
| Supermarket | 500 | Retail center 400 × 1.25 for refrigeration and heavier service systems. The 1.25 factor is a model judgment. |
| Convenience store, greengrocer, marketplace | 400 | RLB retail shopping-center high cost. |
| Bakery, butcher | 500 | Retail center 400 × 1.25 for food preparation, plumbing, and ventilation. The 1.25 factor is a model judgment. |
| Barber | 400 | RLB retail shopping-center high cost. |
| Cafe, restaurant, bar/pub | 500 | Retail center 400 × 1.25 for food-service fit-out and ventilation. The 1.25 factor is a model judgment. |
| Fitness/recreation | 550 | Retail center 400 + 150 for larger open spans, changing areas, and mechanical service. The $150 increment is a model judgment. |
| Cultural venue | 850 | RLB high-school high cost as a proxy for urban assembly space. Specialized theater equipment is excluded. |
| Park | 100 | Urban landscape/site-work estimate informed by the Cambridge park scale check below. |
| Playground | 175 | Park 100 × 1.75 for play equipment and impact-absorbing surfaces. The factor is a model judgment. |
| Outdoor sports | 125 | Park 100 × 1.25 for courts/fields and associated site work. The factor is a model judgment. |

For the outdoor scale check, a [Cambridge Planning Board
transcript](https://www.cambridgema.gov/-/media/Files/CDD/ZoningDevel/PlanningBoard/2010/pb_012610_transcript.pdf)
describes Rogers Street Park as about 2.2 acres and cites an $8 million park
construction contribution. That is about $84 per square foot in **2010**.
It is a historic contribution, not a 2026 hard-cost estimate or a clean
construction bid. The $100 park rate is a cautious urban-site allowance
chosen for this model; the playground and sports premiums are also choices.
No tower area is allowed for these outdoor uses. The model applies the
30% soft-cost assumption to their site-work hard costs as well.

The unused general `healthcare`, `leisure_indoor`, and `leisure_outdoor`
financial groups retain provisional fallback hard rates of **850**, **500**,
and **100** dollars per square foot respectively. The active clinic,
pharmacy, food, fitness, cultural, and outdoor uses use the more specific
rates above. These fallback values keep the 111-use reference catalog priced;
they are not independently sourced observations.

The [Boston input table](boston_construction_costs.json) also preserves the
other RLB categories transcribed from these pages. Direct mappings, blends,
and estimated hard rates are listed separately in that file.

**Provisional model choices:** Soft costs are 30% of hard costs. Tower hard
costs are 1.75 times plinth hard costs, and the same 30% soft-cost allowance
is applied to the adjusted tower cost. These two percentages are working
assumptions chosen for the model; RLB did not provide them. Change
`SOFT_COST_FRACTION` and `TOWER_COST_MULTIPLIER` in
[assumptions.py](assumptions.py) when better estimates are available.

## Land costs

**Transaction anchor:** The [Boston Globe's August 2018 report on 585 Third
Street](https://www.bostonglobe.com/business/2018/08/29/acre-lot-kendall-square-sells-for-more-than-million/c0ko8GWOLIgdmMAQGsrhxI/story.html)
reports an affiliate of BioMed Realty buying a nearly 36,000 sq ft Kendall
Square lot for $50.5 million. It also reports that a future development was
expected to include an arts or cultural component. The arts expectation is why
we treat the tower-permitted transaction price as amenity-inclusive; the
article does not assign a dollar value to that component.

**Derivation supplied for this model:** A working estimate of about 465,000
planned buildable sq ft gives $50.5M / 465,000 = about **$109 per buildable
sq ft**. The nearly 36,000 sq ft lot gives $50.5M / 36,000 = about **$1,400
per land sq ft**. The 465,000 sq ft denominator comes from the project team's
land-price derivation and has not been independently verified here.

For a plinth-only regime, the model applies the roughly $109 per buildable
sq ft to three to five stories: about **$330–$545 per land sq ft in 2018**.
For tower-permitted land, it starts with the full roughly $1,400 per land
sq ft transaction price. The team then used its **CoStar Kendall office
price-per-sq-ft series** as a market adjustment: about $413 in 2018 Q3 and
about $402 at the current observation, a ratio of about 0.97. This is an
office-property market proxy, not a lab-land series or a general inflation
index. The underlying CoStar extract and observation date are not stored in
this repository.

The model's chosen **2026-dollar land rates** are **$450 per sq ft of parcel
land** for `plinth_only` (also used for non-buildable land in that regime)
and **$1,340 per sq ft of parcel land** for `tower_permitted`. These are
rounded scenario estimates within the derivation, not exact products of a
single multiplier. The 2018 purchase preceded entitlement for the later
development, and the office-versus-lab comparison limits this proxy. Both
land rates are editable in [assumptions.py](assumptions.py).

## Amenity preferences

The [vote-weight snapshot](amenity_pref_order_votes.json) was fetched on
2026-10-02 at 22:18 UTC from the [VOLPE amenities endpoint](http://volpe.media.mit.edu:8123/api/amenities/pref_order).
It contains 37 normalized preference weights that sum to one. They are not
raw vote counts. The active amenity identifiers match the endpoint's names.
