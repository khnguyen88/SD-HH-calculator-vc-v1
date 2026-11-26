# Golden Rulebook-Aligned Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `docs/template_golden.xlsx` by applying six structured edits to the Spec-1 repaired `docs/template_wip_new.xlsx`, shipping a `Config` sheet with three project-level toggles (`junctionAngleRule`, `hglCrownCeilingRule`, `hglMethod`) that Spec 3's calculator and visualizer will read on xlsx import.

**Architecture:** One flat Python builder (`build_golden.py`) mirrors Spec 1's `repair.py`: six top-level edit functions plus a `main(src, dst)` CLI. Each edit is independently testable via pytest (one group of function-tests per edit). The builder opens the WIP (pinned by SHA), mutates it in memory, saves to `template_golden.xlsx`. No calculator or visualizer code changes.

**Tech Stack:** Python 3.11, openpyxl 3.1.5, pytest. All already installed and used by Spec 1.

**Spec reference:** `docs/superpowers/specs/2026-11-25-golden-template-design.md` is the source of truth for every edit's intent. This plan is the executable breakdown.

**Working directory convention:** All shell commands below assume CWD = `docs/` (the directory containing `template-analysis/`, `superpowers/`, `template_wip_new.xlsx`). Git commands run from repo root; this plan uses `docs/...` paths for files so they work either way.

---

## File structure

**New files:**

- `docs/template-analysis/build_golden.py` — builder script. Six edit functions + `main(src, dst)` CLI. ~250 lines total, flat module (no subdirs).
- `docs/template-analysis/test_build_golden.py` — pytest suite. Function-based tests grouped by naming convention (`test_config_*`, `test_junction_*`, `test_hgl_clearance_*`, etc.). Follows the style of `test_repair.py`.
- `docs/template-analysis/calculator-import-contract.md` — read/write contract for Spec 3. Pure doc.
- `docs/template_golden.xlsx` — generated binary output. Committed to git.

**Modified files:**

- `docs/template-analysis/conftest.py` — add `golden_built` module-scoped fixture; pin WIP SHA-256.
- `docs/template-analysis/README.md` — append `build_golden.py` under **Scripts**; update sheet-count note.

**Not modified:** anything under `drainage-calculator/`; `repair.py`; `template_wip_new.xlsx`; the 16 per-tab analysis markdowns.

---

## Task 0: Scaffolding — conftest fixture, SHA pin, builder skeleton

**Files:**
- Modify: `docs/template-analysis/conftest.py`
- Create: `docs/template-analysis/build_golden.py` (skeleton — no edits yet)
- Create: `docs/template-analysis/test_build_golden.py` (one smoke test)

- [ ] **Step 0.1: Compute the WIP SHA-256**

Run (from `docs/`):

```bash
python -c "import hashlib; print(hashlib.sha256(open('template_wip_new.xlsx','rb').read()).hexdigest())"
```

Copy the returned 64-char hex string — you'll paste it into `conftest.py` in the next step.

- [ ] **Step 0.2: Extend `conftest.py`**

Open `docs/template-analysis/conftest.py` and replace its contents with:

```python
# Shared pytest fixtures for the template-analysis test suite.
#
# repaired_wb: runs repair.py once per module, loads the result. Reused by
#   test_repair.py. Module-scoped because the subprocess cost is non-trivial.
# golden_built: runs build_golden.py once per module, loads the result.
#   Used by test_build_golden.py. Module-scoped for the same reason.
#
# Both fixtures return read-only workbooks - tests MUST NOT mutate them.
import hashlib
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

HERE = Path(__file__).parent
REPAIR = HERE / "repair.py"
BUILD_GOLDEN = HERE / "build_golden.py"
WIP = HERE.parent / "template_wip_new.xlsx"
BACKUP = HERE.parent / "template_wip_new_pre-repair.xlsx"
GOLDEN = HERE.parent / "template_golden.xlsx"

# Pinned SHA-256 of docs/template_wip_new.xlsx. When WIP is intentionally
# changed, update this hash in the same commit so reviewers see the
# golden rebuild is a deliberate consequence of the WIP change.
WIP_SHA256 = "PASTE_SHA_FROM_STEP_0_1_HERE"


@pytest.fixture(scope="module")
def repaired_wb():
    assert BACKUP.exists(), "pre-repair backup missing - Task 1 not run"
    subprocess.check_call([sys.executable, str(REPAIR), str(BACKUP), str(WIP)])
    return openpyxl.load_workbook(WIP, data_only=False)


@pytest.fixture(scope="module")
def golden_built(tmp_path_factory):
    # Pin the WIP input so an unintended WIP change can't silently alter
    # the golden output. When WIP changes on purpose, update WIP_SHA256
    # in the same commit as the WIP change.
    actual = hashlib.sha256(WIP.read_bytes()).hexdigest()
    assert actual == WIP_SHA256, (
        f"WIP input hash drift:\n  expected {WIP_SHA256}\n  got      {actual}\n"
        "If this WIP change is intentional, update WIP_SHA256 in conftest.py."
    )
    out = tmp_path_factory.mktemp("golden") / "template_golden.xlsx"
    subprocess.check_call([sys.executable, str(BUILD_GOLDEN), str(WIP), str(out)])
    return openpyxl.load_workbook(out, data_only=False)


@pytest.fixture(scope="module")
def golden_built_twice(tmp_path_factory, golden_built):
    # Idempotency check: run the builder on its own output, return both
    # workbooks so tests can diff them.
    out2 = tmp_path_factory.mktemp("golden2") / "template_golden_2.xlsx"
    # golden_built is already built at a tmp path; find it by rebuilding
    # into a known first path instead of trusting the fixture's return.
    first = tmp_path_factory.mktemp("golden1") / "template_golden_1.xlsx"
    subprocess.check_call([sys.executable, str(BUILD_GOLDEN), str(WIP), str(first)])
    subprocess.check_call([sys.executable, str(BUILD_GOLDEN), str(first), str(out2)])
    return openpyxl.load_workbook(first, data_only=False), openpyxl.load_workbook(out2, data_only=False)
```

**Important:** paste the actual SHA hex into `WIP_SHA256` from Step 0.1's output. The placeholder `"PASTE_SHA_FROM_STEP_0_1_HERE"` must not remain.

- [ ] **Step 0.3: Create the builder skeleton**

Create `docs/template-analysis/build_golden.py`:

```python
# Apply Spec-2 edits to the Spec-1 repaired WIP template to produce the
# golden rulebook-aligned template.
#
# Usage: python build_golden.py <wip_source.xlsx> <golden_output.xlsx>
#
# Six edits are applied in order (all idempotent):
#   1. add_config_sheet        - new Config tab with 3 toggle named ranges
#   2. rewire_junction_angle_rule - toggle-aware controlling-angle formula
#   3. add_hgl_crown_ceiling_checks - clearance columns on HGL + HGL(25YEAR)
#   4. annotate_hgl_method     - top-of-sheet hglMethod stamp
#   5. add_u7_small_area_tc_lookup - Table 3-3 Tc lookup on C_FACTOR col W
#   6. annotate_equations_sheet - toggle + citation annotations
#
# Spec: docs/superpowers/specs/2026-11-25-golden-template-design.md
import sys

import openpyxl


def add_config_sheet(wb):
    raise NotImplementedError("Task 1")


def rewire_junction_angle_rule(wb):
    raise NotImplementedError("Task 2")


def add_hgl_crown_ceiling_checks(wb):
    raise NotImplementedError("Task 3")


def annotate_hgl_method(wb):
    raise NotImplementedError("Task 4")


def add_u7_small_area_tc_lookup(wb):
    raise NotImplementedError("Task 5")


def annotate_equations_sheet(wb):
    raise NotImplementedError("Task 6")


def main(src, dst):
    wb = openpyxl.load_workbook(src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    annotate_hgl_method(wb)
    add_u7_small_area_tc_lookup(wb)
    annotate_equations_sheet(wb)
    wb.save(dst)
    print(f"wrote {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: build_golden.py <wip_source.xlsx> <golden_output.xlsx>",
              file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
```

- [ ] **Step 0.4: Create a smoke test**

Create `docs/template-analysis/test_build_golden.py`:

```python
# Tests for build_golden.py - applies Spec-2 edits to the repaired WIP
# template, producing template_golden.xlsx. Shared fixture `golden_built`
# lives in conftest.py.
from pathlib import Path

HERE = Path(__file__).parent


def test_skeleton_runs_end_to_end(golden_built):
    # Smoke test: builder completes end-to-end once every edit is
    # implemented. Until Task 1 is done this test fails with
    # NotImplementedError - that's expected.
    assert golden_built is not None
    assert len(golden_built.sheetnames) == 17
```

- [ ] **Step 0.5: Confirm the skeleton fails cleanly**

Run (from `docs/template-analysis/`):

```bash
python -m pytest test_build_golden.py::test_skeleton_runs_end_to_end -v
```

Expected: FAIL with `NotImplementedError: Task 1` (from `add_config_sheet`). This confirms the fixture wiring works and the builder script is reachable. If instead you see SHA-mismatch, re-run Step 0.1 to capture the correct hash.

- [ ] **Step 0.6: Commit scaffolding**

Run (from repo root):

```bash
git add docs/template-analysis/conftest.py docs/template-analysis/build_golden.py docs/template-analysis/test_build_golden.py
git commit -m "docs(golden): scaffold build_golden.py + conftest fixture"
```

---

## Task 1: Edit 1 — add_config_sheet

**Files:**
- Modify: `docs/template-analysis/build_golden.py` (implement `add_config_sheet`)
- Modify: `docs/template-analysis/test_build_golden.py` (append `test_config_*` tests)

**Spec reference:** §4 (Config sheet schema) and §5.1.

- [ ] **Step 1.1: Write failing tests for Config sheet**

Append to `docs/template-analysis/test_build_golden.py`:

