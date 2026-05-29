"""Pytest configuration — set AGH_DATA_DIR before server module import side effects."""

from __future__ import annotations

import os
import shutil
import tempfile

_test_data_dir = tempfile.mkdtemp(prefix="agh-pytest-")
os.environ.setdefault("AGH_DATA_DIR", _test_data_dir)


def pytest_sessionfinish() -> None:
    """Remove the temporary AGH data directory created for the test session."""
    shutil.rmtree(_test_data_dir, ignore_errors=True)
