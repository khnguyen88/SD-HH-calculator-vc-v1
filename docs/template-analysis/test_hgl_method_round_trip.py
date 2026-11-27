"""Verify that flipping Config!B5 actually changes HGL col K values.

Only col K differs between methods per Task 18's findings. G and M
use the hglMethod IF-wrap defensively but both branches are equal.

Setup is manual (requires one-time Excel open+save per method value):
  fixtures/golden_hec22_cached.xlsx   — Config!B5 = HEC-22, saved
  fixtures/golden_legacy_cached.xlsx  — Config!B5 = legacy, saved
"""
from pathlib import Path
import pytest
import openpyxl

HERE = Path(__file__).parent
HEC22 = HERE / "fixtures" / "golden_hec22_cached.xlsx"
LEGACY = HERE / "fixtures" / "golden_legacy_cached.xlsx"


@pytest.mark.skipif(not HEC22.exists() or not LEGACY.exists(),
                    reason="See fixture setup comments (one-time Excel "
                           "open + save per method value)")
def test_hgl_k_values_differ_between_methods():
    hec = openpyxl.load_workbook(HEC22, data_only=True)
    leg = openpyxl.load_workbook(LEGACY, data_only=True)
    sdc_hec = hec["HGL"]
    sdc_leg = leg["HGL"]
    differing_rows = []
    for r in range(7, 92):
        h = sdc_hec[f"K{r}"].value
        l = sdc_leg[f"K{r}"].value
        if h is None or l is None:
            continue
        if isinstance(h, (int, float)) and isinstance(l, (int, float)):
            if abs(h - l) > 0.001:
                differing_rows.append((r, h, l))
    assert len(differing_rows) > 0, (
        "HGL col K identical across both methods — the toggle has no "
        "effect; check Task 18's formula rewrites."
    )
