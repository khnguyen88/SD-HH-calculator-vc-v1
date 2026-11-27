# Spec 3 — Phase 4: HGL Method Wiring (Tasks 18–20)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Replace Spec 2's label-only `hglMethod` with real `IF(hglMethod=...)` branching formulas on HGL cols G/K/M. Apply the same pattern to `HGL(25YEAR)`.

**Spec:** `docs/superpowers/specs/2026-11-26-spec3-three-shape-bidirectional-design.md` §8

**Depends on:** Phase 3 complete (bidirectional calculator working); pre-work done (WIP + golden regenerated).

**Reference reading before starting:** `docs/template-analysis/02-hgl.md` §G (current legacy formula structure on HGL) and `docs/template-analysis/hgl-reference-values.md` (pre-repair cache baseline — the legacy branch MUST match these values).

---

## Task 18: HGL method wiring — new `build_golden.py` edit

**Files:**
- Modify: `docs/template-analysis/build_golden.py`
- Regenerate: `docs/template_golden.xlsx`

- [ ] **Step 18.1: Add `wire_hgl_method(wb)` edit function**

Open `docs/template-analysis/build_golden.py`. Below the last existing edit function, add:

```python
def wire_hgl_method(wb):
    """Replace HGL cols G, K, M with IF(hglMethod=...) branching formulas.

    Spec 2 left hglMethod label-only. Spec 3 makes the toggle drive the
    formulas on both HGL and HGL(25YEAR).

    Legacy branch (unchanged): MAX(chain, ds_crown, us_crown).
    HEC-22 branch: MAX(chain, ds_crown) — drops the us_crown term.
    """
    for sheet_name in ("HGL", "HGL(25YEAR)"):
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        for col in ("G", "K", "M"):
            for r in range(10, 99):
                cell = ws[f"{col}{r}"]
                if cell.value is None or not str(cell.value).startswith("="):
                    continue
                legacy = cell.value.lstrip("=")
                # The HEC-22 branch is derived by stripping the us_crown
                # MAX arg. Implementer MUST read 02-hgl.md §G to confirm
                # the exact legacy pattern before finalizing this regex.
                # Pattern hint for the common form:
                #   MAX(<chain>, <ds-crown-term>, <us-crown-term>)
                # Replace with MAX(<chain>, <ds-crown-term>).
                import re
                m = re.match(
                    r"^MAX\((.+?),\s*(.+?crown.+?),\s*(.+?crown.+?)\)\s*$",
                    legacy, re.IGNORECASE
                )
                if m:
                    chain, ds_crown, _us_crown = m.groups()
                    hec22 = f"MAX({chain},{ds_crown})"
                else:
                    # Fallback: use legacy for both branches; emit a
                    # structured log so the implementer sees unparsed rows.
                    print(f"[wire_hgl_method] unparsed {sheet_name}!{col}{r}: "
                          f"{legacy!r} — using legacy formula for both branches",
                          file=__import__('sys').stderr)
                    hec22 = legacy
                ws[f"{col}{r}"] = (
                    f'=IF(hglMethod="legacy both-end crown floor",'
                    f'{legacy},{hec22})'
                )
    return wb
```

**IMPORTANT.** The regex pattern covers the common form. Open `template_wip_new.xlsx` in Excel, click a few HGL cells in cols G/K/M, and read the ACTUAL formulas. If the structure differs (e.g., XLOOKUPs wrap the crown terms, or the MAX is nested), extend the regex to match. The `unparsed` fallback log is the signal to add patterns.

- [ ] **Step 18.2: Wire into `main()`**

In `build_golden.py`'s `main(src, dst)`, add after the last existing edit:

```python
    wire_hgl_method(wb)
```

- [ ] **Step 18.3: Rebuild golden**

```bash
cd docs/template-analysis
python build_golden.py ../template_wip_new.xlsx ../template_golden.xlsx
```

Expected: exits 0; any unparsed-row log lines go to stderr (fix them if present).

- [ ] **Step 18.4: Smoke-check in Excel 365**

Open `docs/template_golden.xlsx`. On the HGL sheet, click any populated G/K/M cell. Expected: formula starts with `=IF(hglMethod="legacy both-end crown floor",...)`.

Flip `Config!B5` to `"legacy both-end crown floor"`. HGL col M values should match the pre-repair baseline in `docs/template-analysis/hgl-reference-values.md`. Flip back to HEC-22 — values change.

- [ ] **Step 18.5: Commit**

```bash
git add docs/template-analysis/build_golden.py docs/template_golden.xlsx
git commit -m "feat(template): wire hglMethod to actual HGL formulas

Replaces Spec 2's label-only hglMethod. HGL + HGL(25YEAR) cols G/K/M
now IF-branch on the hglMethod named range: legacy keeps the existing
MAX(chain, ds_crown, us_crown) pin; HEC-22 drops the us_crown term.
Spec 3 Task 18."
```

---

## Task 19: HGL method wiring tests

**Files:**
- Create: `docs/template-analysis/test_hgl_method_formula_branches.py`
- Create: `docs/template-analysis/test_hgl_method_round_trip.py`