```python
def test_config_sheet_exists_and_is_last_tab(golden_built):
    assert "Config" in golden_built.sheetnames
    assert golden_built.sheetnames[-1] == "Config", (
        "Config must be the last tab so existing print-sheet indices "
        "don't shift"
    )


def test_config_sheet_sixteen_originals_preserved_in_order(golden_built, repaired_wb):
    # The 16 original tabs appear in their original order, followed by Config.
    originals = [n for n in golden_built.sheetnames if n != "Config"]
    assert originals == repaired_wb.sheetnames, (
        f"original tab order changed:\n  wip:    {repaired_wb.sheetnames}\n"
        f"  golden: {originals}"
    )


def test_config_three_named_ranges_defined(golden_built):
    names = set(golden_built.defined_names)
    for expected in ("junctionAngleRule", "hglCrownCeilingRule", "hglMethod"):
        assert expected in names, f"named range {expected!r} missing"


def test_config_named_ranges_point_at_b_column(golden_built):
    for name, cell in (
        ("junctionAngleRule", "$B$3"),
        ("hglCrownCeilingRule", "$B$4"),
        ("hglMethod", "$B$5"),
    ):
        dn = golden_built.defined_names[name]
        val = getattr(dn, "value", None) or str(dn)
        assert "Config!" in val and cell in val, (
            f"{name!r} should resolve to Config!{cell}, got {val!r}"
        )


def test_config_defaults(golden_built):
    ws = golden_built["Config"]
    assert ws["A3"].value == "junctionAngleRule"
    assert ws["B3"].value == "smaller-loss"
    assert ws["A4"].value == "hglCrownCeilingRule"
    assert ws["B4"].value == "crown-plus-1ft"
    assert ws["A5"].value == "hglMethod"
    assert ws["B5"].value == "HEC-22 EGL (d/s crown floor)"


def test_config_data_validation_lists_present(golden_built):
    ws = golden_built["Config"]
    dvs = ws.data_validations.dataValidation
    # One list-type DV per toggle cell (B3, B4, B5).
    list_dvs = [dv for dv in dvs if dv.type == "list"]
    assert len(list_dvs) >= 3, f"expected 3 list validations, got {len(list_dvs)}"
    # Each DV applies to exactly one of B3/B4/B5.
    applied_cells = set()
    for dv in list_dvs:
        for rng in dv.sqref.ranges:
            applied_cells.add(str(rng).strip())
    for cell in ("B3", "B4", "B5"):
        assert cell in applied_cells, (
            f"no list DV applied to Config!{cell}, applied cells: {applied_cells}"
        )


def test_config_citation_cells_populated(golden_built):
    ws = golden_built["Config"]
    for cell_addr, must_contain in (
        ("C3", "MDSHA"),
        ("C3", "PG County SWM"),
        ("C4", "MCDOT §4.3.1"),
        ("C4", "PG C I-2"),
        ("C5", "HTML calculator toggle"),
    ):
        v = ws[cell_addr].value
        assert isinstance(v, str) and must_contain in v, (
            f"Config!{cell_addr} should mention {must_contain!r}, got {v!r}"
        )


def test_config_tab_color_set(golden_built):
    ws = golden_built["Config"]
    # Amber signals "settings, not data". Any non-empty color counts.
    assert ws.sheet_properties.tabColor is not None, (
        "Config tab color should be set (amber per spec)"
    )
```

- [ ] **Step 1.2: Run tests to confirm they all fail**

Run (from `docs/template-analysis/`):

```bash
python -m pytest test_build_golden.py -v -k "test_config or test_skeleton"
```

Expected: all 8 fail with `NotImplementedError: Task 1`.

- [ ] **Step 1.3: Implement `add_config_sheet`**

Replace the `add_config_sheet` function in `docs/template-analysis/build_golden.py`:

```python
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation


CONFIG_SHEET_NAME = "Config"

CONFIG_ROWS = (
    # (name,                    default,                               list_options,                                                               citation)
    ("junctionAngleRule",       "smaller-loss",                       ("smaller-loss", "larger-loss"),
     'MDSHA Drainage Manual Ch. 5 "Storm Drain Systems" (Sept 2023); MCDOT §4.3.2.3 (June 2014). '
     'PG County SWM Ch. 8 p. 8-27 (Sept 30 2014) states the opposite rule - set to "larger-loss" '
     'for PG-reviewed projects. The WIP template\'s prior default behavior matches "larger-loss"; '
     'the golden default is "smaller-loss" (MDSHA primary source).'),
    ("hglCrownCeilingRule",     "crown-plus-1ft",                     ("crown-plus-1ft", "rim-only"),
     'MCDOT §4.3.1: HGL ≤ Crown + 1 ft AND HGL ≤ Rim − 1 ft. '
     'PG C I-2 caps only at Rim − 12" (no explicit crown ceiling) - '
     'set to "rim-only" for PG-reviewed projects.'),
    ("hglMethod",               "HEC-22 EGL (d/s crown floor)",       ("HEC-22 EGL (d/s crown floor)", "legacy both-end crown floor"),
     "HTML calculator toggle landed 2026-11-09 (HEC-22 vs legacy both-end crown floor). "
     "Label-only in Spec 2; Spec 3 wires xlsx HGL computation to this toggle."),
)


def add_config_sheet(wb):
    # Idempotent: if Config already exists, remove and rebuild. Guarantees
    # the sheet ends up as the last tab even if a prior run left it mid-list.
    if CONFIG_SHEET_NAME in wb.sheetnames:
        del wb[CONFIG_SHEET_NAME]
    # Also drop any stale defined names so we don't double-register.
    for name in ("junctionAngleRule", "hglCrownCeilingRule", "hglMethod"):
        if name in wb.defined_names:
            del wb.defined_names[name]

    ws = wb.create_sheet(CONFIG_SHEET_NAME)
    ws.sheet_properties.tabColor = "FFC107"  # amber

    # Row 1 header, merged A1:C1.
    ws["A1"] = (
        "Project-level design-rule toggles - DO NOT DELETE. "
        "Read by Spec 3 calculator/visualizer import."
    )
    ws.merge_cells("A1:C1")
    ws["A1"].font = Font(bold=True)
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    editable_fill = PatternFill("solid", fgColor="FFFBEB")  # light yellow
    mono = Font(name="Consolas", size=11)
    label_font = Font(bold=True)
    cite_font = Font(italic=True, color="666666")

    for row_idx, (name, default, options, citation) in enumerate(CONFIG_ROWS, start=3):
        # Column A: label.
        ws.cell(row=row_idx, column=1, value=name).font = label_font
        ws.cell(row=row_idx, column=1).alignment = Alignment(horizontal="right")

        # Column B: editable default value (dropdown-backed).
        b = ws.cell(row=row_idx, column=2, value=default)
        b.font = mono
        b.fill = editable_fill

        # Column C: citation / informational text.
        c = ws.cell(row=row_idx, column=3, value=citation)
        c.font = cite_font
        c.alignment = Alignment(wrap_text=True, vertical="top")

        # Columns E-G: hidden helper lists, one option pair per toggle at E/F/G.
        helper_col = 5 + (row_idx - 3)  # E=5, F=6, G=7
        for opt_idx, opt in enumerate(options, start=3):
            ws.cell(row=opt_idx, column=helper_col, value=opt)

        # Data validation: list sourced from this toggle's helper column.
        helper_letter = openpyxl.utils.get_column_letter(helper_col)
        dv = DataValidation(
            type="list",
            formula1=f"=${helper_letter}$3:${helper_letter}$4",
            allow_blank=False,
        )
        dv.error = f"Must be one of: {', '.join(options)}"
        dv.errorTitle = "Invalid toggle value"
        dv.errorStyle = "stop"
        ws.add_data_validation(dv)
        dv.add(b)

        # Workbook-scoped named range for this toggle.
        wb.defined_names[name] = DefinedName(
            name=name,
            attr_text=f"{CONFIG_SHEET_NAME}!$B${row_idx}",
        )

    # Hide helper columns E-G.
    for col_letter in ("E", "F", "G"):
        ws.column_dimensions[col_letter].hidden = True

    # Column widths.
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 38
    ws.column_dimensions["C"].width = 70
```

**Imports:** add `openpyxl` and the `openpyxl.utils` import at the top of the file if not already present:

```python
import sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
```

- [ ] **Step 1.4: Run the Config tests**

Run (from `docs/template-analysis/`):

```bash
python -m pytest test_build_golden.py -v -k "test_config or test_skeleton"
```

Expected: `test_config_*` tests PASS; `test_skeleton_runs_end_to_end` still fails because Task 2's `rewire_junction_angle_rule` still raises `NotImplementedError`. That's fine; the smoke test will pass once Task 6 is done.

- [ ] **Step 1.5: Commit Task 1**

Run (from repo root):

```bash
git add docs/template-analysis/build_golden.py docs/template-analysis/test_build_golden.py
git commit -m "docs(golden): Edit 1 - add Config sheet with three named-range toggles"
```

---

## Task 2: Edit 2 — rewire_junction_angle_rule

**Files:**
- Modify: `docs/template-analysis/build_golden.py` (implement `rewire_junction_angle_rule`)
- Modify: `docs/template-analysis/test_build_golden.py` (append `test_junction_*` tests)

**Spec reference:** §5.2 (default flip from PG-style "larger-loss" to MDSHA-style "smaller-loss" — intentional behavior change).

**Empirical facts to rely on** (verified before planning):
- `STORM DRAIN COMPS!AD10` currently = `=IF(AR10="","",IF(AR10=0,"-",MAX(IF($AQ$10:$AQ$98=$AR10,$R$10:$R$98))))` (ArrayFormula).
- `STORM DRAIN COMPS!AR10` = `=IF(AA10="","",MAX(IF($B$10:$B$98=$A10,$AQ$10:$AQ$98)))` (ArrayFormula).
- Column `R` header (row 8): `"Angle Out of Pipe (Deg) - Whole #"` — R is the inflow-pipe angle, despite `01-storm-drain-comps.md` labeling R as Manning's n. The analysis doc is wrong on this one column; use the actual header row.
- Column `AJ` is NOT free: `AJ10 = '=IF(Table4[[#This Row],[Column43]]="","",Table4[[#This Row],[Column43]])'`. Fallback to a new column — first free after `BD` is `BE`.
- Data rows are 10–98.

