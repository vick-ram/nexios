#!/usr/bin/env python3
"""Run the test suite"""

import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Run pytest with custom arguments"""
    # Run tests
    args = [
        "-v",  # Verbose
        "--tb=short",  # Short traceback
        "-x",  # Stop on first failure
        # "--cov=nexios",  # Coverage (if pytest-cov installed)
        # "--cov-report=html",  # HTML coverage report
        "nexios/orm/tests"
    ]

    # Add specific test file/class if provided
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    return pytest.main(args)


if __name__ == "__main__":
    sys.exit(main())