- [ ] **Step 19.1: Formula-branch content test**

Create `docs/template-analysis/test_hgl_method_formula_branches.py`:

```python
"""HGL cols G/K/M formulas contain both method branches after Spec 3."""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
GOLDEN = HERE.parent / "template_golden.xlsx"


def test_hgl_g_formulas_branch_on_hgl_method():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    ws = wb["HGL"]
    hits = 0
    for r in range(10, 99):
        v = ws[f"G{r}"].value
        if v is None or not str(v).startswith("="):
            continue
        assert "hglMethod" in str(v), f"G{r} missing hglMethod branch: {v!r}"
        assert "legacy both-end crown floor" in str(v), (
            f"G{r} missing legacy branch literal: {v!r}"
        )
        hits += 1
    assert hits > 0, "No populated G rows on HGL — check fixture setup"


def test_hgl_25yr_same_pattern():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    if "HGL(25YEAR)" not in wb.sheetnames:
        return
    ws = wb["HGL(25YEAR)"]
    for r in range(10, 99):
        for col in ("G", "K", "M"):
            v = ws[f"{col}{r}"].value
            if v is None or not str(v).startswith("="):
                continue
            assert "hglMethod" in str(v), (
                f"HGL(25YEAR)!{col}{r} missing hglMethod branch: {v!r}"
            )
```

- [ ] **Step 19.2: Round-trip test (semi-manual)**

Create `docs/template-analysis/test_hgl_method_round_trip.py`:

```python
"""Verify that flipping Config!B5 actually changes HGL values.

Loads golden with data_only=True (cached values). Requires one-time Excel
open+save per method value to populate the cache:
  fixtures/golden_hec22_cached.xlsx   — opened with B5 = HEC-22, saved
  fixtures/golden_legacy_cached.xlsx  — opened with B5 = legacy, saved
"""
from pathlib import Path
import pytest
import openpyxl

HERE = Path(__file__).parent
HEC22 = HERE / "fixtures" / "golden_hec22_cached.xlsx"
LEGACY = HERE / "fixtures" / "golden_legacy_cached.xlsx"


@pytest.mark.skipif(not HEC22.exists() or not LEGACY.exists(),
                    reason="See fixture setup comments")
def test_hgl_values_differ_between_methods():
    hec = openpyxl.load_workbook(HEC22, data_only=True)
    leg = openpyxl.load_workbook(LEGACY, data_only=True)
    sdc_hec = hec["HGL"]
    sdc_leg = leg["HGL"]
    differing_rows = []
    for r in range(10, 99):
        h = sdc_hec[f"M{r}"].value
        l = sdc_leg[f"M{r}"].value
        if h is None or l is None:
            continue
        if isinstance(h, (int, float)) and isinstance(l, (int, float)):
            if abs(h - l) > 0.001:
                differing_rows.append((r, h, l))
    assert len(differing_rows) > 0, (
        "HGL col M identical across both methods — the toggle has no "
        "effect; check Task 18's formula rewrites."
    )
```

- [ ] **Step 19.3: Run the tests**

```bash
cd docs && pytest template-analysis/test_hgl_method_formula_branches.py -v
```

Expected: 2 tests pass.

The round-trip test skips unless the fixture files exist. Create them by:
1. Open `docs/template_golden.xlsx` in Excel. Flip `Config!B5` to `HEC-22 EGL (d/s crown floor)`. Save as `fixtures/golden_hec22_cached.xlsx`.
2. Re-open the original. Flip B5 to `legacy both-end crown floor`. Save as `fixtures/golden_legacy_cached.xlsx`.

Re-run the test — expected: 3 tests pass.

- [ ] **Step 19.4: Commit**

```bash
git add docs/template-analysis/test_hgl_method_formula_branches.py \
        docs/template-analysis/test_hgl_method_round_trip.py
git commit -m "test(hgl): formula-branch + round-trip tests for hglMethod

Verify each populated G/K/M cell on HGL and HGL(25YEAR) contains both
method branches. Round-trip test compares cached HGL values between
HEC-22 and legacy Excel renders. Spec 3 Task 19."
```

---

## Task 20: Phase 4 ship gate — HGL end-to-end verification

**Files:** none (manual verification only)

- [ ] **Step 20.1: End-to-end matrix**

| Action | Expected |
|---|---|
| Open `template_golden.xlsx` in Excel 365. Flip `Config!B5` to legacy | HGL col M values change on rows where upstream crown ≠ downstream crown |
| Save + close. Re-open. | Values persist. P3 stamp shows legacy. |
| Flip back to HEC-22. | Values revert. |
| Cross-check vs `docs/template-analysis/hgl-reference-values.md` for legacy setting. | HGL col M values match baseline rows exactly. |
| In calculator: change hglMethod via UI toggle (if UI has one). Export Simple → open → formulas honor the toggle. | Pass |

- [ ] **Step 20.2: No commit (no file changes) — phase complete when matrix passes**

Pause for user review. Hand off to [`phase-5-visualizer.md`](phase-5-visualizer.md).