- [ ] **Step 2.1: Write failing tests for junction angle rewire**

Append to `docs/template-analysis/test_build_golden.py`:

```python
def test_junction_wip_has_max_pattern_originally(repaired_wb):
    # Control test: confirms the WIP's AD10 still carries the MAX pattern
    # before Edit 2 runs. If this ever fails, the WIP was changed upstream
    # and Edit 2 may no longer apply - review before proceeding.
    ws = repaired_wb["STORM DRAIN COMPS"]
    ad10 = ws["AD10"].value
    text = getattr(ad10, "text", None) or (ad10 if isinstance(ad10, str) else None)
    assert text is not None, f"AD10 unexpected type: {type(ad10)}"
    assert "MAX(IF($AQ$10:$AQ$98=$AR10,$R$10:$R$98))" in text, (
        f"WIP AD10 drifted - expected MAX-of-angle-by-max-Lv pattern, got {text!r}"
    )


def test_junction_ad_formula_references_toggle(golden_built):
    ws = golden_built["STORM DRAIN COMPS"]
    ad10 = ws["AD10"].value
    text = getattr(ad10, "text", None) or (ad10 if isinstance(ad10, str) else None)
    assert text is not None and "junctionAngleRule" in text, (
        f"golden AD10 should pivot on junctionAngleRule, got {text!r}"
    )


def test_junction_ad_formula_has_both_branches(golden_built):
    ws = golden_built["STORM DRAIN COMPS"]
    text = getattr(ws["AD10"].value, "text", None) or str(ws["AD10"].value)
    # smaller-loss branch picks the angle matching the MIN of positive Lv.
    assert "smaller-loss" in text, f"missing smaller-loss branch: {text!r}"
    # larger-loss branch preserves the original MAX pattern.
    assert "MAX(IF($AQ$10:$AQ$98=$AR10,$R$10:$R$98))" in text, (
        f"larger-loss branch should preserve WIP MAX pattern: {text!r}"
    )


def test_junction_ad_formula_applied_all_data_rows(golden_built):
    ws = golden_built["STORM DRAIN COMPS"]
    # Rows 10-98 all have an AD formula referencing junctionAngleRule.
    for r in range(10, 99):
        v = ws.cell(row=r, column=30).value  # AD = col 30
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        assert text is not None and "junctionAngleRule" in text, (
            f"AD{r} missing toggle reference: {text!r}"
        )


def test_junction_ar_min_helper_populated(golden_built):
    # The AR_min helper column exists somewhere and carries a MIN-of-positive-
    # Lv formula on every data row. Default placement is BE if AJ is occupied.
    ws = golden_built["STORM DRAIN COMPS"]
    # Find the helper column by scanning row 10 for a MIN(...>0...) pattern.
    helper_col = None
    for col in range(1, ws.max_column + 2):
        v = ws.cell(row=10, column=col).value
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        if isinstance(text, str) and "MIN(IF((" in text and "$AQ$10:$AQ$98>0" in text:
            helper_col = col
            break
    assert helper_col is not None, "AR_min helper column not found on row 10"
    # Rows 10-98 all carry the helper formula.
    for r in range(10, 99):
        v = ws.cell(row=r, column=helper_col).value
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        assert text and "MIN" in text, f"helper col row {r} missing MIN: {text!r}"


def test_junction_helper_cell_was_empty_or_pass_through_in_wip(repaired_wb, golden_built):
    # The chosen helper column must NOT have overwritten a user-typed value
    # in the WIP. AJ in WIP is a Table4 pass-through formula on every row;
    # if the builder chose AJ as the helper, something went wrong.
    gws = golden_built["STORM DRAIN COMPS"]
    wws = repaired_wb["STORM DRAIN COMPS"]
    # Find helper col again.
    helper_col = None
    for col in range(1, gws.max_column + 2):
        v = gws.cell(row=10, column=col).value
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        if isinstance(text, str) and "MIN(IF((" in text:
            helper_col = col
            break
    assert helper_col is not None
    # Inspect the same column in the WIP.
    for r in range(10, 20):  # sample first ten rows
        wip_val = wws.cell(row=r, column=helper_col).value
        wip_text = getattr(wip_val, "text", None) or (wip_val if isinstance(wip_val, str) else None)
        # Acceptable: None, blank, or a formula/value we explicitly know exists
        # (e.g. an empty column beyond the active range). Not acceptable: anything
        # user-looking that would be destroyed.
        if wip_text is not None and wip_text != "":
            # If the WIP has content at this column, the builder should have
            # fallen through to a fresh column - this test fails to flag it.
            raise AssertionError(
                f"helper column (col {helper_col}) had pre-existing content at row {r}: "
                f"{wip_text!r} - builder should have chosen a later empty column"
            )
```

- [ ] **Step 2.2: Run the new tests to confirm they fail**

Run (from `docs/template-analysis/`):

```bash
python -m pytest test_build_golden.py -v -k "test_junction"
```

Expected: `test_junction_wip_has_max_pattern_originally` PASSES (control test), the other 4 FAIL with `NotImplementedError: Task 2`.

- [ ] **Step 2.3: Implement `rewire_junction_angle_rule`**

Replace the function body in `docs/template-analysis/build_golden.py`:

```python
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.formula import ArrayFormula


SDC_SHEET = "STORM DRAIN COMPS"
SDC_DATA_START = 10
SDC_DATA_END = 98

# Preferred helper column (first free). WIP's AJ is a Table4 pass-through
# on every data row, so AJ is not free. BE is the first free column past
# the active data block (A:BD).
HELPER_COL_PREFERRED = "BE"


def _find_free_column_for_helper(ws, start_col_letter="BE"):
    # Scan columns right of (inclusive) start_col_letter for one with no
    # value in any data row. Returns the column letter.
    start_col = openpyxl.utils.column_index_from_string(start_col_letter)
    for col in range(start_col, start_col + 16):  # 16-col safety horizon
        letter = get_column_letter(col)
        occupied = any(
            ws.cell(row=r, column=col).value not in (None, "")
            for r in range(SDC_DATA_START, SDC_DATA_END + 1)
        )
        if not occupied:
            return letter
    raise RuntimeError(
        f"no free column found for AR_min helper near {start_col_letter}"
    )


def rewire_junction_angle_rule(wb):
    ws = wb[SDC_SHEET]
    helper_letter = _find_free_column_for_helper(ws, HELPER_COL_PREFERRED)

    for r in range(SDC_DATA_START, SDC_DATA_END + 1):
        # AR_min helper: MIN of positive Lv values entering this structure.
        helper_formula = (
            f'=IFERROR(MIN(IF(($B${SDC_DATA_START}:$B${SDC_DATA_END}=$A{r})'
            f'*($AQ${SDC_DATA_START}:$AQ${SDC_DATA_END}>0),'
            f'$AQ${SDC_DATA_START}:$AQ${SDC_DATA_END})),0)'
        )
        helper_coord = f"{helper_letter}{r}"
        ws[helper_coord] = ArrayFormula(helper_coord, helper_formula)

        # AD: toggle-aware controlling angle.
        #   smaller-loss (MDSHA): angle of MIN-Lv inflow among positive Lv's.
        #   larger-loss (PG):     angle of MAX-Lv inflow (= original WIP).
        ad_coord = f"AD{r}"
        ad_formula = (
            f'=IF(AR{r}="","",IF(AR{r}=0,"-",'
            f'IF(junctionAngleRule="smaller-loss",'
            f'MAX(IF(($B${SDC_DATA_START}:$B${SDC_DATA_END}=$A{r})'
            f'*($AQ${SDC_DATA_START}:$AQ${SDC_DATA_END}={helper_letter}{r}),'
            f'$R${SDC_DATA_START}:$R${SDC_DATA_END})),'
            f'MAX(IF($AQ${SDC_DATA_START}:$AQ${SDC_DATA_END}=$AR{r},'
            f'$R${SDC_DATA_START}:$R${SDC_DATA_END})))))'
        )
        ws[ad_coord] = ArrayFormula(ad_coord, ad_formula)

    # Also write a header-row note so engineers can see which column is the
    # helper. Row 8 is the SDC's dynamic label row.
    ws[f"{helper_letter}8"] = "Lv_min helper (Spec 2, for smaller-loss toggle)"
```

- [ ] **Step 2.4: Run tests, iterate if needed**

Run (from `docs/template-analysis/`):

```bash
python -m pytest test_build_golden.py -v -k "test_junction"
```

Expected: all 6 `test_junction_*` tests PASS. If `test_junction_helper_cell_was_empty_or_pass_through_in_wip` fails with "helper column had pre-existing content," the WIP has grown; update `HELPER_COL_PREFERRED` to the next free letter and re-run.

- [ ] **Step 2.5: Commit Task 2**

Run (from repo root):

```bash
git add docs/template-analysis/build_golden.py docs/template-analysis/test_build_golden.py
git commit -m "docs(golden): Edit 2 - toggle-aware junction controlling-angle formula

BEHAVIOR CHANGE: the default junctionAngleRule flips from the WIP template's
PG-style MAX-of-Lv's-angle (smaller angle wins when Lv's are equal, but the
angle BELONGING TO the larger Lv is picked) to MDSHA-style smaller-loss
(MIN-of-Lv's-angle - the angle BELONGING TO the smaller Lv is picked).

MDSHA Ch. 5 p. 5-26 (Sept 2023) and MCDOT §4.3.2.3 (June 2014) both state:
'If Lv1 is greater, v2 is the controlling angle. If Lv2 is greater, v1 is
the controlling angle' - the angle belonging to the smaller Lv controls.

PG County SWM Ch. 8 p. 8-27 (Sept 30 2014) states the opposite rule. Set
Config!B3 ('junctionAngleRule') to 'larger-loss' to reproduce the WIP's
historical behavior on PG-reviewed projects."
```

---

## Task 3: Edit 3 — add_hgl_crown_ceiling_checks

