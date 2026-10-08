"""Run the VOLPE development model and write results with input provenance."""
import argparse
import json
from pathlib import Path
import sys

from .config import load_config
from .models import Scenario


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("optimize", "preferences", "break-even"), default="optimize")
    parser.add_argument("--scenario", type=Path, help="Scenario JSON; referenced files resolve relative to it")
    parser.add_argument("--objective", choices=("annual-surplus", "development-profit"))
    parser.add_argument("--bonus-policy", choices=("preference", "legacy"))
    parser.add_argument("--cap-rate", type=float)
    parser.add_argument("--required-return", type=float)
    parser.add_argument("--include-land", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--budget", type=float)
    parser.add_argument("--require", action="append", default=[], metavar="USE=QUANTITY")
    parser.add_argument("--sensitivity", action="store_true", help="Compare 4%%, 6%% and 8%% annual required returns")
    parser.add_argument("--time-limit", type=float)
    parser.add_argument("--solver-path", type=Path, help="Optional isolated scipy installation")
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument("--output", type=Path, help="Explicit JSON file; writes a sibling manifest")
    outputs.add_argument("--output-dir", type=Path, help="New run directory; must not already exist")
    args = parser.parse_args(argv)
    if args.solver_path:
        sys.path.insert(0, str(args.solver_path.resolve()))
    try:
        config = load_config(args.scenario)
        finance = {key: value for key, value in {
            "objective": args.objective, "capitalization_rate": args.cap_rate,
            "required_return": args.required_return, "include_land": args.include_land,
            "development_budget_usd": args.budget}.items() if value is not None}
        bonus = {"policy": args.bonus_policy} if args.bonus_policy else {}
        solver = {"time_limit_seconds": args.time_limit} if args.time_limit is not None else {}
        config = config.with_overrides(finance=finance, bonuses=bonus, solver=solver)
        required = {}
        for item in args.require:
            name, quantity = item.split("=", 1)
            if name in required:
                raise ValueError(f"Duplicate required use: {name}")
            required[name] = float(quantity)
        from .pipeline import run, write_run
        metadata = {"required_quantities": required}
        if args.command != "optimize":
            if required or args.sensitivity:
                raise ValueError("--require and --sensitivity apply only to optimize")
            if args.objective not in (None, "development-profit"):
                raise ValueError("Financial diagnostics use development-profit")
            from .analysis import break_even_report, preference_report
            policy = "preference" if args.command == "preferences" else "legacy"
            if args.bonus_policy is not None and args.bonus_policy != policy:
                raise ValueError(f"{args.command} uses the {policy} policy")
            config = config.with_overrides(finance={"objective": "development-profit"}, bonuses={"policy": policy})
            if args.command == "preferences":
                report = preference_report(config)
                result = report.pop("result")
                report["optimization_reference"] = "optimization.json"
                reports = {"optimization.json": result, "calibration.json": report}
                if args.output:
                    raise ValueError("preferences produces multiple reports; use --output-dir")
            else:
                result = break_even_report(config)
                reports = {"break_even.json": result}
        elif args.sensitivity:
            if args.required_return is not None or config.data["finance"]["objective"] != "annual-surplus":
                raise ValueError("Sensitivity requires annual-surplus and no explicit --required-return")
            variants = [config.with_overrides(finance={"required_return": rate}) for rate in (.04, .06, .08)]
            result = [run(variant, required_quantities=required) for variant in variants]
            reports = {"sensitivity.json": result}
            metadata["scenario_variants"] = [variant.resolved()["scenario"] for variant in variants]
        else:
            result = run(config, required_quantities=required)
            reports = {"optimization.json": result}
        manifest = write_run(reports, config, command=args.command, output=args.output,
                             output_dir=args.output_dir, metadata=metadata)
    except (ValueError, ImportError, OSError) as error:
        parser.error(str(error))
    if isinstance(result, list):
        summary = [{k: v for k, v in item.items() if k != "allocation"} for item in result]
        success = all(item["status"] == "optimal" for item in result)
    else:
        summary = {k: v for k, v in result.items() if k not in ("allocation", "amenities")}
        success = result.get("status", "optimal") == "optimal"
    print(json.dumps(summary, indent=2, allow_nan=False))
    print("Manifest:", manifest)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
