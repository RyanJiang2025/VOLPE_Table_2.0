"""Run tests directly from this checkout, optionally using isolated dependencies."""
import argparse
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--solver-path", type=Path)
args = parser.parse_args()
sys.path[:0] = [str(root / "src"), str(root)]
if args.solver_path:
    sys.path.insert(0, str(args.solver_path.resolve()))
suite = unittest.defaultTestLoader.discover(str(root / "tests"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
