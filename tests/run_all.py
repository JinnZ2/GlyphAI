#!/usr/bin/env python3
"""Run every test module in this directory.

Usage: python tests/run_all.py
Exits non-zero if any test fails.
"""

import os
import sys
import glob
import traceback
import importlib.util

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(TESTS_DIR))


def load_module(path):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    paths = sorted(glob.glob(os.path.join(TESTS_DIR, "test_*.py")))
    passed, failures = 0, []

    for path in paths:
        module = load_module(path)
        tests = [v for k, v in sorted(vars(module).items())
                 if k.startswith("test_") and callable(v)]
        print(f"\n{os.path.basename(path)} ({len(tests)} tests)")
        for test in tests:
            try:
                test()
            except Exception:
                failures.append((os.path.basename(path), test.__name__,
                                 traceback.format_exc()))
                print(f"  FAIL  {test.__name__}")
            else:
                passed += 1
                print(f"  ok    {test.__name__}")

    print("\n" + "=" * 50)
    if failures:
        for module_name, test_name, tb in failures:
            print(f"\n--- {module_name}::{test_name} ---\n{tb}")
        print(f"{passed} passed, {len(failures)} FAILED")
        return 1
    print(f"All {passed} tests passed across {len(paths)} modules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
