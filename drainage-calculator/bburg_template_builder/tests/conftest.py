"""Shared pytest fixtures for the template builder tests."""
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

# Ensure the sibling package is importable when running pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.fixture
def empty_wb() -> Workbook:
    """A fresh workbook with the default Sheet removed, ready for sheet modules to populate."""
    wb = Workbook()
    default = wb.active
    if default is not None:
        wb.remove(default)
    return wb


@pytest.fixture
def built_wb():
    """Builds the full template workbook in-memory. Use for integration tests."""
    from bburg_template_builder.workbook import build_workbook
    return build_workbook()
