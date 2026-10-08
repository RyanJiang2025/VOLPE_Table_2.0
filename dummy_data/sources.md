# Compact amenity scenario (current override)

## Bonus FAR stress testing

Run `python -m dummy_data.stress_test --output dummy_data/stress_test_results.json`
with SciPy installed. An isolated installation can be supplied with --solver-path.
The stress harness maximizes earned bonus, not financial surplus. It compares
current votes and equal maximum demand ratios, each with/without the tower cap.
For the equal-ratio case, assign 1/28 to each active bonus-eligible use and zero
to other snapshot entries; the unchanged reference normalization makes every
eligible demand ratio one. No vote file is modified.

Housing and indoor facilities may be allocated between the separate podium and
tower unless ground-level or tower-eligibility flags restrict placement. Facility
counts are whole, housing is zero or at least five apartments, and per-use
maximums aggregate repeated facilities. Shared ground-floor and outdoor limits
apply. Nonhousing floor equivalents use the actual podium/tower plate sizes.
Zero-bonus filler is excluded because it cannot improve the bonus objective.
Placements need not be unique; this is an area model without floor-plan packing,
common-area allowances, mandatory amenities, budgets, or financial optimization.
Solver optimality and allocation feasibility are checked before results are saved.


The tower now has an absolute MAX_TOWER_STORIES = 30 limit: 180,000 sq ft
at the current 6,000 sq ft footprint. Effective tower capacity is the lesser
of base-plus-bonus capacity and this physical limit. The separate five-story
podium retains its 20,000 sq ft capacity and its own construction rates.

The active catalog now has 33 uses. Hospital, school, full-size supermarket and outdoor
sports are excluded. Higher education/career training means a classroom-based
training centre. Identifiers
remain unchanged to preserve the original preference mapping, which is a proxy
for these narrowed services. The original 37-use vote snapshot is preserved,
and its reference weight remains fixed; inactive rows receive no allocation.

The tower plate is 6,000 sq ft, and each nonhousing indoor use is capped at
12,000 sq ft across the entire development, not per repeated facility. The
4,000 sq ft podium footprint separately caps ground-floor uses. Pocket park
and playground each have a 2,500 sq ft maximum and compete for one shared
2,500 sq ft open-space allotment. These areas use the model's simplified area
basis; no net-to-gross adjustment is added; the absolute tower cap applies.
All geometry and the five-apartment minimum are editable in assumptions.py.
Catalog defaults are checked against those assumptions at import time.
BONUS_FAR_AREA_SQFT is a compatibility alias for TOWER_FOOTPRINT_SQFT: one
bonus FAR grants one tower floor of area (currently 6,000 sq ft). It is not
an independently adjustable assumption. Indoor refunds use the same denominator.

All five housing defaults now contain five apartments, with a five-apartment
minimum; apartments remain indivisible. Facility variants remain whole
facilities: their default_unit_sqft and minimum match the smaller facility.
Libraries, cultural venues and other compact sizes are preliminary planning
assumptions; construction and maintenance rates retain their existing proxies.
The two catalog copies retain their pre-existing financial/bonus differences.

The building_use_example.py in the top-level dummy_data folder removes the
hospital, selects five apartments of each of its three subsidized housing
archetypes, five luxury apartments, a 10,000 sq ft lab and 12,000 sq ft office.
Unused allowable capacity is reported rather than filled beyond per-use caps.
Run `python dummy_data/building_use_example.py` from the repository root.

The historical notes below describe the earlier scenario and are superseded
by this section for catalog counts, sizes, bounds and example allocations.

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
- Existing office and retail inputs, soft-cost and
  tower multipliers, and land rates remain as copied. Missing commercial rates
  and public maintenance allowances are in assumptions.py's DUMMY dictionaries.
- Housing archetypes differ in unit area, annual per-unit rent, operating
  allowance, example program size, and hard construction cost. Housing rents
  now use the user's monthly scenario inputs converted to annual amounts:
  general $4,000, mid-career $5,000, senior $1,800, attainable $2,000, and
  luxury $7,000 per month. These replace the copied low annual rent inputs.
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
| General | 995 | 48,000 | 40% | 390 |
| Mid-career | 1,100 | 60,000 | 38% | 410 |
| Senior | 800 | 21,600 | 45% | 420 |
| Attainable | 750 | 24,000 | 42% | 350 |
| Luxury | 1,250 | 84,000 | 35% | 480 |

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
demand_FAR_Bonus = FAR_BONUS_SCALE * (amenity_pref_order / reference_weight)
            * (square_footage / FAR_BONUS_REFERENCE_AREA_SQFT)
            / (1 + exp(NOI_per_sqft / FAR_BONUS_NOI_PER_SQFT_SCALE))
