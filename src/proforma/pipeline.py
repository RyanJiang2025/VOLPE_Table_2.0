"""Coordinate policy and solving, and write reproducible run artifacts."""
from __future__ import annotations

from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import subprocess
from uuid import uuid4

from . import bonuses
from .catalog import catalog_programs
from .config import PROJECT_ROOT, load_config, thaw
from .models import Scenario
from .optimizer import optimize as solve


def optimize(programs=None, scenario=None, required_quantities=None, time_limit=None,
             objective="annual-surplus", max_amenity_types=None, bonus_policy="preference",
             *, config=None, relative_gap=None, threshold_cache=None):
    """Compatibility API: annual surplus by default; policy orchestration lives here.

    The CLI and run() use the selected scenario's explicit objective instead.
    For an I/O-free solve of explicit inputs, use proforma.optimizer.optimize.
    """
    config = config or load_config()
    scenario = scenario or Scenario.from_config(config)
    if bonus_policy not in ("preference", "legacy"):
        raise ValueError("Unknown bonus policy")
    options = config.solver_options
    if time_limit is not None:
        options["time_limit"] = time_limit
    if relative_gap is not None:
        options["relative_gap"] = relative_gap
    provided = programs is not None
    if programs is None:
        programs = catalog_programs(config=config, scenario=scenario)
        if bonus_policy == "preference":
            policy = bonuses.BonusPolicy.from_config(config)
            programs, _, _ = bonuses.calibrate(scenario, config.weights, programs, policy=policy,
                                               solver_options=options, threshold_cache=threshold_cache)
            if max_amenity_types is None:
                max_amenity_types = policy.maximum_amenity_types
    report = solve(programs, scenario, required_quantities, objective=objective,
                   max_amenity_types=max_amenity_types, **options)
    report["bonus_policy"] = "provided" if provided else bonus_policy
    return report


def run(config=None, *, required_quantities=None):
    config = config or load_config()
    return optimize(config=config, required_quantities=required_quantities,
                    objective=config.data["finance"]["objective"], bonus_policy=config.data["bonuses"]["policy"])


def _git_state():
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
                                  text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, capture_output=True,
                                    text=True, check=True).stdout.strip())
        return {"revision": revision, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"revision": None, "dirty": None}


def write_run(reports, config, *, command, output_dir=None, output=None, metadata=None):
    """Write one fresh run directory. An explicit output file gets a manifest sidecar."""
    if output_dir is not None and output is not None:
        raise ValueError("Choose output_dir or output")
    now = datetime.now(timezone.utc)
    if output is not None:
        if len(reports) != 1:
            raise ValueError("A single output file requires exactly one report")
        destination = Path(output).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        paths = {next(iter(reports)): destination}
        manifest_path = destination.with_name(destination.stem + ".manifest.json")
    else:
        directory = Path(output_dir) if output_dir is not None else PROJECT_ROOT / "results" / (now.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8])
        directory = directory.resolve()
        directory.mkdir(parents=True, exist_ok=False)
        paths = {name: directory / name for name in reports}
        manifest_path = directory / "manifest.json"
    dependencies = {}
    for package in ("numpy", "pandas", "scipy"):
        try:
            dependencies[package] = version(package)
        except PackageNotFoundError:
            dependencies[package] = None
    manifest = {"schema_version": 1, "created_at_utc": now.isoformat(), "command": command,
                "source_hashes": thaw(config.source_hashes), "resolved_configuration": config.resolved(),
                "code": _git_state(), "dependencies": dependencies,
                "reports": {name: path.name for name, path in paths.items()}, "run_parameters": metadata or {}}
    # Serialize every artifact first so invalid numerical output never creates a partial report set.
    serialized = {name: json.dumps(value, indent=2, allow_nan=False) + "\n" for name, value in reports.items()}
    manifest_text = json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    for name, path in paths.items():
        path.write_text(serialized[name], encoding="utf-8")
    manifest_path.write_text(manifest_text, encoding="utf-8")
    return manifest_path
