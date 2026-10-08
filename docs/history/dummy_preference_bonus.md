# Provisional preference bonus experiment

Run `python -m dummy_data.preference_bonus` with requirements.txt installed.
This writes preference_bonus_results.json containing the frozen schedule,
isolated amenity comparisons, luxury-only baseline, and optimized allocation.
The original financial_optimizer entry point and example catalog retain the
legacy formula for comparison; the new experiment explicitly replaces those
bonuses before solving. It uses development profit, including developer-funded
construction and capitalized operating liabilities, at the provisional 4.5% rate.

Preference is the cardinal voting weight divided by the largest weight in the
saved snapshot, including inactive uses. It measures relative preference, not
resident support percentages. No conversion to ordinal ranks is used.

For score d, compensation coverage is min(1, (d/0.60)^2). The extra premium is
0.15 * max(0, (d-0.60)/0.40). These multiply financially calibrated compensation;
there is no additional area refund. Nonhousing uses earn bonus proportionally
to quantity, subject to existing size and placement limits. Benchmarks use the
minimum package plus luxury filler and are frozen before joint optimization.

Housing compensation is calibrated cumulatively at 5, 10, 15, and 20 apartments.
Successive benchmark differences determine block compensation. Premiums decline
to 100%, 75%, 50%, and 25% of the preference premium across these blocks.
Only complete blocks earn bonuses. Further apartments may be built without bonus.
If a benchmark cannot break even within the height cap, that package and later
blocks earn no bonus and are flagged infeasible in the schedule.

There is no amenity-type limit. Each nonhousing use is limited to one facility
or commercial bay per plot; housing, general office, and lab are exempt. Uses
measured continuously in square feet are limited to one minimum program package,
rather than one square foot. These limits apply across podium and tower together.
The developer chooses the mix endogenously within these limits and the existing
30-story height limit. This replaces the provisional five-type limit following
the comparison of the one-per-type scenarios with and without that limit.
Office and lab also have no per-use upper area or floor-equivalent limits;
their solver bounds are the total physical building envelope. Their minimum
selected areas (5,000 and 10,000 sqft) remain. Other nonhousing uses retain their
existing size limits. Office/lab profitability tests recalibrate compensation
against the best mix of all bonus-ineligible uses, including the boosted use.

TODO: revisit threshold, premium, one-unit limit, supported housing quantity,
premium decline, and cardinal normalization. Consider endogenous portfolio size
through a finite total bonus budget or diminishing community benefit rather than
a type cap. Calibrate cap rates and omitted development costs before policy use.
Individual benchmarks do not guarantee portfolio marginal profitability or that
preference ranking determines selection. Bundle interactions are deliberately
outside this demo's calibration scope; isolated comparisons are exported so
low-preference outcomes remain visible. Extra FAR is not a guaranteed profit margin.
