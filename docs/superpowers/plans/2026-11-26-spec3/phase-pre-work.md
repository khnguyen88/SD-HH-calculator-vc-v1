# Spec 3 — Pre-work (Tasks 1–2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Clean up unused DATA2 columns and correct two per-tab analysis docs before Phase 1 starts. Small, safe, independent commits.

**Spec:** `docs/superpowers/specs/2026-11-26-spec3-three-shape-bidirectional-design.md` §3

**Shared conventions:** see `docs/superpowers/plans/2026-11-26-spec3-three-shape-bidirectional.md` (the index file) for shell-CWD and build conventions.

---

## Task 1: DATA2 cleanup script + repair-pipeline integration

**Files:**
- Create: `docs/template-analysis/cleanup_data2.py`
- Create: `docs/template-analysis/test_cleanup_data2.py`
- Modify: `docs/template-analysis/repair.py`
- Regenerate: `docs/template_wip_new.xlsx`, `docs/template_golden.xlsx`

- [ ] **Step 1.1: Write the failing test**

Create `docs/template-analysis/test_cleanup_data2.py`:

```python
"""Verify DATA2 cleanup invariants.

After cleanup:
  - DATA2!A1:C101 unchanged (headers + values preserved).
  - DATA2!D1:L101 completely empty.
  - STORM DRAIN COMPS VLOOKUP formulas unchanged in string form.
"""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
WIP = HERE.parent / "template_wip_new.xlsx"
GOLDEN = HERE.parent / "template_golden.xlsx"


def _assert_data2_clean(wb):
    ws = wb["DATA2"]
    for col_letter in ("A", "B", "C"):
        v = ws[f"{col_letter}1"].value
        assert v is not None, f"DATA2!{col_letter}1 header missing"
    assert ws["A2"].value == 0
    assert ws["B101"].value == 1
    for col_letter in ("D", "E", "F", "G", "H", "I", "J", "K", "L"):
        for r in range(1, 102):
            v = ws[f"{col_letter}{r}"].value
            assert v in (None, ""), (
                f"DATA2!{col_letter}{r} should be empty, got {v!r}"
            )


def _assert_sdc_vlookup_intact(wb):
    sdc = wb["STORM DRAIN COMPS"]
    az10 = sdc["AZ10"].value
    bb10 = sdc["BB10"].value
    assert az10 == '=IFERROR(VLOOKUP(AY10,DATA2!$A$2:$D$101,2),"")', (
        f"AZ10 formula drifted: {az10!r}"
    )
    assert bb10 == '=IFERROR(VLOOKUP(AY10,DATA2!$A$2:$D$101,3),"")', (
        f"BB10 formula drifted: {bb10!r}"
    )


def test_wip_data2_cleaned():
    wb = openpyxl.load_workbook(WIP, data_only=False)
    _assert_data2_clean(wb)
    _assert_sdc_vlookup_intact(wb)


def test_golden_data2_cleaned():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    _assert_data2_clean(wb)
    _assert_sdc_vlookup_intact(wb)
```

- [ ] **Step 1.2: Run the test to confirm it fails**

```bash
cd docs && pytest template-analysis/test_cleanup_data2.py -v
```

Expected: fails on `test_wip_data2_cleaned` because DATA2 cols D–L still carry old values (e.g., E1 is `'angle'`).

- [ ] **Step 1.3: Write `cleanup_data2.py`**

Create `docs/template-analysis/cleanup_data2.py`:

```python
"""Clear DATA2 columns D-L in a workbook (Spec 3 pre-work).

Keeps A-C untouched. VLOOKUP ranges on STORM DRAIN COMPS stay as
$A$2:$D$101 — all 178 formulas unchanged. Idempotent.

Usage:
    python cleanup_data2.py <input.xlsx> <output.xlsx>
"""
import sys
from pathlib import Path

import openpyxl


COLUMNS_TO_CLEAR = ("D", "E", "F", "G", "H", "I", "J", "K", "L")
ROW_RANGE = range(1, 102)


def clean_data2(wb):
    ws = wb["DATA2"]
    for col_letter in COLUMNS_TO_CLEAR:
        for r in ROW_RANGE:
            cell = ws[f"{col_letter}{r}"]
            if cell.value is not None:
                cell.value = None
    return wb


def main(src, dst):
    wb = openpyxl.load_workbook(src)
    clean_data2(wb)
    wb.save(dst)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: cleanup_data2.py <src.xlsx> <dst.xlsx>", file=sys.stderr)
        sys.exit(2)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
```

- [ ] **Step 1.4: Add the cleanup pass to `repair.py`**

Open `docs/template-analysis/repair.py`. At the top, add:

```python
from cleanup_data2 import clean_data2
```