**Files:**
- Modify: `docs/template-analysis/build_golden.py` (implement `add_hgl_crown_ceiling_checks`)
- Modify: `docs/template-analysis/test_build_golden.py` (append `test_hgl_clearance_*` tests)

**Spec reference:** §5.3.

**Empirical facts** (verified before planning):
- `HGL` sheet: data rows 7–91. Row 6 is the header row. Column `O` already holds `FREEBOARD (1 FT MIN)` = `N - K` (numeric); it stays. Columns `P` and beyond are empty except Q (user-input alt TW) and R (note). Existing print area = `'HGL'!$A$1:$Q$85`.
- `HGL(25YEAR)` sheet: data rows 7–91. No rim column of its own; the rim must be pulled from `STORM DRAIN COMPS!AB` via XLOOKUP. Print area is empty (will be set by this edit).
- Column `M` on each sheet is `HGL. ELEV IN "FROM" STR.` (HGL at upstream structure including structure loss). Column `D` is `U/S (FROM) CROWN` (upstream crown).
- Edit adds **three new columns** per sheet, placed on the first empty columns after the existing used range. On `HGL`, `Q` and `R` are occupied; use `S`, `T`, `U`. On `HGL(25YEAR)`, columns through `V` are occupied; use `W`, `X`, `Y`.

- [ ] **Step 3.1: Write failing tests for HGL clearance checks**

Append to `docs/template-analysis/test_build_golden.py`:

```python
CLEARANCE_HEADERS = ("Crown+1ft Check", "Rim-1ft Check", "Clearance Governing")


def _find_clearance_cols(ws, header_row):
    found = {}
    for col in range(1, ws.max_column + 2):
        v = ws.cell(row=header_row, column=col).value
        if isinstance(v, str) and v in CLEARANCE_HEADERS:
            found[v] = col
    return found


def test_hgl_clearance_three_columns_added(golden_built):
    ws = golden_built["HGL"]
    cols = _find_clearance_cols(ws, header_row=6)
    for hdr in CLEARANCE_HEADERS:
        assert hdr in cols, f"HGL missing clearance column {hdr!r}"


def test_hgl_25year_clearance_three_columns_added(golden_built):
    ws = golden_built["HGL(25YEAR)"]
    cols = _find_clearance_cols(ws, header_row=6)
    for hdr in CLEARANCE_HEADERS:
        assert hdr in cols, f"HGL(25YEAR) missing clearance column {hdr!r}"


def test_hgl_clearance_governing_references_toggle(golden_built):
    for sheet_name in ("HGL", "HGL(25YEAR)"):
        ws = golden_built[sheet_name]
        cols = _find_clearance_cols(ws, header_row=6)
        gov_col = cols["Clearance Governing"]
        # Inspect row 7 (first data row).
        v = ws.cell(row=7, column=gov_col).value
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        assert text and "hglCrownCeilingRule" in text, (
            f"{sheet_name} Clearance Governing row 7 missing toggle: {text!r}"
        )


def test_hgl_clearance_formulas_applied_all_data_rows(golden_built):
    for sheet_name in ("HGL", "HGL(25YEAR)"):
        ws = golden_built[sheet_name]
        cols = _find_clearance_cols(ws, header_row=6)
        for hdr in CLEARANCE_HEADERS:
            col = cols[hdr]
            for r in range(7, 92):
                v = ws.cell(row=r, column=col).value
                text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
                assert text and text.startswith("="), (
                    f"{sheet_name}!{get_column_letter_safe(col)}{r} missing "
                    f"formula for {hdr!r}: {text!r}"
                )


def get_column_letter_safe(col):
    from openpyxl.utils import get_column_letter
    return get_column_letter(col)


def test_hgl_print_area_includes_new_columns(golden_built):
    ws = golden_built["HGL"]
    cols = _find_clearance_cols(ws, header_row=6)
    last_new_col = max(cols.values())
    pa = ws.print_area or ""
    # print_area is a range string like "'HGL'!$A$1:$U$91" - rough check:
    # the last column letter in the range must be >= the max new-col letter.
    import re
    m = re.search(r"\$([A-Z]+)\$\d+:\$([A-Z]+)\$\d+", pa)
    assert m, f"HGL print_area malformed or unset: {pa!r}"
    from openpyxl.utils import column_index_from_string
    end_col_idx = column_index_from_string(m.group(2))
    assert end_col_idx >= last_new_col, (
        f"HGL print_area ends at col {m.group(2)} (idx {end_col_idx}); "
        f"clearance cols end at {last_new_col}"
    )


def test_hgl_25year_print_area_set(golden_built):
    ws = golden_built["HGL(25YEAR)"]
    # Spec-1 left HGL(25YEAR) with empty print_area; Edit 3 sets one.
    assert ws.print_area, "HGL(25YEAR) print_area should be set by Edit 3"
```

- [ ] **Step 3.2: Run tests to confirm they fail**

```bash
python -m pytest test_build_golden.py -v -k "test_hgl_clearance or test_hgl_25year_clearance or test_hgl_print_area or test_hgl_25year_print_area"
```

Expected: all 6 FAIL with `NotImplementedError: Task 3`.

- [ ] **Step 3.3: Implement `add_hgl_crown_ceiling_checks`**

Replace the function body in `docs/template-analysis/build_golden.py`:

```python
HGL_HEADER_ROW = 6
HGL_DATA_START = 7
HGL_DATA_END = 91

# Column letters that hold the pieces each formula needs. These are the
# existing HGL + HGL(25YEAR) semantics - column D = U/S crown, M = HGL at
# "FROM" str. Rim differs: HGL has it in col N (lookup from SDC!AB);
# HGL(25YEAR) has no rim column, so the Governing formula XLOOKUPs rim
# directly from SDC!AB.
HGL_COL_UPSTREAM_CROWN = "D"
HGL_COL_HGL_AT_FROM = "M"
HGL_COL_RIM_IN_PLACE = "N"  # only on HGL sheet
HGL_COL_FROM_ID = "A"
HGL_COL_TO_ID = "B"

SDC_RIM_LOOKUP_RANGE = "'STORM DRAIN COMPS'!$A:$A"
SDC_TO_LOOKUP_RANGE = "'STORM DRAIN COMPS'!$B:$B"
SDC_RIM_RETURN_RANGE = "'STORM DRAIN COMPS'!$AB:$AB"


def _rim_cell_formula_for_hgl_25year(r):
    # HGL(25YEAR) has no rim column, so pull from SDC via the (From, To)
    # pair - same pattern as the Spec-1 R1 rebuild on HGL(25YEAR) cols C/E/H/L.
    return (
        f'IF(OR(A{r}="",B{r}=""),"",'
        f'XLOOKUP(1,({SDC_RIM_LOOKUP_RANGE}=$A{r})*({SDC_TO_LOOKUP_RANGE}=$B{r}),'
        f'{SDC_RIM_RETURN_RANGE}))'
    )


def _first_empty_column_in_row(ws, row, start_col_letter):
    from openpyxl.utils import column_index_from_string
    start = column_index_from_string(start_col_letter)
    for col in range(start, start + 32):
        if ws.cell(row=row, column=col).value in (None, ""):
            return col
    raise RuntimeError(
        f"no empty column found after {start_col_letter} on {ws.title}"
    )


def _add_checks_to_hgl_sheet(ws, rim_formula_fn, start_search_letter):
    first_empty = _first_empty_column_in_row(ws, HGL_HEADER_ROW, start_search_letter)
    crown_col = first_empty
    rim_col = first_empty + 1
    gov_col = first_empty + 2

    crown_letter = get_column_letter(crown_col)
    rim_letter = get_column_letter(rim_col)
    gov_letter = get_column_letter(gov_col)

    # Headers in the existing header row.
    ws.cell(row=HGL_HEADER_ROW, column=crown_col, value="Crown+1ft Check")
    ws.cell(row=HGL_HEADER_ROW, column=rim_col, value="Rim-1ft Check")
    ws.cell(row=HGL_HEADER_ROW, column=gov_col, value="Clearance Governing")

    for r in range(HGL_DATA_START, HGL_DATA_END + 1):
        # Crown + 1 ft: HGL at FROM str > upstream crown + 1 -> FAIL.
        ws.cell(
            row=r, column=crown_col,
            value=(
                f'=IF({HGL_COL_HGL_AT_FROM}{r}="","",'
                f'IF({HGL_COL_HGL_AT_FROM}{r}-{HGL_COL_UPSTREAM_CROWN}{r}>1,"FAIL","OK"))'
            ),
        )
        # Rim - 1 ft: rim - HGL at FROM str < 1 -> FAIL.
        rim_expr = rim_formula_fn(r)
        ws.cell(
            row=r, column=rim_col,
            value=(
                f'=LET(rim,{rim_expr},hgl,{HGL_COL_HGL_AT_FROM}{r},'
                f'IF(OR(rim="",hgl=""),"",IF(rim-hgl<1,"FAIL","OK")))'
            ),
        )
        # Governing: toggle picks which rule's verdict shows.
        ws.cell(
            row=r, column=gov_col,
            value=(
                f'=IF(OR({crown_letter}{r}="",{rim_letter}{r}=""),"",'
                f'IF(hglCrownCeilingRule="crown-plus-1ft",'
                f'IF(OR({crown_letter}{r}="FAIL",{rim_letter}{r}="FAIL"),"FAIL","OK"),'
                f'{rim_letter}{r}))'
            ),
        )

    # Set/extend the sheet's print area to cover the three new columns.
    end_col_letter = gov_letter
    ws.print_area = f"'{ws.title}'!$A$1:${end_col_letter}${HGL_DATA_END}"


def add_hgl_crown_ceiling_checks(wb):
    hgl = wb["HGL"]
    # HGL has rim in-place at column N. Row 7 lookup uses the existing cell.
    _add_checks_to_hgl_sheet(
        hgl,
        rim_formula_fn=lambda r: f"{HGL_COL_RIM_IN_PLACE}{r}",
        start_search_letter="S",  # Q is user-input, R is a note - start at S
    )
    hgl25 = wb["HGL(25YEAR)"]
    # HGL(25YEAR) must look up rim from SDC per (From, To) pair.
    _add_checks_to_hgl_sheet(
        hgl25,
        rim_formula_fn=_rim_cell_formula_for_hgl_25year,
        start_search_letter="W",  # Q-V are 25-yr aux columns
    )
```

