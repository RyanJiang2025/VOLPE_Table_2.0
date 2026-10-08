# Pending decision: financial objective

We will return to compare annual surplus and valuation-based development profit
and choose which one should guide the project. Neither objective is a settled
policy choice. Development profit is the provisional CLI default; the Python
API retains its annual-surplus default for compatibility with existing callers.

The shared optimizer supports both:

```powershell
python -m dummy_data.financial_optimizer --objective development-profit --cap-rate 0.045 --output dummy_data/valuation_optimizer_result.json
python -m dummy_data.financial_optimizer --objective annual-surplus --output dummy_data/financial_optimizer_result.json
python -m dummy_data.financial_optimizer --objective annual-surplus --sensitivity
```

Both runs report annual NOI, annual surplus at the required return, completed
value, development profit, and profit on development cost for their chosen
allocation. Objective values have different units: annual dollars versus dollars
of estimated development profit. They must not be compared directly.

Annual surplus = NOI - required return * development cost.
Development profit = sum(NOI by use / capitalization rate by use) - development cost.

The shared 4.5% capitalization rate in assumptions.py is an illustrative,
unvalidated scenario, not a researched Boston/Cambridge market estimate.
Program.capitalization_rate can override it for an individual use. Required
return remains 6% and does not enter the valuation objective. No additional
minimum profit-margin constraint is imposed; maximize absolute profit.

Negative NOI is capitalized as an ongoing maintenance liability. Thus reported
completed value is net of these obligations, not just the market sale value of
rentable space. This is a simplifying perpetual-obligation assumption and must
be reviewed for public amenities, ownership transfers, and subsidy arrangements.
User clarification: all amenity construction and ongoing operating costs must
remain with the developer, to fiscally help the city. Do not assume city-funded
operations or transfer operating liabilities to the city in this scenario.
Do not clip negative NOI to zero or add annual NOI again to capitalized value.

Development cost currently includes hard/soft construction and optional land
(--include-land). Budget and physical/FAR constraints are shared across both
objectives. Land is excluded by default. Financing, construction timing,
lease-up, vacancy, selling costs, and net-to-gross efficiency are not yet modeled.

Before choosing an objective: calibrate capitalization rates by use, rental
efficiency, vacancy, full development costs, and treatment of amenity obligations;
compare the selected allocations and run capitalization-rate sensitivities.

Initial illustrative valuation run (4.5%, land excluded): 16 luxury apartments
in the 20,000 sq ft podium and 24 in the 30,000 sq ft tower, five stories in
each zone. No bonus amenities selected. Estimated net completed value is
$60.667 million, development cost $45.240 million, and development profit
$15.427 million. These are scenario outputs before the omitted costs above,
not a market feasibility conclusion. Saved in valuation_optimizer_result.json.

Per-amenity break-even analysis: run `python -m dummy_data.amenity_break_even`.
Results are saved in amenity_break_even_results.json. Each comparison requires
exactly the minimum package of one amenity, permits luxury housing as filler,
and optimizes placement and whole apartments. Other amenities are excluded to
isolate each incentive. It searches the total FAR bonus needed to match the
luxury-only baseline profit, including operating liabilities and displaced
housing. These thresholds are not a simultaneous optimal bonus schedule.