At the end of the edit pipeline inside `main`, just before `wb.save(dst)`, insert:

```python
    clean_data2(wb)  # Spec 3 pre-work: clear DATA2 cols D-L
```

- [ ] **Step 1.5: Regenerate WIP + golden**

```bash
cd docs/template-analysis
python repair.py ../template_wip_new_pre-repair.xlsx ../template_wip_new.xlsx
python build_golden.py ../template_wip_new.xlsx ../template_golden.xlsx
```

Expected: both exit 0.

- [ ] **Step 1.6: Re-pin `WIP_SHA256` in `conftest.py`**

```bash
cd docs
python -c "import hashlib; print(hashlib.sha256(open('template_wip_new.xlsx','rb').read()).hexdigest())"
```

Copy the 64-char output. In `docs/template-analysis/conftest.py`, replace the `WIP_SHA256` value.

- [ ] **Step 1.7: Run the full test suite**

```bash
cd docs && pytest template-analysis/ -v
```

Expected: 64 pre-existing tests + 2 new = 66 passed.

- [ ] **Step 1.8: Commit**

```bash
cd C:/_AAA/WS_HH/SD-HH-calculator-vc-v1
git add docs/template-analysis/cleanup_data2.py \
        docs/template-analysis/test_cleanup_data2.py \
        docs/template-analysis/repair.py \
        docs/template-analysis/conftest.py \
        docs/template_wip_new.xlsx \
        docs/template_golden.xlsx
git commit -m "docs(template): DATA2 cleanup — clear unused cols D-L

Cols D, E-H, J-L were unreferenced per the Spec 3 audit. A-C preserved
verbatim (178 live VLOOKUPs on SDC reach them). repair.py extended so
future repair runs apply the cleanup automatically. SHA pin updated.

Spec 3 pre-work."
```

---

## Task 2: Doc corrections (01-storm-drain-comps.md, 05-c-factor.md)

**Files:**
- Modify: `docs/template-analysis/01-storm-drain-comps.md`
- Modify: `docs/template-analysis/05-c-factor.md`

- [ ] **Step 2.1: Correct 01-storm-drain-comps.md**

Open the file. Search for the first occurrence of `"Manning's n"` associated with column R. Replace the column R description with:

> Column R (row 8 header "Angle Out of Pipe (Deg) - Whole #") — the deflection angle at which this pipe leaves the upstream structure, used by the controlling-angle junction-loss computation on columns AD/AE/AF.

Search for the column S description. Update to:

> Column S (row 8 header "Manning Coeff") — Manning's roughness coefficient n for the pipe. Default 0.013 (concrete pipe); user override permitted.

Add a one-line footnote at the bottom:

> Correction landed in Spec 3 pre-work: an earlier version of this doc listed column R as "Manning's n." Verified empirically against the row-8 headers in both `template_wip_new.xlsx` and `template_golden.xlsx`.

- [ ] **Step 2.2: Correct 05-c-factor.md**

Open the file. Find the section about column I. Replace any claim that I holds a Tc lookup with:

> Column I (row 5 header "Imp. Area (Ac)") — the impervious-area portion of the drainage area in acres. Consumed by the composite-C computation on column M.

Add a new sub-section covering column W:

> Column W (added by Spec 2 Edit 5; present in golden only, blank in legacy WIP) — Table 3-3 small-area Tc lookup. Formula branches on D (sheet-flow length category) and M (composite C). Advisory column — the calculator's reader MUST NOT read W as authoritative (per `calculator-import-contract.md` §4 note).

- [ ] **Step 2.3: Verify the Spec-1 U7 citation location**

```bash
grep -rn "Table 3-3" docs/superpowers/specs/ docs/template-analysis/
```

If any live spec-1 doc still claims U7 lives on column I, add a one-line correction note with a pointer to `05-c-factor.md`. If grep returns only self-references, no additional edit needed.

- [ ] **Step 2.4: Commit**

```bash
git add docs/template-analysis/01-storm-drain-comps.md \
        docs/template-analysis/05-c-factor.md
git commit -m "docs(template-analysis): correct col labels (Spec 3 pre-work)

01-storm-drain-comps.md: col R is 'Angle Out of Pipe (Deg)', not
Manning's n. Col S is Manning's n.

05-c-factor.md: col I is 'Imp. Area (Ac)'. Table 3-3 Tc lookup lives on
col W (golden only, added by Spec 2 Edit 5), not col I.

Both verified empirically against row-8 / row-5 headers in WIP and
golden templates."
```

---

## Pre-work ship gate

- [ ] Pytest green (66 passed).
- [ ] WIP + golden xlsx files committed with the SHA pin update.
- [ ] Doc corrections landed.

Hand off to [`phase-1-simple-reader.md`](phase-1-simple-reader.md).
