# Financial objective remains provisional

The scenario/CLI currently selects `development-profit`. The compatibility Python API retains its existing `annual-surplus` default. This reorganization does not decide which objective should govern the project.

Both objectives share the same physical, budget, and whole-unit constraints:

- Annual surplus = annual NOI − required annual return × development cost.
- Development profit = sum of annual NOI divided by each use's capitalization rate − development cost.

The default required return is 6%, capitalization rate 4.5%, and land is excluded. These values are scenario settings; the cap rate remains illustrative and unvalidated. Required return does not enter the development-profit objective. There is no additional minimum profit-margin constraint.

Negative NOI represents ongoing developer-funded maintenance and is capitalized as a liability. Do not clip it to zero, add annual NOI again to capitalized value, or transfer amenity operating costs to the city. Valuation is an estimate, not an additional cash receipt.

Compare objectives with:

```powershell
python -m proforma --objective development-profit
python -m proforma --objective annual-surplus
python -m proforma --objective annual-surplus --sensitivity
```

Each report includes both financial measures for its chosen allocation. Objective values have different units (annual USD versus estimated development-profit USD), so compare allocation consequences and assumptions rather than directly comparing objective magnitudes.

Before choosing an objective, calibrate use-specific cap rates, rental efficiency, vacancy, complete costs, and the ownership treatment of public obligations. The old financial-objective narratives, including historical luxury-only results, remain in `docs/history/`; the original saved results remain in `results/history/`.
