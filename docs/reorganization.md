# Reorganization record

The project now has one shared implementation in `src/proforma/`, four shared input datasets plus a scenario entry point in `config/`, and separate examples, experiments, reference taxonomy, results, and documentation.

## Preserved evidence

- All 52 original root/dummy files are accounted for in [reorganization_map.json](reorganization_map.json), including original SHA-256 hashes and destination paths.
- All 20 prior saved result files are preserved byte-for-byte under `results/history/`; their archive paths and hashes are recorded in `results/history/index.json`.
- The seven previous source/decision/checklist narratives are retained verbatim under `docs/history/`. Their old commands and paths are historical, not current instructions.
- `tests/fixtures/before_reorganization.json` was captured from the old implementation **before** creating the new package. It records raw and calibrated programs, both policies under both objectives, financial groups, the reference catalog, prescribed example, and legacy break-even results.
- A complete local backup of the original root files, dummy folder, and tests was taken at `C:\Users\dukef\AppData\Local\Temp\proforma-before-reorganization-0jwe05i7`. It excludes dependency installations, Git internals, and Python caches. This is a local rollback copy, separate from the versioned historical evidence.

## Verification

The original 35 tests passed before migration. All **51** migrated and expanded tests pass. Tests now exercise the shared package rather than a duplicate dummy implementation. Additional checks cover configuration relationships, immutable inputs, dynamic housing-size conversion and scenario bounds, complete voting normalization, result manifests, command execution from another working directory, and safe calibration-threshold reuse.

Default resolved programs, financial groups, reference rows, calibration schedule, break-even results, and both policies under both objectives match the captured baseline within numerical tolerances. The prescribed example retains its numerical allocation and totals. Separate before/after comparisons verified all stress-test cases, the uncapped experiment, and two seeded Monte Carlo trials each for default, office-profitability, and lab-profitability scenarios.

Smoke checks passed for default optimization, preference diagnostics, break-even analysis, return sensitivity, the example, and all three experiment commands. The regenerated default allocation and totals match the pre-migration baseline exactly. All 20 archived result hashes were rechecked after deleting the duplicate originals. A local wheel build and a temporary installation were verified from outside the checkout, including bundled configuration/reference data and a legacy-baseline solve. No dependencies were downloaded or installed into the user's Python environment.

## Intentional structural changes

- No algorithm imports `dummy_data` or the former root modules. The duplicate implementations are retired.
- Configuration values have named fields and explicit units. Derived capacities, NOI, costs, and bonuses are calculated at runtime.
- Dataset paths are relative to the selected scenario rather than the code file or current shell directory.
- The solver receives explicit programs and a scenario. Policy calibration can call it, but it does not import policy calibration.
- The 111-row reference taxonomy is not processed during normal optimization.
- Generated outputs are grouped by run; preference diagnostics reference a canonical optimization result instead of embedding another copy.
- Financial threshold reuse in Monte Carlo scenarios is keyed by complete immutable financial/scenario inputs and is tested against uncached results.
- Small scenarios can exclude programs whose minimum package cannot fit rather than failing because a descriptive example area exceeds the scenario envelope.

The financial objective, capitalization rate, bonus formula, and policy choices remain provisional. Existing numerical defaults, the complete 37-identifier vote snapshot, developer-funded maintenance treatment, and the compatibility API's annual-surplus default are preserved.

Start with [the README](../README.md) and [configuration guide](configuration.md). Dependencies are declared in `pyproject.toml`; the existing isolated `.solver-deps/` installation is retained.