**Note on `LET`:** openpyxl writes the formula string verbatim; Excel 365 evaluates `LET(...)` natively. If the Excel 365 version in use doesn't have `LET` (unlikely for current Office), swap to inline-repeated subexpressions.

- [ ] **Step 3.4: Run tests**

```bash
python -m pytest test_build_golden.py -v -k "test_hgl_clearance or test_hgl_25year_clearance or test_hgl_print_area or test_hgl_25year_print_area"
```

Expected: all 6 PASS.

- [ ] **Step 3.5: Commit Task 3**

```bash
git add docs/template-analysis/build_golden.py docs/template-analysis/test_build_golden.py
git commit -m "docs(golden): Edit 3 - HGL + HGL(25YEAR) crown/rim/governing clearance columns"
```

---

## Task 4: Edit 4 — annotate_hgl_method

**Files:**
- Modify: `docs/template-analysis/build_golden.py` (implement `annotate_hgl_method`)
- Modify: `docs/template-analysis/test_build_golden.py` (append `test_hgl_method_annotation_*` tests)

**Spec reference:** §5.4.

**Empirical facts:**
- `HGL` row 4 non-blank: B (storm concat), K (`REVIEWED BY:`), L (`B`). Row 3 and later rows 2 have project metadata. The annotation goes to the right of the metadata.
- `HGL(25YEAR)` row 4 non-blank: B (`25 YEAR STORM`).
- Place the annotation at **row 3, column P** on both sheets — above the Edit 3 clearance columns' header, outside the walking data table, inside the extended print area set in Task 3.

- [ ] **Step 4.1: Write failing tests**

Append to `docs/template-analysis/test_build_golden.py`:

```python
HGL_METHOD_ANNOTATION_CELL = "P3"


def test_hgl_method_annotation_on_hgl(golden_built):
    ws = golden_built["HGL"]
    v = ws[HGL_METHOD_ANNOTATION_CELL].value
    assert isinstance(v, str) and v.startswith("=") and "hglMethod" in v, (
        f"HGL!{HGL_METHOD_ANNOTATION_CELL} should be an hglMethod-referencing "
        f"formula, got {v!r}"
    )
    assert "HGL method:" in v, f"annotation label missing: {v!r}"


def test_hgl_method_annotation_on_hgl_25year(golden_built):
    ws = golden_built["HGL(25YEAR)"]
    v = ws[HGL_METHOD_ANNOTATION_CELL].value
    assert isinstance(v, str) and v.startswith("=") and "hglMethod" in v, (
        f"HGL(25YEAR)!{HGL_METHOD_ANNOTATION_CELL} should be an hglMethod-"
        f"referencing formula, got {v!r}"
    )


def test_hgl_method_annotation_inside_print_area(golden_built):
    # P is before the clearance columns extended in Edit 3, so the annotation
    # must fall inside the print area set by Edit 3.
    import re
    from openpyxl.utils import column_index_from_string
    for sheet_name in ("HGL", "HGL(25YEAR)"):
        ws = golden_built[sheet_name]
        m = re.search(r"\$([A-Z]+)\$\d+:\$([A-Z]+)\$\d+", ws.print_area or "")
        assert m, f"{sheet_name} print_area malformed: {ws.print_area!r}"
        end_col = column_index_from_string(m.group(2))
        ann_col = column_index_from_string("P")
        assert ann_col <= end_col, (
            f"{sheet_name} annotation col P (idx {ann_col}) outside print area "
            f"(ends at {m.group(2)}, idx {end_col})"
        )
```

- [ ] **Step 4.2: Run tests to confirm they fail**

```bash
python -m pytest test_build_golden.py -v -k "test_hgl_method_annotation"
```

Expected: all 3 FAIL with `NotImplementedError: Task 4`.

- [ ] **Step 4.3: Implement `annotate_hgl_method`**

Replace the function body in `docs/template-analysis/build_golden.py`:

```python
HGL_METHOD_STAMP_COORD = "P3"


def annotate_hgl_method(wb):
    for sheet_name in ("HGL", "HGL(25YEAR)"):
        ws = wb[sheet_name]
        cell = ws[HGL_METHOD_STAMP_COORD]
        cell.value = '="HGL method: " & hglMethod'
        cell.font = Font(bold=True, italic=True)
        cell.alignment = Alignment(horizontal="right")
```

- [ ] **Step 4.4: Run tests**

```bash
python -m pytest test_build_golden.py -v -k "test_hgl_method_annotation"
```

Expected: all 3 PASS.

- [ ] **Step 4.5: Commit Task 4**

```bash
git add docs/template-analysis/build_golden.py docs/template-analysis/test_build_golden.py
git commit -m "docs(golden): Edit 4 - hglMethod top-of-sheet stamp on HGL sheets"
```

---

## Task 5: Edit 5 — add_u7_small_area_tc_lookup (C_FACTOR column W)

**Files:**
- Modify: `docs/template-analysis/build_golden.py` (implement `add_u7_small_area_tc_lookup`)
- Modify: `docs/template-analysis/test_build_golden.py` (append `test_cfactor_tc_*` tests)

