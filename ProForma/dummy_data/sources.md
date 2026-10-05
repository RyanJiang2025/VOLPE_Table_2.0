# Dummy dataset assumptions

This folder is a synthetic working copy. Added values are model examples, not
researched market observations. The original source notes below describe the
copied baseline; this section takes precedence for dummy-folder overrides.

- All 37 active uses have typical program areas, default unit/bay/facility
  sizes, and minimum/maximum total program areas in demo_buildable_use_data.json.
  These are illustrative choices, not architectural requirements. Indoor areas
  use a simplified single area basis without a net-to-gross adjustment; outdoor
  areas represent improved site area. Square-foot programs use a one-sq-ft unit.
- FAR_Bonus remains a null runtime placeholder in the input JSON. The active
  catalog computes its value from the copied preference snapshot and annual NOI;
  see the subsidy formula below.
- Public/community uses here include schools, higher education/training,
  childcare, library, community centre, government operations, place of worship,
  post office, cultural venue, park, playground, and outdoor sports.
  They have zero revenue and direct annual maintenance costs per sq ft.
  upkeep_fraction_of_rent is intentionally inapplicable (NaN), not missing
  maintenance data. Their annual NOI is consequently negative, increasing
  their FAR subsidy factor.
- Hospitals and clinics are treated as commercial facilities for this example.
  Their rent represents space revenue, not healthcare operating revenue.
- Existing office and retail inputs, general housing baseline, soft-cost and
  tower multipliers, and land rates remain as copied. Missing commercial rates
  and public maintenance allowances are in assumptions.py's DUMMY dictionaries.
- Housing archetypes differ in unit area, annual per-unit rent, operating
  allowance, example program size, and hard construction cost. Annual rents
  deliberately retain the original annual-period convention, including the
  low $4,045 general housing baseline; no monthly conversion is applied.
- Four synthetic housing construction rates override the copied shared rate:
  mid-career 410, senior 420, attainable 350, and luxury 480 USD/sq ft.
  General housing retains 390 USD/sq ft.
- The active 37-use catalog is the populated example dataset. The 111-row
  reference taxonomy still has unallocated areas and legacy FAR placeholders;
  it shares the updated financial rates but is not a populated example program.
- Hotel/student inputs remain outside the active catalog. No new uses were added.

## Housing dummy inputs

| Archetype | Unit sq ft | Annual rent/unit | Opex | Hard cost/sq ft |
|---|---:|---:|---:|---:|
| General | 995 | 4,045 | 40% | 390 |
| Mid-career | 1,100 | 4,600 | 38% | 410 |
| Senior | 800 | 3,600 | 45% | 420 |
| Attainable | 750 | 2,800 | 42% | 350 |
| Luxury | 1,250 | 6,500 | 35% | 480 |

## Per-amenity yield on cost

`yield_on_cost = NOI_yearly / construction_cost` is calculated in both catalogs.
Construction cost includes hard and soft costs; land, financing, taxes, and FAR
benefits are excluded. The stored value is a decimal ratio: 0.08 means 8% annually.
Public/community amenities have negative yields because revenue is zero and
maintenance is positive. Zero-cost/unallocated programs have an undefined yield
(NaN); this applies to the unallocated reference catalog.

This metric does not change the FAR formula or calculate a required-return
surplus. Any extra building use enabled by FAR is evaluated through its own NOI
and construction cost when included in a development. Aggregate yields should
be calculated from combined NOI divided by combined costs, not summed.

## FAR subsidy formula

amenity_pref_order_votes.json is an exact copy of the original 37-use snapshot.
Its numbers are normalized demand weights, not rank positions or raw vote counts.
The active catalog exposes these weights as amenity_pref_order.

```
NOI_per_sqft = NOI_yearly / square_footage
FAR_Bonus = FAR_BONUS_SCALE * (amenity_pref_order / reference_weight)
            * (square_footage / FAR_BONUS_REFERENCE_AREA_SQFT)
            / (1 + exp(NOI_per_sqft / FAR_BONUS_NOI_PER_SQFT_SCALE))
```

reference_weight is the largest weight in the copied snapshot. Defaults in
assumptions.py are FAR_BONUS_SCALE = 2.0, reference area = 10,000 sq ft, and
NOI scale = 100 USD/sq ft/year. These are adjustable dummy choices. Bonuses
are absolute FAR increments; 2.0 is a coefficient, not a maximum bonus.
There is no subsidy eligibility cutoff or per-use bonus cap. Minimum program
sizes describe program assembly only; they do not gate subsidy calculations.
Zero program area yields zero bonus. Negative areas are rejected.

Holding demand and NOI per sq ft fixed, doubling area doubles the bonus.
For example, with the highest demand weight and NOI of 20 USD/sq ft/year,
a 1,000-sq-ft cafe receives approximately 0.0900 FAR and a 2,000-sq-ft cafe
receives 0.1801 FAR. Splitting a program into identical smaller programs
preserves their combined bonus when they share the same economics and demand.
Holding area and NOI fixed, higher demand increases the bonus. Holding area
and positive demand fixed, lower NOI increases the bonus. Public/community
uses have negative NOI per sq ft, increasing their subsidy factor.

Indoor area means program floor area; outdoor area means dedicated improved
site area. Outdoor amenities are intended to use separate open-space allotments,
not consume buildable floor capacity. This catalog calculates bonuses but does
not implement allocation constraints. No four-floor open-space bonus is applied.

The formula does not value bonus space, determine financial subsidy equivalence,
or enforce parcel-level zoning caps. Combining bonuses and converting them
into buildable capacity remain development-level decisions. The 111-use reference
taxonomy is not assigned bonuses. JSON null values in the active input file are
runtime placeholders overwritten in the assembled active catalog.

## Copied baseline source notes

# ProForma sources and assumptions

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
