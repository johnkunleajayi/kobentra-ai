"""Keep tests independent of developer .env credentials and outside the system temp folder."""

import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"


def pytest_configure(config):
    if config.option.basetemp is None:
        config.option.basetemp = str(
            Path(__file__).resolve().parents[2] / "work" / "pytest-phase2a"
        )