footprint_refund_FAR = square_footage / BONUS_FAR_AREA_SQFT  # indoor only
FAR_Bonus = demand_FAR_Bonus + footprint_refund_FAR
```

The scenario uses `BONUS_FAR_AREA_SQFT = TOWER_FOOTPRINT_SQFT`: one bonus FAR adds 6,000
sq ft of tower floor area. Eligible indoor uses receive their occupied **total floor
area**, rather than just its ground footprint, back through this conversion,
plus the existing demand bonus. Park, playground, and outdoor sports receive
only the existing demand bonus. The catalog exposes both bonus components.
Lab, general office, coworking, commercial services, and luxury housing are
designated for-profit uses and receive zero demand bonus and zero floor-area
refund.
For actual selected areas, pass `amenity_type` to `far_bonus_for_use`, along
with `indoor=True` for indoor uses; leave `indoor=False` for outdoor uses.
Keep the conversion consistent
with the development's bonus-capacity calculation.

Office, lab, and luxury housing filler consume capacity without generating further capacity,
so a fixed selected amenity program has a finite remainder for these uses.
Repeatedly adding eligible indoor amenities can still grow capacity; development
allocation must enforce selected-program bounds and any building-size cap.

## Building-use example allocation

Run `python ProForma/dummy_data/building_use_example.py` to regenerate
`building_use_example.json`. The example keeps hospital and mid-career, general,
and attainable housing at their catalog example areas in the tower. Senior
housing has been replaced with one 1,500-sq-ft cafe and one 2,500-sq-ft greengrocer
grocery store, filling the 4,000-sq-ft ground floor. These selected amenities earn
bonuses at their actual areas. The user-selected playground is one facility resized to 2,500
sq ft, occupying the entire open-space allotment. This exceeds its 2,000-sq-ft
minimum; its demand bonus and economics are recomputed at the selected area.

After summing these selected amenities' bonuses once, the example allocates the
remaining indoor space to office while preserving the previous 60,280.993524182064
sq ft of lab and 48 luxury apartments (60,000 sq ft). Office fills the remaining
16,000 sq ft of podium and the rest of the tower. The total capacity is
recomputed after removing senior housing's bonus and adding the cafe and grocery
store bonuses; senior housing's previous 80,000 sq ft is not retained as an
independent capacity allowance.

reference_weight is the largest weight in the copied snapshot. Defaults in
assumptions.py are FAR_BONUS_SCALE = 2.0, reference area = 10,000 sq ft, and
NOI scale = 100 USD/sq ft/year. These are adjustable dummy choices. Bonuses
are absolute FAR increments; 2.0 is a coefficient, not a maximum bonus.
There is no subsidy eligibility cutoff or per-use bonus cap. Minimum program
sizes describe program assembly only; they do not gate subsidy calculations.
Zero program area yields zero bonus. Negative areas are rejected.

Holding demand and NOI per sq ft fixed, doubling area doubles the bonus.
For example, with the highest demand weight and NOI of 20 USD/sq ft/year,
a 1,000-sq-ft cafe receives approximately 0.0900 demand FAR plus 0.1667 refund
FAR; a 2,000-sq-ft cafe receives 0.1801 demand FAR plus 0.3333 refund FAR.
Splitting a program into identical smaller programs
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
indicative construction-cost tables on PDF pages 10Ã¢â‚¬â€œ11. We use the **high**
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
| Lab | 1,100 | Prime office 725 Ãƒâ€” 1.5 = 1,087.50, rounded to 1,100 for more demanding lab systems and fit-out. The 1.5 factor is a model judgment. |
| Childcare | 750 | RLB elementary-school high cost; similar classroom and child-serving space. |
| Library | 725 | Prime-office/civic high cost; assumes an urban enclosed public building. |
| Clinic | 850 | Prime office 725 + 125 for medical rooms and building systems. The $125 increment is a model judgment; the hospital's 1,200 would overstate a small clinic. |
| Pharmacy | 400 | RLB retail shopping-center high cost; excludes specialized pharmacy equipment and inventory. |
| Supermarket | 500 | Retail center 400 Ãƒâ€” 1.25 for refrigeration and heavier service systems. The 1.25 factor is a model judgment. |
| Convenience store, greengrocer, marketplace | 400 | RLB retail shopping-center high cost. |
| Bakery, butcher | 500 | Retail center 400 Ãƒâ€” 1.25 for food preparation, plumbing, and ventilation. The 1.25 factor is a model judgment. |
| Barber | 400 | RLB retail shopping-center high cost. |
| Cafe, restaurant, bar/pub | 500 | Retail center 400 Ãƒâ€” 1.25 for food-service fit-out and ventilation. The 1.25 factor is a model judgment. |
| Fitness/recreation | 550 | Retail center 400 + 150 for larger open spans, changing areas, and mechanical service. The $150 increment is a model judgment. |
| Cultural venue | 850 | RLB high-school high cost as a proxy for urban assembly space. Specialized theater equipment is excluded. |
| Park | 100 | Urban landscape/site-work estimate informed by the Cambridge park scale check below. |
| Playground | 175 | Park 100 Ãƒâ€” 1.75 for play equipment and impact-absorbing surfaces. The factor is a model judgment. |
| Outdoor sports | 125 | Park 100 Ãƒâ€” 1.25 for courts/fields and associated site work. The factor is a model judgment. |

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
sq ft to three to five stories: about **$330Ã¢â‚¬â€œ$545 per land sq ft in 2018**.
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
