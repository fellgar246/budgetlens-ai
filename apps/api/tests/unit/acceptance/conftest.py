from __future__ import annotations

from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = Path(str(item.path))
        if not path.is_relative_to(HERE):
            continue
        item.add_marker(pytest.mark.acceptance)
