# Preference compensation remains provisional

The scenario selects calibrated preference compensation by default. Use `--bonus-policy legacy` for the historical catalog formula. Changing the directory structure does not change these rules.

Preference is cardinal weight divided by the largest weight in the full saved snapshot, including inactive uses. It is not a resident-support percentage or ordinal rank.

For normalized preference `d`, compensation coverage is `min(1, (d / 0.60)^2)`. The premium is `0.15 × max(0, (d − 0.60) / 0.40)`, adjusted by the configured housing-block multiplier. These multiply financially calibrated compensation; preference policy does not add the legacy occupied-area refund again.

The default baseline is luxury housing alone. Individual minimum amenity packages are financially calibrated against this baseline before joint optimization. Housing thresholds are cumulative at 5, 10, 15, and 20 apartments; successive differences receive premiums of 100%, 75%, 50%, and 25%. Only complete blocks earn bonuses; further apartments may be built without bonus. Infeasible benchmarks and later blocks earn no compensation.

There is no default amenity-type limit. Nonhousing uses are limited to one facility/bay or minimum square-foot package, with housing, office, and lab exempt. Office/lab also have no per-use upper area or floor-equivalent limit; the total physical envelope still applies. Other uses retain their scenario and intrinsic size limits.

The calibration API/scenario can explicitly select all bonus-ineligible fillers. Office/lab profitability experiments use this baseline so boosted alternatives are reflected in opportunity cost. Construction and ongoing amenity costs remain developer-funded.

```powershell
python -m proforma preferences
python -m proforma --bonus-policy legacy
python -m proforma break-even
```

Preference diagnostics write a canonical optimization report and a separate calibration report referencing it. Isolated and reoptimized portfolio checks are retained. Legacy break-even analysis searches minimum single-amenity packages and is a different diagnostic from a simultaneous optimal compensation schedule.

Threshold, premium, normalization, supported housing blocks, package limits, and portfolio interactions remain open decisions. Individual benchmarks do not guarantee portfolio marginal profitability or selection in preference order. Original narratives are retained under `docs/history/`.