**Spec reference:** §5.5 (column W placement — correction vs Spec 1 U7's column-I claim).

**Empirical facts:**
- `C_FACTOR` row 2 has primary headers: B=Structure, C=Total Area (SF), D=Total Area (Ac), M=Weighted C Factor, R=C FACTOR, V=Time of Concentration (Tc).
- Column `I` is "C-Soil Group Impervious Area" (consumed by composite-C formula). **Do not place the lookup on `I`.**
- Column `W` is empty for all data rows; place the lookup there.
- Data rows: 6–88.

- [ ] **Step 5.1: Write failing tests**

Append to `docs/template-analysis/test_build_golden.py`:

```python
CFACTOR_TC_COL_LETTER = "W"
CFACTOR_TC_HEADER_ROW = 2
CFACTOR_DATA_START = 6
CFACTOR_DATA_END = 88


def test_cfactor_tc_header_on_column_w(golden_built):
    ws = golden_built["C_FACTOR"]
    v = ws[f"{CFACTOR_TC_COL_LETTER}{CFACTOR_TC_HEADER_ROW}"].value
    assert v == "Tc (Table 3-3, small-area)", (
        f"C_FACTOR!{CFACTOR_TC_COL_LETTER}{CFACTOR_TC_HEADER_ROW} should be "
        f"the Table 3-3 header, got {v!r}"
    )


def test_cfactor_tc_formula_on_all_data_rows(golden_built):
    ws = golden_built["C_FACTOR"]
    for r in range(CFACTOR_DATA_START, CFACTOR_DATA_END + 1):
        v = ws[f"{CFACTOR_TC_COL_LETTER}{r}"].value
        # Accept the builder formula OR a pre-existing formula that references
        # D and M (treated as "already there" by the spec).
        assert isinstance(v, str) and v.startswith("="), (
            f"C_FACTOR!{CFACTOR_TC_COL_LETTER}{r} missing formula, got {v!r}"
        )
        assert f"D{r}" in v or f"$D${r}" in v or "D6" in v, (
            f"C_FACTOR!{CFACTOR_TC_COL_LETTER}{r} should reference D column: {v!r}"
        )


def test_cfactor_tc_formula_structure_table_3_3(golden_built):
    ws = golden_built["C_FACTOR"]
    v6 = ws[f"{CFACTOR_TC_COL_LETTER}{CFACTOR_DATA_START}"].value
    # Formula must encode the four Table 3-3 thresholds.
    for threshold in ("0.8", "0.65", "0.4"):
        assert threshold in v6, (
            f"Table 3-3 threshold {threshold!r} missing from W6 formula: {v6!r}"
        )
    for tc_val in ("5", "7", "10", "15"):
        assert tc_val in v6, f"Tc value {tc_val!r} missing from W6 formula: {v6!r}"


def test_cfactor_column_v_untouched_by_edit_5(repaired_wb, golden_built):
    # Column V (user-typed Tc) must be identical pre/post.
    w_wip = repaired_wb["C_FACTOR"]
    w_gold = golden_built["C_FACTOR"]
    for r in range(CFACTOR_DATA_START, CFACTOR_DATA_END + 1):
        assert w_wip[f"V{r}"].value == w_gold[f"V{r}"].value, (
            f"C_FACTOR!V{r} changed: wip={w_wip[f'V{r}'].value!r}, "
            f"golden={w_gold[f'V{r}'].value!r}"
        )


def test_cfactor_column_i_untouched_by_edit_5(repaired_wb, golden_built):
    # Column I is C-Soil Group Impervious Area (feeds composite-C on col M).
    # Edit 5 must NOT touch it, regardless of what Spec-1 U7 claimed.
    w_wip = repaired_wb["C_FACTOR"]
    w_gold = golden_built["C_FACTOR"]
    for r in range(CFACTOR_DATA_START, CFACTOR_DATA_END + 1):
        assert w_wip[f"I{r}"].value == w_gold[f"I{r}"].value, (
            f"C_FACTOR!I{r} unexpectedly changed by Edit 5"
        )
```

- [ ] **Step 5.2: Run tests to confirm they fail**

```bash
python -m pytest test_build_golden.py -v -k "test_cfactor_tc or test_cfactor_column"
```

Expected: all 5 FAIL with `NotImplementedError: Task 5`.

- [ ] **Step 5.3: Implement `add_u7_small_area_tc_lookup`**

Replace the function body in `docs/template-analysis/build_golden.py`:

```python
CFACTOR_SHEET = "C_FACTOR"
CFACTOR_TC_COL = "W"
CFACTOR_TC_HDR_ROW = 2
CFACTOR_DATA_RANGE = range(6, 89)  # inclusive 6..88


def add_u7_small_area_tc_lookup(wb):
    ws = wb[CFACTOR_SHEET]
    skipped = []

    ws[f"{CFACTOR_TC_COL}{CFACTOR_TC_HDR_ROW}"] = "Tc (Table 3-3, small-area)"

    for r in CFACTOR_DATA_RANGE:
        existing = ws[f"{CFACTOR_TC_COL}{r}"].value
        if existing is None or existing == "":
            # Blank - add the lookup.
            pass
        elif isinstance(existing, str) and existing.startswith("=") and (
            f"D{r}" in existing or f"$D${r}" in existing
        ) and (f"M{r}" in existing or f"$M${r}" in existing):
            # Already looks like our formula from a prior run - leave it.
            continue
        else:
            # Something else is in the cell - don't clobber it.
            skipped.append(r)
            continue
        ws[f"{CFACTOR_TC_COL}{r}"] = (
            f'=IF(D{r}="","",'
            f'IF(D{r}>2,"",'
            f'IF(M{r}>=0.8,5,'
            f'IF(M{r}>=0.65,7,'
            f'IF(M{r}>=0.4,10,15)))))'
        )

    if skipped:
        print(
            f"Edit 5: skipped C_FACTOR!{CFACTOR_TC_COL} on rows "
            f"{skipped} (pre-existing unrelated content)"
        )
```

- [ ] **Step 5.4: Run tests**

```bash
python -m pytest test_build_golden.py -v -k "test_cfactor_tc or test_cfactor_column"
```

Expected: all 5 PASS.

- [ ] **Step 5.5: Commit Task 5**

```bash
git add docs/template-analysis/build_golden.py docs/template-analysis/test_build_golden.py
git commit -m "docs(golden): Edit 5 - C_FACTOR column W Table 3-3 small-area Tc lookup

Spec-1 U7 mis-claimed the lookup lived on column I. Column I is
actually 'C-Soil Group Impervious Area' (feeds composite-C on col M).
Placing the Table 3-3 lookup on W - first empty column after V
(authoritative user-typed Tc) - keeps both existing semantics intact.
Column V remains the authoritative Tc that STORM DRAIN COMPS!E reads;
W is advisory only."
```

---

## Task 6: Edit 6 — annotate_equations_sheet

**Files:**
- Modify: `docs/template-analysis/build_golden.py` (implement `annotate_equations_sheet`)
- Modify: `docs/template-analysis/test_build_golden.py` (append `test_equations_*` tests)

**Spec reference:** §5.6.

**Empirical facts:**
- `EQUATIONS + INSTRUCTIONS` max_row = 49, max_col = 24. Append new content starting at row 51 (one blank spacer).
- The append is idempotent: scan for the section header `"Design-Rule Toggles (Config sheet)"` in column A; if present, overwrite starting at that row instead of appending.

- [ ] **Step 6.1: Write failing tests**

Append to `docs/template-analysis/test_build_golden.py`:

```python
TOGGLES_HEADER = "=== Design-Rule Toggles (Config sheet) ==="
CITATIONS_HEADER = "=== Citation refresh (Spec 1 U1-U7) ==="


def _find_text_row(ws, needle):
    for row in ws.iter_rows():
        for cell in row:
            if cell.value == needle:
                return cell.row
    return None


def test_equations_toggles_section_header_present(golden_built):
    ws = golden_built["EQUATIONS + INSTRUCTIONS"]
    assert _find_text_row(ws, TOGGLES_HEADER) is not None, (
        f"{TOGGLES_HEADER!r} missing from EQUATIONS + INSTRUCTIONS"
    )


def test_equations_citations_section_header_present(golden_built):
    ws = golden_built["EQUATIONS + INSTRUCTIONS"]
    assert _find_text_row(ws, CITATIONS_HEADER) is not None, (
        f"{CITATIONS_HEADER!r} missing from EQUATIONS + INSTRUCTIONS"
    )


def test_equations_live_toggle_cells_present(golden_built):
    ws = golden_built["EQUATIONS + INSTRUCTIONS"]
    found = {"junctionAngleRule": False, "hglCrownCeilingRule": False, "hglMethod": False}
    for row in ws.iter_rows():
        for cell in row:
            v = cell.value
            if not isinstance(v, str) or not v.startswith("="):
                continue
            for name in found:
                if name in v:
                    found[name] = True
    for name, ok in found.items():
        assert ok, f"no live-reference formula found for {name!r}"


def test_equations_pg_citation_appears(golden_built):
    ws = golden_built["EQUATIONS + INSTRUCTIONS"]
    found = False
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "PG C I-2" in cell.value:
                found = True
    assert found, "PG C I-2 citation (HGL clearance disclosure) missing"
```

- [ ] **Step 6.2: Run tests to confirm they fail**

```bash
python -m pytest test_build_golden.py -v -k "test_equations_"
```

Expected: all 4 FAIL with `NotImplementedError: Task 6`.

- [ ] **Step 6.3: Implement `annotate_equations_sheet`**

Replace the function body in `docs/template-analysis/build_golden.py`:

```python
EQ_SHEET = "EQUATIONS + INSTRUCTIONS"
EQ_TOGGLES_HEADER = "=== Design-Rule Toggles (Config sheet) ==="
EQ_CITATIONS_HEADER = "=== Citation refresh (Spec 1 U1-U7) ==="


def _eq_find_row(ws, needle, col=1):
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=col).value == needle:
            return r
    return None


def annotate_equations_sheet(wb):
    ws = wb[EQ_SHEET]

    # Idempotent: start writing at an existing header row if we find one.
    start = _eq_find_row(ws, EQ_TOGGLES_HEADER)
    if start is None:
        start = ws.max_row + 2  # one blank row spacer

    def write(row_offset, col, value, bold=False):
        c = ws.cell(row=start + row_offset, column=col, value=value)
        if bold:
            c.font = Font(bold=True)

    # Clear 60 rows below `start` so a prior longer annotation gets
    # replaced cleanly on idempotent re-run.
    for r in range(start, min(start + 60, ws.max_row + 60)):
        for col in range(1, 4):
            ws.cell(row=r, column=col).value = None

    # Toggles section.
    write(0, 1, EQ_TOGGLES_HEADER, bold=True)
    write(1, 1, "junctionAngleRule =")
    write(1, 2, "=junctionAngleRule")
    write(2, 1, "Controlling-angle procedure at 2-inflow junctions.")
    write(3, 1, "  MDSHA Ch. 5 / MCDOT §4.3.2.3: smaller Lv's angle controls  [smaller-loss, default]")
    write(4, 1, "  PG SWM Ch. 8 p. 8-27 (Sept 30 2014): larger H's angle controls  [larger-loss]")
    write(5, 1, "  Set on Config!B3. Affects STORM DRAIN COMPS!AD (controlling angle) and downstream Hb.")

    write(7, 1, "hglCrownCeilingRule =")
    write(7, 2, "=hglCrownCeilingRule")
    write(8, 1, "HGL vertical-clearance ceiling.")
    write(9, 1, '  MCDOT §4.3.1: HGL ≤ Crown + 1 ft AND HGL ≤ Rim − 1 ft  [crown-plus-1ft, default]')
    write(10, 1, '  PG C I-2: HGL ≤ Rim − 12" only (pipes may surcharge within the structure)  [rim-only]')
    write(11, 1, "  Set on Config!B4. Affects HGL and HGL(25YEAR) \"Clearance Governing\" column.")

    write(13, 1, "hglMethod =")
    write(13, 2, "=hglMethod")
    write(14, 1, "HGL-walk method.")
    write(15, 1, "  HEC-22 EGL (d/s crown floor) - HEC-22 §7.4 standard  [HEC-22, default]")
    write(16, 1, "  Legacy both-end crown floor - firm historical convention  [legacy]")
    write(17, 1, "  Set on Config!B5. Label-only in this template; Spec 3 wires xlsx HGL computation.")

    # Citations section.
    write(20, 1, EQ_CITATIONS_HEADER, bold=True)
    write(21, 1, "Junction-loss primary source - MDSHA Drainage Manual Ch. 5 p. 5-26 (Sept 2023), Fig 5-8")
    write(22, 1, "  (mirrored by MCDOT §4.3.2.3 p. 46, Revised Final June 2014).")
    write(23, 1, "Pipe slope - MCDOT §4.3.3(k) (15\" and 18\" ≥ 1.0%); our rule <24\" ≥ 1.0% is a touch")
    write(24, 1, "  more conservative (catches 21\" too) - intentional.")
    write(25, 1, "Time of concentration for small areas (≤ 2 acres) - MCDOT §3.2.1 Table 3-3:")
    write(26, 1, "  C ≥ 0.80 → 5 min; 0.65-0.79 → 7; 0.40-0.64 → 10; ≤ 0.39 → 15.")
    write(27, 1, "Composite C - MCDOT §3.4 area-weighted; PG SWM Ch. 8 §8.2.1 same intent.")
    write(28, 1, "PG DPIE checklist items affecting calculator-visible rules:")
    write(29, 1, "  C-19 (15\" min pipe), G-8 (min cover: 1 ft RCP, 2 ft flexible),")
    write(30, 1, "  G-9 (0.1 ft min drop through structure), C-20 (400 ft max access spacing),")
    write(31, 1, "  C-21 (≤ 45° pipe-to-flat-wall), H-6 (last reach to outfall ≤ 1%),")
    write(32, 1, "  L-4 (channel armoring v > 5 fps cut / 4 fps fill),")
    write(33, 1, "  I-2 (HGL ≤ Rim − 1 ft; the crown-ceiling toggle disclosure).")
```

- [ ] **Step 6.4: Run tests, incl. the smoke test**

```bash
python -m pytest test_build_golden.py -v -k "test_equations_ or test_skeleton"
```

Expected: `test_equations_*` all PASS; `test_skeleton_runs_end_to_end` now PASSES too — the end-to-end builder is finally complete.

- [ ] **Step 6.5: Commit Task 6**

```bash
git add docs/template-analysis/build_golden.py docs/template-analysis/test_build_golden.py
git commit -m "docs(golden): Edit 6 - EQUATIONS + INSTRUCTIONS toggle + citation annotation"
```

---

## Task 7: Workbook invariants + idempotency + drift catcher

**Files:**
- Modify: `docs/template-analysis/test_build_golden.py` (append workbook-wide tests)

**Spec reference:** §8 — `TestWorkbookInvariants` class (adapted to function-based).

- [ ] **Step 7.1: Write the invariant tests**

Append to `docs/template-analysis/test_build_golden.py`:

```python
def test_invariants_zero_ref_errors(golden_built):
    for ws in golden_built.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                text = v if isinstance(v, str) else getattr(v, "text", None)
                if isinstance(text, str):
                    assert "#REF!" not in text, (
                        f"{ws.title}!{cell.coordinate} contains #REF!: {text!r}"
                    )


def test_invariants_zero_broken_defined_names(golden_built):
    for name in golden_built.defined_names:
        dn = golden_built.defined_names[name]
        val = getattr(dn, "value", None) or str(dn)
        assert "#REF!" not in val, (
            f"defined name {name!r} resolves to #REF!: {val!r}"
        )


def test_invariants_seventeen_sheets_config_last(golden_built):
    assert len(golden_built.sheetnames) == 17
    assert golden_built.sheetnames[-1] == "Config"


def test_invariants_original_sheet_order_preserved(repaired_wb, golden_built):
    assert [n for n in golden_built.sheetnames if n != "Config"] == repaired_wb.sheetnames


def test_invariants_no_external_links(golden_built):
    # Mirrors Spec-1 test_workbook_has_no_external_links on the WIP side.
    for ws in golden_built.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                text = v if isinstance(v, str) else getattr(v, "text", None)
                if isinstance(text, str):
                    # External workbook refs look like "[filename.xlsx]SheetName!A1".
                    assert not ("[" in text and ".xlsx]" in text), (
                        f"{ws.title}!{cell.coordinate} has external link: {text!r}"
                    )


def test_invariants_builder_idempotent(golden_built_twice):
    first, second = golden_built_twice
    # Defined-name sets match.
    assert set(first.defined_names) == set(second.defined_names), (
        "defined-name set changed on re-run"
    )
    # Per-sheet cell values match on every sheet, limited to the used range.
    for sheet in first.sheetnames:
        ws1 = first[sheet]
        ws2 = second[sheet]
        max_r = max(ws1.max_row, ws2.max_row)
        max_c = max(ws1.max_column, ws2.max_column)
        for r in range(1, max_r + 1):
            for c in range(1, max_c + 1):
                v1 = ws1.cell(row=r, column=c).value
                v2 = ws2.cell(row=r, column=c).value
                t1 = v1 if isinstance(v1, str) else getattr(v1, "text", None)
                t2 = v2 if isinstance(v2, str) else getattr(v2, "text", None)
                if t1 is not None or t2 is not None:
                    assert t1 == t2, (
                        f"idempotency drift on {sheet}!{ws1.cell(row=r,column=c).coordinate}: "
                        f"{t1!r} vs {t2!r}"
                    )
                else:
                    assert v1 == v2, (
                        f"idempotency drift on {sheet}!{ws1.cell(row=r,column=c).coordinate}: "
                        f"{v1!r} vs {v2!r}"
                    )
```

- [ ] **Step 7.2: Run invariants**

```bash
python -m pytest test_build_golden.py -v -k "test_invariants"
```

Expected: all 6 PASS. If any fail:
- `#REF!` present → Edit 2's formula construction has a bad cell address. Re-check `rewire_junction_angle_rule`.
- idempotency drift → likely Edit 6 is appending content on re-run. The `_eq_find_row` + overwrite pattern should prevent it; check the "clear 60 rows below `start`" range covers your actual block length.

- [ ] **Step 7.3: Run the full test suite to confirm nothing regressed**

```bash
python -m pytest -v
```

Expected: all tests PASS (both the Spec-1 `test_repair.py` suite and the new `test_build_golden.py`).

- [ ] **Step 7.4: Commit Task 7**

```bash
git add docs/template-analysis/test_build_golden.py
git commit -m "docs(golden): workbook invariants + idempotency tests"
```

---

## Task 8: Build and commit the golden xlsx

**Files:**
- Create: `docs/template_golden.xlsx` (generated artifact)

- [ ] **Step 8.1: Run the builder end-to-end**

Run (from `docs/`):

```bash
python template-analysis/build_golden.py template_wip_new.xlsx template_golden.xlsx
```

Expected output:

```
wrote template_golden.xlsx
```

If Edit 5 prints a `skipped` warning, note the row list — those rows had unrelated content and won't carry the Table 3-3 lookup. That is informational, not a failure.

- [ ] **Step 8.2: Quick-check the output**

Run (from `docs/`):

```bash
python -c "
import openpyxl
wb = openpyxl.load_workbook('template_golden.xlsx', data_only=False)
print('sheets:', len(wb.sheetnames), '-', wb.sheetnames[-1])
print('names:', [n for n in wb.defined_names if n in ('junctionAngleRule','hglCrownCeilingRule','hglMethod')])
print('Config B3/B4/B5:', wb['Config']['B3'].value, '/', wb['Config']['B4'].value, '/', wb['Config']['B5'].value)
"
```

Expected:
```
sheets: 17 - Config
names: ['junctionAngleRule', 'hglCrownCeilingRule', 'hglMethod']
Config B3/B4/B5: smaller-loss / crown-plus-1ft / HEC-22 EGL (d/s crown floor)
```

- [ ] **Step 8.3: Commit the generated xlsx — flagged as behavior change**

Run (from repo root):

```bash
git add docs/template_golden.xlsx
git commit -m "docs(golden): generate template_golden.xlsx

BEHAVIOR CHANGE: the default junctionAngleRule on Config is 'smaller-loss'
(MDSHA Ch. 5 / MCDOT §4.3.2.3 primary source). The predecessor WIP template
computed with PG-style 'larger-loss' by default. PG-reviewed projects must
flip Config!B3 to 'larger-loss' before computing.

Generated by: python template-analysis/build_golden.py \\
  template_wip_new.xlsx template_golden.xlsx

Source WIP SHA-256 pinned in template-analysis/conftest.py so any
WIP-side change forces a conscious rebuild review."
```

---

## Task 9: Calculator import contract doc

**Files:**
- Create: `docs/template-analysis/calculator-import-contract.md`

**Spec reference:** §7.

- [ ] **Step 9.1: Write the contract doc**

Create `docs/template-analysis/calculator-import-contract.md`:

````markdown
# Calculator ↔ xlsx Import/Export Contract

**Contract-Version:** 1

Specifies how the HTML calculator (and the companion visualizer) read from and
write to the two xlsx shapes shipped by this project:

- **Latest sample template** — `docs/template_wip_new.xlsx` (Spec-1 repaired
  WIP; 16 sheets; no `Config` sheet).
- **Golden template** — `docs/template_golden.xlsx` (Spec-2 output; 17 sheets
  with `Config` last).

Spec 3 is the first consumer of this contract. Spec 2 ships the contract as a
doc so the read/write surface is agreed before any code is written.

---

## 1. Shape detection

On import, the calculator reads `wb.defined_names` (via SheetJS equivalent).

- `junctionAngleRule` present → **golden** shape. Read all three toggles from
  their named ranges.
- `junctionAngleRule` absent → **legacy** shape. Apply the three toggle
  defaults.

One branch. No heuristic sniffing (no "guess by sheet count," no "guess by
header text").

## 2. Toggle values

### Golden

| Named range | Values (first is default) |
|---|---|
| `junctionAngleRule` | `smaller-loss` \| `larger-loss` |
| `hglCrownCeilingRule` | `crown-plus-1ft` \| `rim-only` |
| `hglMethod` | `HEC-22 EGL (d/s crown floor)` \| `legacy both-end crown floor` |

### Legacy

Named ranges absent. Calculator uses the same defaults a golden file would
carry out of the box:

- `junctionAngleRule = "smaller-loss"`
- `hglCrownCeilingRule = "crown-plus-1ft"`
- `hglMethod = "HEC-22 EGL (d/s crown floor)"`

## 3. Pipe-row read path (both shapes — identical)

Sheet: `STORM DRAIN COMPS`, Excel Table `Table4`, rows 10–98.
Jurisdiction / design-storm cells: `T3` / `H3` on the same sheet.

| Source | Calculator field |
|---|---|
| `STORM DRAIN COMPS!A{row}` | `fromId` |
| `STORM DRAIN COMPS!B{row}` | `toId` |
| `STORM DRAIN COMPS!N{row}` | `pipeDiameterIn` |
| `STORM DRAIN COMPS!O{row}` | `pipeLengthFt` |
| `STORM DRAIN COMPS!P{row}` | `invertUsFt` |
| `STORM DRAIN COMPS!Q{row}` | `invertDsFt` |
| `STORM DRAIN COMPS!R{row}` | `inflowAngleDeg` — "Angle Out of Pipe (Deg)" |
| `STORM DRAIN COMPS!S{row}` | `manningN` |
| `STORM DRAIN COMPS!AA{row}` | `structureType` (Inlet/Manhole/Bend/Junction/Flow Splitter/Outfall) |
| `STORM DRAIN COMPS!AB{row}` | `rimElevFt` |
| `STORM DRAIN COMPS!AG{row}` | `inflowAngle1Deg` (2-inflow structures) |
| `STORM DRAIN COMPS!AH{row}` | `inflowAngle2Deg` (2-inflow structures) |
| `STORM DRAIN COMPS!AK{row}` | `lateralFlowCfs` (user-typed) |
| `STORM DRAIN COMPS!T3` | `jurisdiction` |
| `STORM DRAIN COMPS!H3` | `designStormYr` |

Rows where `A{row}` is blank are skipped.

**Note:** Spec-1's analysis doc `01-storm-drain-comps.md` lists column `R` as
"Manning's n." The actual header-row label is "Angle Out of Pipe (Deg) -
Whole #", and the AD/AN controlling-angle formulas reference it as an angle.
Spec-3 implementers: read the live header row, not the analysis doc.

## 4. Drainage-area read path (both shapes — identical)

Sheet: `C_FACTOR`, rows 6–88.

| Source | Calculator field |
|---|---|
| `C_FACTOR!B{row}` | `rowId` (join key to `STORM DRAIN COMPS!A`) |
| `C_FACTOR!C{row}` | `areaSf` |
| `C_FACTOR!M{row}` | `compositeC` (prefers user override on `R` via existing `IFERROR`) |
| `C_FACTOR!V{row}` | `tcMin` — authoritative |

**Advisory columns the calculator MUST NOT read as authoritative:**
- `C_FACTOR!W{row}` (Table 3-3 small-area Tc lookup; golden only) — informational.

## 5. HGL sheets are not read on import

The calculator computes HGL internally from the imported pipe rows. `HGL`,
`HGL(25YEAR)`, and all six print-report sheets are review artifacts, not
persistence. Never round-trip HGL numbers through them.

## 6. Sheets the calculator ignores on import

- All six print-report sheets (`MCDOT PIPE COMPS-DESIGN`, `MCDOT INLET
  COMPS-DESIGN`, `MCDOT HGL-DESIGN`, `SHA SD-61.1-420-DESIGN`, `SHA
  (2-YR)SPREAD 61.1-491`, `SHA (25-YR)HGL 61.1-493`).
- `PIPE SCHEDULE`, `STRUCTURE SCHEDULE` (hand-maintained inventories).
- `DATA`, `DATA2` (static lookup tables).
- `EQUATIONS + INSTRUCTIONS` (reference text).
- `INLET SPACING` (inlet-spread hydraulics stay in xlsx; the calculator
  doesn't own them).

## 7. Export (calculator → xlsx)

The calculator writes back into **input columns only** on `STORM DRAIN COMPS`
and `C_FACTOR`:

- `STORM DRAIN COMPS!A, B, N, O, P, Q, R, S, AA, AB, AG, AH, AK` plus `T3`
  and `H3`.
- `C_FACTOR!B, C, V`. (Composite C is computed by the xlsx formula on `M`
  from land-use sub-areas; the calculator writes `R` if the project uses the
  simple two-zone composite override, otherwise leaves `R` blank.)
- `Config!B3, B4, B5` on the golden shape only — writes the three toggle
  values. Does not touch columns `C` (citations), `E:G` (dropdown helpers),
  or row 1 (header).

The calculator **never writes to any formula-driven column** (C_FACTOR M, O,
P; STORM DRAIN COMPS C, D, E, F, G, H, I, J, K, L, M, T–BD, and the Edit-2
helper column; any HGL sheet cell; any print-report cell). Reopening the file
in Excel recomputes every derived value from the inputs.

## 8. Versioning

Any change to the read set, the write set, or the detection rule bumps
`Contract-Version` in this file. Spec 3's calculator import/export reads this
header and either supports both versions or documents the migration path in
a new section here.
````

- [ ] **Step 9.2: Commit Task 9**

```bash
git add docs/template-analysis/calculator-import-contract.md
git commit -m "docs(golden): add calculator-import-contract.md for Spec 3"
```

---

## Task 10: Update template-analysis README

**Files:**
- Modify: `docs/template-analysis/README.md`

- [ ] **Step 10.1: Read current README state**

Look at the existing `## Scripts` section at the bottom of `docs/template-analysis/README.md`. It currently lists `extract.py`, `repair.py`, `test_extract.py`, `test_repair.py`.

- [ ] **Step 10.2: Append build_golden.py and contract**

Replace the `## Scripts` section with:

```markdown
## Scripts

- `extract.py` — Pass A automated JSON dump. Committed output: `pass_a.json`.
- `repair.py` — applies R1–R5 from the Spec-1 design doc. Reads `../template_wip_new_pre-repair.xlsx`, writes `../template_wip_new.xlsx`.
- `build_golden.py` — Spec-2 builder. Reads `../template_wip_new.xlsx` (SHA-pinned in `conftest.py`), applies six Edits (Config sheet, junction-angle toggle, HGL clearance checks, hglMethod stamp, C_FACTOR Table 3-3 Tc lookup, EQUATIONS annotation), writes `../template_golden.xlsx`.
- `test_extract.py`, `test_repair.py`, `test_build_golden.py` — pytest suites. Run `python -m pytest` from this directory.

## Contracts

- `calculator-import-contract.md` — Spec 3 read/write contract for both xlsx shapes (WIP + golden).
```

Also update the overview paragraph: find the line that says "Per-tab analysis of `docs/template_wip_new.xlsx`" or similar at the top, and add after it:

```markdown
> **Golden template:** `docs/template_golden.xlsx` is the Spec-2 output produced by `build_golden.py` from the WIP. It carries a new `Config` sheet (tab 17) with three project-level toggles that Spec 3's calculator/visualizer read on import. See `calculator-import-contract.md`.
```

- [ ] **Step 10.3: Commit Task 10**

```bash
git add docs/template-analysis/README.md
git commit -m "docs(golden): README adds build_golden.py and import contract"
```

---

## Task 11: Run full suite + acceptance checklist

- [ ] **Step 11.1: Full-suite green check**

Run (from `docs/template-analysis/`):

```bash
python -m pytest -v
```

Expected: every test passes. Record the final count in the next step.

- [ ] **Step 11.2: Final `openpyxl` scan on the committed golden**

Run (from `docs/`):

```bash
python -c "
import openpyxl
wb = openpyxl.load_workbook('template_golden.xlsx', data_only=False)
ref_hits = 0
for ws in wb.worksheets:
    for row in ws.iter_rows():
        for cell in row:
            v = cell.value
            t = v if isinstance(v,str) else getattr(v,'text',None)
            if isinstance(t,str) and '#REF!' in t: ref_hits += 1
broken_names = [n for n in wb.defined_names if '#REF!' in (getattr(wb.defined_names[n],'value',None) or str(wb.defined_names[n]))]
print(f'sheets: {len(wb.sheetnames)}')
print(f'last tab: {wb.sheetnames[-1]}')
print(f'defined names of interest: {sorted(n for n in wb.defined_names if n in (\"junctionAngleRule\",\"hglCrownCeilingRule\",\"hglMethod\"))}')
print(f'#REF! formula hits: {ref_hits}')
print(f'broken defined names: {broken_names}')
"
```

Expected:
```
sheets: 17
last tab: Config
defined names of interest: ['hglCrownCeilingRule', 'hglMethod', 'junctionAngleRule']
#REF! formula hits: 0
broken defined names: []
```

- [ ] **Step 11.3: Walk the acceptance checklist**

Open `docs/superpowers/specs/2026-11-25-golden-template-design.md` §9 and confirm each box:

- [ ] `docs/template-analysis/build_golden.py` exists with `main(src, dst)` CLI.
- [ ] `docs/template-analysis/test_build_golden.py` exists and all tests pass.
- [ ] `docs/template-analysis/calculator-import-contract.md` exists and covers both shapes.
- [ ] `docs/template_golden.xlsx` committed; openpyxl scan shows 0 `#REF!`, 0 broken names, 0 external links, 17 sheets, 3 new named ranges.
- [ ] `docs/template-analysis/README.md` updated with `build_golden.py` + contract listing.
- [ ] Manual Excel verification deferred to user — note this status in the acceptance commit.
- [ ] No files under `drainage-calculator/` touched (`git log --name-only HEAD~N..HEAD | grep -c drainage-calculator` should return 0 for N = number of Task commits).
- [ ] `CLAUDE.md` still under 200 lines (`wc -l CLAUDE.md` in repo root).
- [ ] Commit for Task 2 contains the `BEHAVIOR CHANGE:` marker; commit for Task 8 does too.

- [ ] **Step 11.4: Acceptance commit**

Run (from repo root):

```bash
git commit --allow-empty -m "docs(golden): Spec 2 acceptance — all tests pass, manual Excel verify deferred to user

- 17-sheet golden template committed (docs/template_golden.xlsx).
- build_golden.py + test_build_golden.py cover Edits 1-6, invariants,
  idempotency, WIP drift detection (SHA-pinned).
- calculator-import-contract.md committed for Spec 3.
- Manual Excel-365 verification (Spec 2 §8 manual steps 1-5) deferred
  to user per the Spec-1 acceptance precedent."
```

- [ ] **Step 11.5: Summarize back to the user**

Report:
- Number of commits made (expect ~11: scaffolding + 6 edits + invariants + build + contract + README + acceptance).
- Full-suite test count (Spec-1 + Spec-2 combined).
- Manual verification steps 1–5 from spec §8 the user needs to perform in Excel.

---

## Notes for the executor

**Idempotency testing.** Every edit function must be idempotent — re-running on an already-golden file produces the same output. The `golden_built_twice` fixture catches drift. If your test fails only on the second run, the edit is appending instead of replacing.

**openpyxl + ArrayFormula.** When reading formulas from a WIP cell, some are returned as `openpyxl.worksheet.formula.ArrayFormula` objects (CSE/dynamic-array formulas), not plain strings. Always use `getattr(value, "text", None) or (value if isinstance(value, str) else None)` to extract the formula string, as shown in the test helpers.

**openpyxl + defined_names.** On openpyxl 3.1, `wb.defined_names` behaves like a dict — iterate over names with `for name in wb.defined_names`, access with `wb.defined_names[name]`, delete with `del wb.defined_names[name]`. Add new ones via `wb.defined_names[name] = DefinedName(name=name, attr_text=...)`. The `attr_text` on `DefinedName` holds the cell reference string.

**Running tests from the right directory.** Pytest should be invoked from `docs/template-analysis/` because `conftest.py`'s module-scoped fixtures run `python repair.py ...` and `python build_golden.py ...` as subprocesses with those scripts in the same directory.

**When a test fails:** read the assertion message carefully. The tests are written to name the failure path (e.g., "helper column had pre-existing content at row N"). Follow the message's hint — don't blindly edit the test to pass.

