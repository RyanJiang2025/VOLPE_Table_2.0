# VOLPE ProForma

The active model selects a building program using shared financial inputs, parcel constraints, and either calibrated preference bonuses or the historical bonus formula.

Start with **[config/scenarios/default.json](config/scenarios/default.json)**. It selects four shared input files and contains the parcel, financial objective, bonus policy, selection rules, and solver settings. [Configuration guide](docs/configuration.md) explains their relationships and units.

## Setup

From this checkout, create an environment and install the package in editable mode:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\Activate.ps1
```

The dependencies are declared once in `pyproject.toml`. Editable installation keeps the checkout's `config/` files authoritative and makes `proforma` importable from other working directories. Built packages also include the default configuration and reference dataset; new results are written under the working directory when using an installed package outside this checkout.

The existing `.solver-deps/` installation is preserved. To use it without installing dependencies:

```powershell
$env:PYTHONPATH = (Join-Path $PWD 'src')
python -m proforma --solver-path .solver-deps
```

## Run the model

```powershell
python -m proforma
python -m proforma --bonus-policy legacy
python -m proforma --objective annual-surplus
python -m proforma --objective annual-surplus --sensitivity
python -m proforma --require library=1 --budget 50000000
python -m proforma --scenario config/scenarios/default.json
python -m proforma --fetch_pref_order
python -m proforma --fetch_pref_order --sample=100
```

Preferences default to the local snapshot. `--fetch_pref_order` fetches
`http://volpe.media.mit.edu:8123/api/amenities/pref_order` for this run only;
`--sample=N` adds `?n=N` (a positive integer) and is ignored without the fetch flag.
The local snapshot is never overwritten. Fetch or validation failures stop the run
rather than silently falling back. The manifest preserves the fetched weights,
source URL, and response hash.

The CLI uses the scenario's explicit objective: currently provisional `development-profit`. The compatibility Python API `proforma.pipeline.optimize()` retains its previous `annual-surplus` default. `proforma.pipeline.run(config)` uses the configured objective. `proforma.optimizer.optimize(programs, scenario, ...)` is the solver for explicit inputs and does not read configuration or select policy.

Each command writes a fresh `results/<run-id>/` directory containing a report and `manifest.json`. The manifest records resolved inputs, source hashes, code revision and dirty state, and dependency versions. `--output-dir PATH` chooses a new run directory; `--output PATH.json` writes one report plus a manifest sidecar.

## Analysis, examples, and experiments

Run these from the checkout after editable installation (or with `PYTHONPATH` set as above):

```powershell
python -m proforma preferences
python -m proforma break-even
python -m examples.building_use
python -m experiments.preference_monte_carlo --trials 10 --seed 7
python -m experiments.preference_monte_carlo --winner general_office
python -m experiments.preference_monte_carlo --winner lab
python -m experiments.stress_test
python -m experiments.uncapped_amenities
```

`preferences` writes separate optimization and calibration reports, avoiding a duplicate embedded optimization result. The prescribed building example and bonus-maximization stress test use the legacy formula for comparison. The Monte Carlo experiment uses calibrated preference compensation, with hypothetical voting weights and optional office/lab profitability overrides. Every experiment uses the shared model package.

Solver-based commands and experiments accept `--solver-path .solver-deps` when using the preserved isolated dependencies. All examples and experiments accept `--scenario` and `--output`.

## Project layout

| Location | Purpose |
|---|---|
| `src/proforma/` | One shared model implementation |
| `config/` | Four shared input datasets and the scenario entry point |
| `reference/` | The 111-row historical taxonomy; loaded only when requested |
| `examples/` | Prescribed building allocation |
| `experiments/` | Monte Carlo, bonus stress, and uncapped comparisons |
| `results/` | Generated run artifacts; old outputs are preserved in `results/history/` |
| `docs/` | Configuration, provenance, limitations, and unresolved policy decisions |
| `tests/` | Independent small financial checks and pre-reorganization regression snapshots |

## Verify

```powershell
python -B tests/run.py
# With the existing isolated dependencies:
python -B tests/run.py --solver-path .solver-deps
```

See [reorganization notes](docs/reorganization.md) for the migration record, [sources](docs/sources.md) for input provenance, and [limitations](docs/limitations.md) for unresolved modeling decisions. The numerical defaults remain synthetic/provisional; the reorganization does not settle the financial objective or bonus-policy decisions.
