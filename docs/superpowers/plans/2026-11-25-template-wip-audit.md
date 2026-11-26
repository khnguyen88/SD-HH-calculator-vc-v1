# WIP Template Audit, Repair, and Rulebook Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce 16 per-tab analysis markdowns + a README under `docs/template-analysis/`, repair the five known issues in `docs/template_wip_new.xlsx` via a committed `repair.py`, and refresh `engineering-methodology.md`, `storm-drain-calculator-spec.md`, and `user-design-criteria.md` for the MDSHA/MCDOT vs PG County SWM Ch. 8 jurisdictional divergence and the `junctionAngleRule` toggle intent that Spec 3 will implement.

**Architecture:** Two Python/openpyxl scripts drive the mechanical work: `extract.py` (Pass A — automated JSON dump of every sheet's formulas and cross-sheet refs) and `repair.py` (R1–R5 applied deterministically to a backup copy of the WIP xlsx). Per-tab analysis docs are human-written against a fixed template, grounded in the Pass A JSON and the project rulebook. Rulebook updates are targeted Edit operations on existing files.

**Tech Stack:** Python 3.11 + `openpyxl`, `pytest` (available in the repo's venv), Microsoft Excel for manual verification. Governing docs: `docs/engineering-methodology.md`, `drainage-calculator/storm-drain-calculator-spec.md`, `docs/user-design-criteria.md`. Source xlsx: `docs/template_wip_new.xlsx`.

**No calculator code changes.** `drainage-calculator/storm-drain-design-calculator-dev.html` is untouched by this plan.

---

## Task 1: Create analysis directory and back up the WIP xlsx

**Files:**
- Create: `docs/template-analysis/` (directory)
- Create: `docs/template_wip_new_pre-repair.xlsx` (binary copy of the current WIP xlsx)

- [ ] **Step 1: Verify the WIP xlsx exists and confirm openpyxl availability**

Run:
```bash
python -c "import openpyxl; print('openpyxl', openpyxl.__version__)"
test -f docs/template_wip_new.xlsx && echo "wip ok"
```
Expected: version prints (any 3.x), "wip ok" prints.

- [ ] **Step 2: Create the analysis directory**

Run:
```bash
mkdir -p docs/template-analysis
```

- [ ] **Step 3: Copy the WIP xlsx to the pre-repair backup**

Run:
```bash
cp docs/template_wip_new.xlsx docs/template_wip_new_pre-repair.xlsx
```

- [ ] **Step 4: Verify backup is byte-identical to source**

Run:
```bash
python -c "
import hashlib
a=hashlib.sha256(open('docs/template_wip_new.xlsx','rb').read()).hexdigest()
b=hashlib.sha256(open('docs/template_wip_new_pre-repair.xlsx','rb').read()).hexdigest()
print('match' if a==b else 'MISMATCH', a[:12], b[:12])
"
```
Expected: `match <hash> <hash>` with identical prefixes.

- [ ] **Step 5: Commit the backup**

```bash
git add docs/template_wip_new_pre-repair.xlsx
git commit -m "docs(template): add pre-repair backup of template_wip_new.xlsx"
```

---

## Task 2: Build the Pass A extraction script

**Files:**
- Create: `docs/template-analysis/extract.py`
- Create: `docs/template-analysis/test_extract.py`

- [ ] **Step 1: Write the failing test**

Create `docs/template-analysis/test_extract.py`:
```python
"""Tests for extract.py — Pass A automated xlsx formula extraction."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "extract.py"
WIP = HERE.parent / "template_wip_new.xlsx"
OUT = HERE / "pass_a.json"


def run_extract():
    subprocess.check_call([sys.executable, str(SCRIPT), str(WIP), str(OUT)])
    return json.loads(OUT.read_text(encoding="utf-8"))


def test_outputs_valid_json_with_sixteen_sheets():
    data = run_extract()
    assert "sheets" in data, "top-level 'sheets' key missing"
    assert len(data["sheets"]) == 16, f"expected 16 sheets, got {len(data['sheets'])}"


def test_each_sheet_has_required_keys():
    data = run_extract()
    required = {"name", "max_row", "max_col", "formula_count",
                "ref_error_count", "tables", "cross_sheet_refs"}
    for sh in data["sheets"]:
        missing = required - set(sh.keys())
        assert not missing, f"sheet {sh.get('name')!r} missing keys {missing}"


def test_hgl_25year_ref_errors_reported():
    data = run_extract()
    hgl25 = next(s for s in data["sheets"] if s["name"] == "HGL(25YEAR)")
    assert hgl25["ref_error_count"] >= 600, (
        f"HGL(25YEAR) should report >=600 #REF! formulas, "
        f"got {hgl25['ref_error_count']}")


def test_broken_defined_names_reported():
    data = run_extract()
    assert "broken_defined_names" in data
    broken = data["broken_defined_names"]
    assert len(broken) >= 25, f"expected >=25 broken names, got {len(broken)}"
    names = {b["name"] for b in broken}
    assert "_DUR1" in names
    assert "_INT1" in names
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest docs/template-analysis/test_extract.py -v
```
Expected: FAIL — `extract.py` does not exist yet.

- [ ] **Step 3: Write the extract.py implementation**

Create `docs/template-analysis/extract.py`:
```python
"""Pass A: dump structured JSON describing every sheet in a template xlsx.

Usage: python extract.py <input.xlsx> <output.json>

Produces, for each sheet: name, dimensions, Table definitions, formula count,
#REF! error count, list of cross-sheet references (sheet names referenced in
any formula on this sheet), and the raw formula text for later review.
Workbook-level: list of defined names that resolve to #REF! or external links.
"""
import json
import re
import sys
from pathlib import Path

import openpyxl

SHEET_REF_RE = re.compile(r"'([^']+)'!|([A-Za-z_][A-Za-z0-9_ ]*)!")


def scan_sheet(ws, all_sheet_names):
    formulas = []
    ref_errors = 0
    cross_sheet = set()
    for row in ws.iter_rows():
        for cell in row:
            v = cell.value
            text = None
            if isinstance(v, str) and v.startswith("="):
                text = v
            elif hasattr(v, "text") and isinstance(getattr(v, "text", None), str):
                text = v.text  # ArrayFormula
            if text is None:
                continue
            formulas.append({"cell": cell.coordinate, "formula": text})
            if "#REF!" in text:
                ref_errors += 1
            for m in SHEET_REF_RE.finditer(text):
                name = (m.group(1) or m.group(2) or "").strip()
                if name and name in all_sheet_names and name != ws.title:
                    cross_sheet.add(name)
    tables = []
    if getattr(ws, "tables", None):
        for tname, tref in ws.tables.items():
            tables.append({"name": tname, "ref": tref})
    return {
        "name": ws.title,
        "max_row": ws.max_row,
        "max_col": ws.max_column,
        "formula_count": len(formulas),
        "ref_error_count": ref_errors,
        "tables": tables,
        "cross_sheet_refs": sorted(cross_sheet),
        "formulas": formulas,
    }


def scan_defined_names(wb):
    broken = []
    duplicates = {}
    for name in wb.defined_names:
        d = wb.defined_names[name]
        val = getattr(d, "value", None) or str(d)
        if "#REF!" in val:
            broken.append({"name": name, "value": val})
        duplicates.setdefault(val, []).append(name)
    dup_report = [
        {"range": rng, "names": names}
        for rng, names in duplicates.items()
        if len(names) > 1
    ]
    return broken, dup_report


def main(src, dst):
    wb = openpyxl.load_workbook(src, data_only=False)
    names = wb.sheetnames
    sheets = [scan_sheet(wb[n], set(names)) for n in names]
    broken, dups = scan_defined_names(wb)
    out = {
        "source": str(src),
        "sheet_count": len(names),
        "sheets": sheets,
        "broken_defined_names": broken,
        "duplicate_defined_names": dups,
    }
    Path(dst).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {dst}: {len(sheets)} sheets, "
          f"{sum(s['ref_error_count'] for s in sheets)} #REF! formulas, "
          f"{len(broken)} broken names, {len(dups)} duplicate-name ranges")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: extract.py <in.xlsx> <out.json>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
pytest docs/template-analysis/test_extract.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/template-analysis/extract.py docs/template-analysis/test_extract.py
git commit -m "docs(template): add Pass A openpyxl extraction script with tests"
```

---

## Task 3: Run Pass A and commit the JSON dump

**Files:**
- Create: `docs/template-analysis/pass_a.json`

- [ ] **Step 1: Run the extraction**

Run:
```bash
python docs/template-analysis/extract.py docs/template_wip_new.xlsx docs/template-analysis/pass_a.json
```
Expected: summary line like `wrote ...pass_a.json: 16 sheets, 704 #REF! formulas, 25 broken names, 1 duplicate-name ranges`.

- [ ] **Step 2: Sanity-check the JSON**

Run:
```bash
python -c "
import json
d=json.loads(open('docs/template-analysis/pass_a.json').read())
assert d['sheet_count']==16
print('sheets:', [s['name'] for s in d['sheets']])
print('total #REF!:', sum(s['ref_error_count'] for s in d['sheets']))
print('broken names:', len(d['broken_defined_names']))
"
```
Expected: lists all 16 sheet names, total #REF! around 704, broken names >= 25.

- [ ] **Step 3: Commit the JSON**

```bash
git add docs/template-analysis/pass_a.json
git commit -m "docs(template): capture Pass A extraction snapshot"
```

---

## Task 4: Write per-tab analysis — Working-engine sheets (4 docs)

Working engine = the four sheets where the real formulas live.

**Files:**
- Create: `docs/template-analysis/01-storm-drain-comps.md`
- Create: `docs/template-analysis/02-hgl.md`
- Create: `docs/template-analysis/03-hgl-25year.md`
- Create: `docs/template-analysis/04-inlet-spacing.md`

Each doc uses the fixed template below.

**Fixed template for every per-tab doc:**

````markdown
# <SHEET NAME>

## Purpose
One sentence — why this sheet exists.

## Headers & ranges
The occupied range (e.g., A10:AR98). Any Table objects (name + ref). Header rows.

## Inputs
User-typed cells; dropdown sources; workbook-scoped named ranges read on this sheet.

## Formulas
Grouped by column or by role. Each entry: `<cell> <column header> → <formula>` with the rulebook citation for the governing equation (file + section).

## Outputs
Which other sheets read from this one, and by which lookup key (From/To pipe pair, Inlet ID, etc.).

## Dependencies
Which sheets this one reads, and by which key.

## Issues found
Enumerated — severity (Critical / High / Medium / Low / Watch), cell range, one-line description. Pull from `pass_a.json` plus manual inspection.

## Fix plan
Per-issue, point to the corresponding R-ID in `docs/superpowers/specs/2026-11-25-template-wip-audit-design.md` Section 5.2. If "none", say so.
````

- [ ] **Step 1: Write `01-storm-drain-comps.md`**

The hub sheet — Table4 at A10:AR98. Must enumerate every column in row 8 by header text and link each formula column to its rulebook equation. Reference `pass_a.json` for the raw formula list. Required citations:

- Column C / D / E / F / G / H (DA, C, Tc, A*C, intensity, Q increm) → `engineering-methodology.md` §1 Rational Method
- Column I / J / K / L / M (A total, A*C total, pipe Tc, intensity, Q total) → §1 Rational + §2 TR-55 time-in-pipe accumulation
- Column T (Full Flow Capacity) → §3 Manning full-flow
- Column U (Q/A → V), V (Vf full), W (Flow Velocity), X (Time in Pipe) → §3 and §4
- Column Y (Friction Slope) → §4 Friction Loss
- Column Z (Actual Slope) → `user-design-criteria.md` "Pipe slope (longitudinal)"
- Columns AA–AF (Str Type, Top Elev, Str No., Control Angle, Kb, Str Loss) → §5 Structure Loss — controlling angle; cite MDSHA Ch. 5 and MCDOT §4.3.2.3
- Columns AM–AR (Hx chain — Downstream Str Type, K, Diameter, V1/3, Hx, Max Hx) → §5 and §6 HGL propagation
- Columns AT–BD (N, S, Q, D, AR2/3/Do8/3, Y/D0, Y, A/DO2, A) → normal-depth/partial-flow computation using DATA2 lookup

Issues section: none within this sheet (it is the source of truth). Fix plan: none (no R-ID).

- [ ] **Step 2: Write `02-hgl.md`** (10-year HGL)

Range: A5:O91 (header rows 5–6, data rows 7–91). Uses `XLOOKUP(1, (A=$A7)*(B=$B7), …)` array-formula pattern keyed on (From, To) pipe-pair.

Columns to cover (map each to rulebook):
- A (From), B (To): direct lookup to STORM DRAIN COMPS A10/B10
- C (U/S Invert) ← STORM DRAIN COMPS $P:$P
- D (U/S Crown) = C + (STORM DRAIN COMPS N/12)
- E (D/S Invert) ← $Q:$Q
- F (D/S Crown) = E + N/12
- G (HGL at D/S Invert) = IFERROR(IF(A="","", MAX(F, Q, MAX(IF($A$7:$A$91=$B7, $M$7:$M$91)))), "") — HGL propagation per `engineering-methodology.md` §6, with crown floor (legacy both-end method) via F
- H (Pipe Length) ← $O:$O
- I (Friction Slope %) ← $Y:$Y — §4
- J (Pipe Loss) = H × I — §4 Hf = Sf × L
- K (HGL at High Invert) = MAX(D, J + G) — §6 upstream HGL = downstream HGL + Hf, floored at upstream crown
- L (Structure Loss) ← $AF:$AF — §5
- M (HGL in From Str) = K + L — §6
- N (Top/Opening Elev) ← $AB:$AB
- O (Freeboard) = N − K — user-design-criteria.md HGL ≤ rim − 1 ft check

Issues: none (clean sheet). Fix plan: none.

- [ ] **Step 3: Write `03-hgl-25year.md`**

Current state: broken. Every cell in rows 7–91 uses `OFFSET('STORM DRAIN COMPS'!#REF!, …)` — 680 `#REF!` formulas reported by Pass A. Same column layout as `02-hgl.md` (headers rows 5–6 match 10-year sheet), but the sheet is non-functional.

Issues: Critical — all 680 formulas unusable. Fix plan: R1 (see Task 11). The repair will mirror the 10-year XLOOKUP pattern. The source template has no 25-year friction-slope column on STORM DRAIN COMPS (column Y holds the 10-year Sf; column AI is a *normal depth* for the 25-year storm, not a friction slope). Document this gap explicitly: after R1, the sheet will compute a *10-year-equivalent* HGL in the 25-year slot and a header note on the repaired sheet will instruct the engineer to either (a) accept 10-year Sf as a conservative upper bound for the 25-year check, or (b) manually override column I with a 25-year Sf per row.

- [ ] **Step 4: Write `04-inlet-spacing.md`**

Range: A8:AR109. Not a Table — plain cells. Two staged sections (EXISTING CONDITIONS at row 10, PROPOSED CONDITIONS further down — confirm from the sheet). Uses `VLOOKUP` against `C_FACTOR` and `DATA`, plus `SUMIF` for carryover flow.

Columns to cover:
- A (Inlet Number), B (Catch Basin Type), C (Inlet Length): user-typed
- D (Area acres) ← VLOOKUP into C_FACTOR
- E (C runoff coef) ← VLOOKUP into C_FACTOR
- F (CA incremental) = D × E — §1 Rational
- G (Bypass CA) = SUMIF — carryover flow from upstream inlet
- H (Total CA) = F + G
- I (Tc minutes) ← VLOOKUP into C_FACTOR
- J (I10 intensity in/hr) ← conditional on jurisdiction, pulls from DATA sheet IDF block
- K (Q10 cfs) = H × J — §1
- L–AJ: spread/capture hydraulics per HEC-22 Chapter 4 (inlet-on-grade + sump), per the spec's `spec` section on inlet spacing (Spec Phase B)

Issues: **High** — column AK rows 11–96 contain 24 formulas of form `=IF(EXACT(#REF!, $S11), $R11, 0)`. The `#REF!` argument to `EXACT` indicates a lost reference to what was likely a header or configuration cell holding an inlet-type tag. Fix plan: R2. Before R2 runs, determine AK's intent by:
  1. Inspecting columns AJ and AL in `pass_a.json` for related patterns.
  2. Searching for any downstream sheet that reads column AK (if nothing reads it, R2 deletes the column; if something reads it, R2 reconstructs it against the recovered target cell).

Document the outcome inline in this file before running `repair.py`.

- [ ] **Step 5: Commit all four**

```bash
git add docs/template-analysis/01-storm-drain-comps.md \
        docs/template-analysis/02-hgl.md \
        docs/template-analysis/03-hgl-25year.md \
        docs/template-analysis/04-inlet-spacing.md
git commit -m "docs(template): per-tab analysis - working-engine sheets"
```

---

## Task 5: Write per-tab analysis — Data-source sheets (6 docs)

Data sources = lookup tables and static reference. Fewer formulas; focus on *what feeds what*.

**Files:**
- Create: `docs/template-analysis/05-c-factor.md`
- Create: `docs/template-analysis/06-data.md`
- Create: `docs/template-analysis/07-data2.md`
- Create: `docs/template-analysis/14-pipe-schedule.md`
- Create: `docs/template-analysis/15-structure-schedule.md`
- Create: `docs/template-analysis/16-equations-instructions.md`

Each uses the same fixed template from Task 4.

- [ ] **Step 1: Write `05-c-factor.md`** — Runoff-coefficient lookup table used by INLET SPACING columns D/E and by STORM DRAIN COMPS column C/D via `VLOOKUP(A_inlet, C_FACTOR!$B$6:$V$88, …)`. No formulas on this sheet; list column schema (Inlet ID, Area, C, Tc) and the exact range the lookups anchor on. Issues: none. Fix plan: none.

- [ ] **Step 2: Write `06-data.md`** — IDF curve tables for MoCo, PG, DC (rows 6–63) and the dropdown source cells (jurisdiction, structure type, inlet type, at-grade/sump). No formulas. List the named ranges that resolve here (`Select_County`, `SelectCounty`, `StormFrequency`, `StormFrequencyDC`, `StrType`, `SELECT_INLET_TYPE`, `SELECT_AT_GRADE_OR_IN_SUMP`). Issues: **Low** — `Select_County` and `SelectCounty` are duplicate names for the same range `DATA!$C$1:$C$4`. Fix plan: R4 (Task 13).

- [ ] **Step 3: Write `07-data2.md`** — Partial-flow depth lookup table (`A2:D101`). Used by STORM DRAIN COMPS columns AZ, BA, BB, BC via `VLOOKUP(AY10, DATA2!$A$2:$D$101, n)`. Document the four-column schema. Issues: none. Fix plan: none.

- [ ] **Step 4: Write `14-pipe-schedule.md`** — Hand-maintained pipe inventory. Primarily tabular reference listed on the drawings. No downstream formula references. Issues: none. Fix plan: none.

- [ ] **Step 5: Write `15-structure-schedule.md`** — Hand-maintained structure inventory (type, standard number, station, invert elevations per MCDOT §4.2.4). No downstream formula references. Issues: none. Fix plan: none.

- [ ] **Step 6: Write `16-equations-instructions.md`** — Reference sheet carrying governing equations and workbook usage notes. No computed cells. Issues: **Watch** — current text does not warn users that From/To columns must describe an acyclic pipe network (a loop in the data breaks the cross-row MAX/XLOOKUP chains because iterative calc is off). Fix plan: R5 (Task 14) adds that note.

- [ ] **Step 7: Commit all six**

```bash
git add docs/template-analysis/05-c-factor.md \
        docs/template-analysis/06-data.md \
        docs/template-analysis/07-data2.md \
        docs/template-analysis/14-pipe-schedule.md \
        docs/template-analysis/15-structure-schedule.md \
        docs/template-analysis/16-equations-instructions.md
git commit -m "docs(template): per-tab analysis - data-source sheets"
```

---

## Task 6: Write per-tab analysis — Printable-report sheets (6 docs)

Printable reports = views that pull from STORM DRAIN COMPS and HGL for agency submittal (MCDOT and MDSHA SHA form layouts).

**Files:**
- Create: `docs/template-analysis/08-mcdot-pipe-design.md`
- Create: `docs/template-analysis/09-mcdot-inlet-design.md`
- Create: `docs/template-analysis/10-mcdot-hgl-design.md`
- Create: `docs/template-analysis/11-sha-sd-420.md`
- Create: `docs/template-analysis/12-sha-2yr-spread.md`
- Create: `docs/template-analysis/13-sha-25yr-hgl.md`

For each, pull the `cross_sheet_refs` list from `pass_a.json` to verify what the sheet reads. All six sheets follow the same `INDEX/MATCH(from_column, STORM_DRAIN_COMPS_A, 0)` pattern — pipe row = keyed by From Str. Document the exact column-to-column mapping.

- [ ] **Step 1: Write `08-mcdot-pipe-design.md`** — MCDOT pipe computations submittal form. Range A3:O32 (Table22). Maps STORM DRAIN COMPS columns B/C/I/D/F/J/E/L/M/N/Y/W/O/K into the local A–O layout. Rulebook: §1 Rational, §3 Manning, §4 friction loss. Issues: none. Fix plan: none.

- [ ] **Step 2: Write `09-mcdot-inlet-design.md`** — MCDOT inlet computations submittal form (A3:U26, Table2). Pulls from STORM DRAIN COMPS and from INLET SPACING. Issues: none. Fix plan: none.

- [ ] **Step 3: Write `10-mcdot-hgl-design.md`** — MCDOT HGL submittal form (paired rows per pipe: row 3 for pipe header, row 4 for structure-side data). Columns B–M pull from STORM DRAIN COMPS; columns P pull from HGL (`$K` and `$G`). Rulebook: §4 friction loss, §5 structure loss, §6 HGL. Issues: none. Fix plan: none.

- [ ] **Step 4: Write `11-sha-sd-420.md`** — MDSHA SHA SD-61.1-420 pipe design form. Same pattern as MCDOT PIPE COMPS-DESIGN with MDSHA-specific layout. Issues: none. Fix plan: none.

- [ ] **Step 5: Write `12-sha-2yr-spread.md`** — MDSHA SHA 61.1-491 2-year inlet spread form. Issues: none. Fix plan: none.

- [ ] **Step 6: Write `13-sha-25yr-hgl.md`** — MDSHA SHA 61.1-493 25-year HGL form. Pulls from the HGL(25YEAR) sheet. Issues: **Downstream-of-R1** — currently non-functional because its input sheet (HGL(25YEAR)) is broken. After R1 lands, this sheet should display 10-year-equivalent HGL in the 25-year slot until the engineer overrides column I on HGL(25YEAR). Document this dependency chain. Fix plan: none here (fix is in R1).

- [ ] **Step 7: Commit all six**

```bash
git add docs/template-analysis/08-mcdot-pipe-design.md \
        docs/template-analysis/09-mcdot-inlet-design.md \
        docs/template-analysis/10-mcdot-hgl-design.md \
        docs/template-analysis/11-sha-sd-420.md \
        docs/template-analysis/12-sha-2yr-spread.md \
        docs/template-analysis/13-sha-25yr-hgl.md
git commit -m "docs(template): per-tab analysis - printable-report sheets"
```

---

## Task 7: Write the README with dependency diagram

**Files:**
- Create: `docs/template-analysis/README.md`

- [ ] **Step 1: Write the README**

Create `docs/template-analysis/README.md` with the content shown below (uses a fenced code block for the dep diagram so markdown renderers display it as monospace):

````markdown
# WIP Template Analysis

Per-tab analysis of `docs/template_wip_new.xlsx` — the new "legacy" reference template for PG / MoCo / DC storm-drain design. Produced as Spec 1 of the three-part series (audit → golden template → calculator compatibility). See `docs/superpowers/specs/2026-11-25-template-wip-audit-design.md` for the design.

## Dependency diagram

```
                   DATA (IDF curves, dropdowns)
                      |                  |
                      v                  v
                INLET SPACING     STORM DRAIN COMPS  <----- C_FACTOR
                                  (Table4 A10:AR98)         (runoff coef)
                                        |
                      +-----------------+------------------+
                      |                 |                  |
                      v                 v                  v
                    HGL (10yr)   HGL(25YEAR)       MCDOT PIPE COMPS-DESIGN
                    (XLOOKUP)    (XLOOKUP)         MCDOT INLET COMPS-DESIGN
                                                   MCDOT HGL-DESIGN
                                                   SHA SD-61.1-420-DESIGN
                                                   SHA (2-YR)SPREAD 61.1-491
                                                   SHA (25-YR)HGL 61.1-493
                                                          |
                                                          v
                                                   DATA2 (Y/D lookup for
                                                   normal-depth)

                    PIPE SCHEDULE       (hand-maintained, no formulas)
                    STRUCTURE SCHEDULE  (hand-maintained, no formulas)
                    EQUATIONS + INSTRUCTIONS (reference text only)
```

STORM DRAIN COMPS is the hub. Every HGL sheet and every printable report derives from it.

## Sheet roles

| Role | Sheets |
|---|---|
| Working engine | STORM DRAIN COMPS, HGL, HGL(25YEAR), INLET SPACING |
| Data sources | C_FACTOR, DATA, DATA2, PIPE SCHEDULE, STRUCTURE SCHEDULE, EQUATIONS + INSTRUCTIONS |
| Printable reports | MCDOT PIPE COMPS-DESIGN, MCDOT INLET COMPS-DESIGN, MCDOT HGL-DESIGN, SHA SD-61.1-420-DESIGN, SHA (2-YR)SPREAD 61.1-491, SHA (25-YR)HGL 61.1-493 |

## Per-tab docs

- [01 STORM DRAIN COMPS](01-storm-drain-comps.md)
- [02 HGL](02-hgl.md)
- [03 HGL(25YEAR)](03-hgl-25year.md)
- [04 INLET SPACING](04-inlet-spacing.md)
- [05 C_FACTOR](05-c-factor.md)
- [06 DATA](06-data.md)
- [07 DATA2](07-data2.md)
- [08 MCDOT PIPE COMPS-DESIGN](08-mcdot-pipe-design.md)
- [09 MCDOT INLET COMPS-DESIGN](09-mcdot-inlet-design.md)
- [10 MCDOT HGL-DESIGN](10-mcdot-hgl-design.md)
- [11 SHA SD-61.1-420-DESIGN](11-sha-sd-420.md)
- [12 SHA (2-YR)SPREAD 61.1-491](12-sha-2yr-spread.md)
- [13 SHA (25-YR)HGL 61.1-493](13-sha-25yr-hgl.md)
- [14 PIPE SCHEDULE](14-pipe-schedule.md)
- [15 STRUCTURE SCHEDULE](15-structure-schedule.md)
- [16 EQUATIONS + INSTRUCTIONS](16-equations-instructions.md)

## Scripts

- `extract.py` — Pass A automated JSON dump (committed output: `pass_a.json`).
- `repair.py` — applies R1–R5 from the Spec-1 design doc; produces the repaired `../template_wip_new.xlsx` from `../template_wip_new_pre-repair.xlsx`.
- `test_extract.py`, `test_repair.py` — pytest suites.
````

- [ ] **Step 2: Commit**

```bash
git add docs/template-analysis/README.md
git commit -m "docs(template): add analysis README with dep diagram and index"
```

---

## Task 8: Build the repair.py skeleton + the R1/R2/R3/R4/R5 bodies

**Files:**
- Create: `docs/template-analysis/repair.py`
- Create: `docs/template-analysis/test_repair.py`

The repair script reads from the backup (pre-repair) xlsx and writes to the live xlsx. This way re-running it reproduces the repaired file from a known-good starting point. All five repairs are implemented in this one task; subsequent tasks only add tests that verify each repair's effect.

- [ ] **Step 1: Write the failing skeleton test**

Create `docs/template-analysis/test_repair.py` with the content below:

```python
# Tests for repair.py - applies R1-R5 to template_wip_new.xlsx.
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

HERE = Path(__file__).parent
SCRIPT = HERE / "repair.py"
WIP = HERE.parent / "template_wip_new.xlsx"
BACKUP = HERE.parent / "template_wip_new_pre-repair.xlsx"


@pytest.fixture(scope="module")
def repaired_wb():
    assert BACKUP.exists(), "pre-repair backup missing - Task 1 not run"
    subprocess.check_call([sys.executable, str(SCRIPT), str(BACKUP), str(WIP)])
    return openpyxl.load_workbook(WIP, data_only=False)


def test_script_runs_and_produces_file(repaired_wb):
    assert WIP.exists()
    assert len(repaired_wb.sheetnames) == 16
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest docs/template-analysis/test_repair.py::test_script_runs_and_produces_file -v
```
Expected: FAIL — `repair.py` does not exist.

- [ ] **Step 3: Write the full repair.py implementation**

Create `docs/template-analysis/repair.py` with the content below. All five repairs are implemented at once because the logic for each is short and they must run in one pass to guarantee a consistent output file:

```python
# Apply R1-R5 repairs from the Spec-1 design to the WIP xlsx.
#
# Usage: python repair.py <backup.xlsx> <output.xlsx>
#
# Reads <backup.xlsx> (the pre-repair snapshot), applies every repair
# deterministically, writes <output.xlsx>. Re-running on the same backup
# reproduces the output.
#
# Design reference: docs/superpowers/specs/2026-11-25-template-wip-audit-design.md
# Section 5.2.
import sys

import openpyxl


ORPHAN_NAMES = (
    ["\\0", "\\c", "\\e", "\\p", "\\r"]
    + [f"_DUR{i}" for i in range(1, 19)]
    + ["_INT1", "_INT2"]
)
DUPLICATE_NAME_TO_REMOVE = "SelectCounty"  # keep Select_County


def remove_defined_names(wb, names):
    # R3 + R4: remove orphan #REF! names and the SelectCounty duplicate.
    for name in list(wb.defined_names):
        if name in names:
            del wb.defined_names[name]


def rebuild_hgl_25year(wb):
    # R1: rebuild ONLY the broken OFFSET-pattern columns on HGL(25YEAR):
    # A, B, C, D, E, F, H, L. Every other column on the sheet is intact
    # and must be left untouched:
    #   G, I, J, K, M = HGL chain (G propagates MAX; I computes 25-year
    #     friction slope from column U (25-year Q) and V (Manning n); J =
    #     Hf = H*I; K = upstream HGL floored at U/S crown; M = HGL in
    #     From Str = K + Hb).
    #   O = 10-year tailwater pull from HGL!Q.
    #   Q, R, S, T, U, V = 25-year auxiliary columns (pipe diameter from
    #     SDC N, A*C total from SDC J, pipe Tc from SDC K, 25-year
    #     intensity from DATA, 25-year Q = T*R, Manning n from SDC S).
    # The sheet already implements correct 25-year flow and friction
    # slope on-sheet, so R1 does not need to substitute a source-sheet
    # Y column - the existing I-column formula is correct as-is.
    ws = wb["HGL(25YEAR)"]
    _write_hgl25_broken_columns(ws, start=7, end=91)


def fix_inlet_spacing_ak(wb):
    # R2: resolve the AK #REF! formulas. Default: clear AK rows 11-96.
    # If the per-tab analysis in docs/template-analysis/04-inlet-spacing.md
    # recorded that AK is referenced by a downstream sheet, override this
    # function at that point and rebuild the EXACT(...) argument against
    # the recovered target cell.
    ws = wb["INLET SPACING"]
    for row in range(11, 97):
        cell = ws.cell(row=row, column=37)  # AK = column 37
        if isinstance(cell.value, str) and "#REF!" in cell.value:
            cell.value = None


def update_equations_instructions(wb):
    # R5: append a note explaining the acyclic-pipe-network requirement.
    ws = wb["EQUATIONS + INSTRUCTIONS"]
    note_row = ws.max_row + 2
    ws[f"A{note_row}"] = (
        "NOTE: From/To columns must describe an acyclic pipe network. "
        "Iterative calculation is intentionally OFF - a loop in the data "
        "will produce #VALUE!, not an iteratively settled answer. Check "
        "your From/To entries if you see unexpected errors on HGL or "
        "structure-loss columns."
    )


def _write_hgl25_broken_columns(ws, start, end):
    # Overwrites only the 8 broken columns on HGL(25YEAR) with the
    # XLOOKUP-pattern formulas used by the clean 10-year HGL sheet.
    # Broken columns: A, B (From/To), C (U/S invert), D (U/S crown), E
    # (D/S invert), F (D/S crown), H (pipe length), L (structure loss).
    # Every other column on the sheet is left untouched - the intact
    # 25-year formulas on G, I, J, K, M, O, Q-V remain in place.
    sdc = "'STORM DRAIN COMPS'"
    q = '""'  # empty-string literal inside a formula
    for r in range(start, end + 1):
        src = 10 + (r - start)  # STORM DRAIN COMPS data starts at row 10
        ws[f"A{r}"] = f"=IF({sdc}!A{src}={q},{q},{sdc}!A{src})"
        ws[f"B{r}"] = f"=IF({sdc}!B{src}={q},{q},{sdc}!B{src})"
        ws[f"C{r}"] = (
            f"=IF(OR(A{r}={q},B{r}={q}),{q},"
            f"XLOOKUP(1,({sdc}!$A:$A=$A{r})*({sdc}!$B:$B=$B{r}),{sdc}!$P:$P))"
        )
        ws[f"D{r}"] = f"=IF(C{r}={q},{q},({sdc}!N{src}/12)+C{r})"
        ws[f"E{r}"] = (
            f"=IF(OR(A{r}={q},B{r}={q}),{q},"
            f"XLOOKUP(1,({sdc}!$A:$A=$A{r})*({sdc}!$B:$B=$B{r}),{sdc}!$Q:$Q))"
        )
        ws[f"F{r}"] = f"=IF(E{r}={q},{q},{sdc}!N{src}/12+E{r})"
        ws[f"H{r}"] = (
            f"=IF(OR(A{r}={q},B{r}={q}),{q},"
            f"XLOOKUP(1,({sdc}!$A:$A=$A{r})*({sdc}!$B:$B=$B{r}),{sdc}!$O:$O))"
        )
        ws[f"L{r}"] = (
            f"=IF(OR(A{r}={q},B{r}={q}),{q},"
            f"XLOOKUP(1,({sdc}!$A:$A=$A{r})*({sdc}!$B:$B=$B{r}),{sdc}!$AF:$AF))"
        )


def main(src, dst):
    wb = openpyxl.load_workbook(src, data_only=False)
    rebuild_hgl_25year(wb)
    fix_inlet_spacing_ak(wb)
    remove_defined_names(wb, set(ORPHAN_NAMES) | {DUPLICATE_NAME_TO_REMOVE})
    update_equations_instructions(wb)
    wb.save(dst)
    print(f"wrote {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: repair.py <backup.xlsx> <output.xlsx>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
```

- [ ] **Step 4: Run the skeleton test to verify it passes**

Run:
```bash
pytest docs/template-analysis/test_repair.py::test_script_runs_and_produces_file -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/template-analysis/repair.py docs/template-analysis/test_repair.py
git commit -m "docs(template): add repair.py with R1-R5 implementations"
```

---

## Task 9: Add tests for R3 orphan defined-name removal

**Files:**
- Modify: `docs/template-analysis/test_repair.py`

- [ ] **Step 1: Add the failing test**

Append to `docs/template-analysis/test_repair.py`:
```python
def test_r3_orphan_names_removed(repaired_wb):
    names = list(repaired_wb.defined_names)
    for orphan in ("\\0", "\\c", "\\e", "\\p", "\\r"):
        assert orphan not in names, f"orphan name {orphan!r} still present"
    for i in range(1, 19):
        assert f"_DUR{i}" not in names, f"_DUR{i} still present"
    assert "_INT1" not in names
    assert "_INT2" not in names


def test_r3_no_broken_names_remain(repaired_wb):
    for name in repaired_wb.defined_names:
        d = repaired_wb.defined_names[name]
        val = getattr(d, "value", None) or str(d)
        assert "#REF!" not in val, f"name {name!r} still resolves to #REF!: {val!r}"
```

- [ ] **Step 2: Run tests**

Run:
```bash
pytest docs/template-analysis/test_repair.py -v
```
Expected: both new tests PASS (repair.py already implements R3).

- [ ] **Step 3: Commit**

```bash
git add docs/template-analysis/test_repair.py
git commit -m "docs(template): test R3 orphan defined-name removal"
```

---

## Task 10: Add tests for R4 duplicate defined-name removal

**Files:**
- Modify: `docs/template-analysis/test_repair.py`

- [ ] **Step 1: Add the failing test**

Append to `docs/template-analysis/test_repair.py`:
```python
def test_r4_selectcounty_duplicate_removed(repaired_wb):
    names = list(repaired_wb.defined_names)
    assert "SelectCounty" not in names, "SelectCounty duplicate still present"
    assert "Select_County" in names, "Select_County (canonical) was removed by mistake"


def test_r4_no_duplicate_range_names(repaired_wb):
    seen = {}
    for name in repaired_wb.defined_names:
        d = repaired_wb.defined_names[name]
        val = getattr(d, "value", None) or str(d)
        seen.setdefault(val, []).append(name)
    dupes = {rng: names for rng, names in seen.items() if len(names) > 1}
    assert not dupes, f"duplicate-name ranges remain: {dupes}"
```

- [ ] **Step 2: Run tests**

Run:
```bash
pytest docs/template-analysis/test_repair.py -v
```
Expected: both new tests PASS.

- [ ] **Step 3: Commit**

```bash
git add docs/template-analysis/test_repair.py
git commit -m "docs(template): test R4 duplicate defined-name removal"
```

---

## Task 11: Add tests for R1 HGL(25YEAR) rebuild

**Files:**
- Modify: `docs/template-analysis/test_repair.py`

- [ ] **Step 1: Add the failing tests**

Append to `docs/template-analysis/test_repair.py`:
```python
def test_r1_no_ref_errors_on_hgl_25year(repaired_wb):
    ws = repaired_wb["HGL(25YEAR)"]
    for row in ws.iter_rows():
        for cell in row:
            v = cell.value
            text = v if isinstance(v, str) else getattr(v, "text", None)
            if isinstance(text, str):
                assert "#REF!" not in text, (
                    f"HGL(25YEAR)!{cell.coordinate} still contains #REF!: {text!r}"
                )


def test_r1_hgl_25year_broken_columns_use_xlookup(repaired_wb):
    # Every previously broken column is now an XLOOKUP against SDC.
    ws = repaired_wb["HGL(25YEAR)"]
    c7 = ws["C7"].value
    assert isinstance(c7, str) and "XLOOKUP" in c7 and "'STORM DRAIN COMPS'!$P:$P" in c7, (
        f"C7 should XLOOKUP U/S invert from SDC $P, got {c7!r}")
    e7 = ws["E7"].value
    assert isinstance(e7, str) and "XLOOKUP" in e7 and "'STORM DRAIN COMPS'!$Q:$Q" in e7, (
        f"E7 should XLOOKUP D/S invert from SDC $Q, got {e7!r}")
    h7 = ws["H7"].value
    assert isinstance(h7, str) and "XLOOKUP" in h7 and "'STORM DRAIN COMPS'!$O:$O" in h7, (
        f"H7 should XLOOKUP pipe length from SDC $O, got {h7!r}")
    l7 = ws["L7"].value
    assert isinstance(l7, str) and "XLOOKUP" in l7 and "'STORM DRAIN COMPS'!$AF:$AF" in l7, (
        f"L7 should XLOOKUP structure loss from SDC $AF, got {l7!r}")


def test_r1_hgl_25year_intact_columns_preserved(repaired_wb):
    # The on-sheet 25-year friction-slope and HGL chain formulas must be
    # left alone. The spec requires preserving the intact 25-year Sf
    # formula in column I (which computes Sf from column U = 25-year Q and
    # column V = Manning n), along with G/J/K/M (HGL chain) and Q-V
    # (25-year auxiliary data).
    ws = repaired_wb["HGL(25YEAR)"]
    i7 = ws["I7"].value
    assert isinstance(i7, str), f"I7 must still be a formula, got {type(i7).__name__}"
    # The intact I7 formula recomputes Sf using column U (25-year Q) and
    # column V (Manning n); it must NOT have been replaced by an SDC Y lookup.
    assert "U7" in i7 and "V7" in i7, (
        f"I7 should recompute 25-year Sf from U7 (25-yr Q) and V7 (Manning n), "
        f"got {i7!r}")
    assert "'STORM DRAIN COMPS'!$Y:$Y" not in i7, (
        f"I7 must NOT have been replaced by an SDC $Y (10-year) lookup; "
        f"got {i7!r}")
    # Spot-check the 25-year auxiliary columns Q-V still compute on-sheet.
    for col in ("Q7", "R7", "S7", "T7", "U7", "V7"):
        v = ws[col].value
        assert isinstance(v, str) and v.startswith("="), (
            f"{col} should still carry a formula, got {v!r}")


def test_r1_no_header_override_note(repaired_wb):
    # The earlier-approach override note is no longer appropriate because
    # the intact I-column computes a true 25-year Sf; verify nothing added
    # an obsolete "defaults to 10-year Sf" note on A4.
    ws = repaired_wb["HGL(25YEAR)"]
    a4 = (ws["A4"].value or "")
    assert "10-year Sf" not in a4, (
        f"A4 should not carry a 10-year-default note; got {a4!r}")
```

- [ ] **Step 2: Run tests**

Run:
```bash
pytest docs/template-analysis/test_repair.py -v
```
Expected: all four new R1 tests PASS. Pay special attention to `test_r1_hgl_25year_intact_columns_preserved` — if it fails, `rebuild_hgl_25year` is incorrectly overwriting intact cells.

- [ ] **Step 3: Commit**

```bash
git add docs/template-analysis/test_repair.py
git commit -m "docs(template): test R1 HGL(25YEAR) XLOOKUP rebuild"
```

---

## Task 12: Add tests for R2 INLET SPACING AK column

**Files:**
- Modify: `docs/template-analysis/test_repair.py`

- [ ] **Step 1: Add the failing tests**

Append to `docs/template-analysis/test_repair.py`:
```python
def test_r2_inlet_spacing_ak_has_no_ref_errors(repaired_wb):
    ws = repaired_wb["INLET SPACING"]
    for row in range(11, 97):
        cell = ws.cell(row=row, column=37)  # AK
        v = cell.value
        text = v if isinstance(v, str) else getattr(v, "text", None)
        if isinstance(text, str):
            assert "#REF!" not in text, (
                f"INLET SPACING!AK{row} still contains #REF!: {text!r}"
            )
```

- [ ] **Step 2: Run tests**

Run:
```bash
pytest docs/template-analysis/test_repair.py -v
```
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add docs/template-analysis/test_repair.py
git commit -m "docs(template): test R2 INLET SPACING AK column cleared of #REF!"
```

---

## Task 13: Add tests for R5 EQUATIONS + INSTRUCTIONS note and the whole-workbook invariants

**Files:**
- Modify: `docs/template-analysis/test_repair.py`

- [ ] **Step 1: Add the failing tests**

Append to `docs/template-analysis/test_repair.py`:
```python
def test_r5_acyclic_note_present(repaired_wb):
    ws = repaired_wb["EQUATIONS + INSTRUCTIONS"]
    found = False
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "acyclic pipe network" in cell.value:
                found = True
                break
        if found:
            break
    assert found, "R5 acyclic-network note not found on EQUATIONS + INSTRUCTIONS"


def test_workbook_has_no_ref_errors_anywhere(repaired_wb):
    hits = []
    for ws in repaired_wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                text = v if isinstance(v, str) else getattr(v, "text", None)
                if isinstance(text, str) and "#REF!" in text:
                    hits.append(f"{ws.title}!{cell.coordinate}")
    assert not hits, f"#REF! still present at: {hits[:10]}..."


def test_workbook_has_no_external_links(repaired_wb):
    import re
    ext_pat = re.compile(r"'?\[[^\]]+\.xls[xmb]?\]")
    hits = []
    for ws in repaired_wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                text = v if isinstance(v, str) else getattr(v, "text", None)
                if isinstance(text, str) and ext_pat.search(text):
                    hits.append(f"{ws.title}!{cell.coordinate}")
    assert not hits, f"external workbook links remain: {hits[:10]}..."
```

- [ ] **Step 2: Run tests**

Run:
```bash
pytest docs/template-analysis/test_repair.py -v
```
Expected: all three new tests PASS. (This is the final automated verification pass.)

- [ ] **Step 3: Commit**

```bash
git add docs/template-analysis/test_repair.py
git commit -m "docs(template): test R5 note and whole-workbook invariants"
```

---

## Task 14: Commit the repaired xlsx and verify it in Excel

**Files:**
- Modify: `docs/template_wip_new.xlsx` (this is the output of the repair script; the Task 8+ test run has already overwritten it)

- [ ] **Step 1: Confirm the repaired file is current**

Run:
```bash
python docs/template-analysis/repair.py docs/template_wip_new_pre-repair.xlsx docs/template_wip_new.xlsx
```
Expected: `wrote docs/template_wip_new.xlsx`.

- [ ] **Step 2: Re-run the full test suite as a final sanity check**

Run:
```bash
pytest docs/template-analysis/ -v
```
Expected: every test in `test_extract.py` and `test_repair.py` PASSES.

- [ ] **Step 3: Open the repaired xlsx in Excel for Microsoft 365 and verify manually**

Manual verification checklist — open `docs/template_wip_new.xlsx` in Excel:
1. File opens without the "we found a problem" repair dialog. If Excel offers to repair, note the message and do NOT dismiss it — stop and investigate.
2. `HGL(25YEAR)` has clean columns A–O with no `#REF!` values; row 4 shows the override note starting "25 YEAR STORM - column I defaults to 10-year Sf".
3. `INLET SPACING` column AK rows 11–96 are blank (no `#REF!`).
4. Name Manager (Formulas → Name Manager) shows no `#REF!` entries and no `SelectCounty` entry; `Select_County` remains.
5. `EQUATIONS + INSTRUCTIONS` shows the acyclic-network note appended at the bottom.
6. Populate a 3-pipe sample: STORM DRAIN COMPS rows 10–12 take real From/To/area/length/invert/slope values (copy from `docs/template_wip_new_pre-repair.xlsx` — rows 10–12 carry a pre-populated I-3 → MH-4 → MH-3 chain). Confirm columns H, K, M, T, U, Y, AF compute without errors and that HGL rows 7–9 populate end-to-end.

If any step fails, do NOT commit — fix the underlying issue in `repair.py`, re-run Task 14 Step 1, and re-verify.

- [ ] **Step 4: Commit the repaired xlsx**

```bash
git add docs/template_wip_new.xlsx
git commit -m "docs(template): apply repair.py (R1-R5) to template_wip_new.xlsx"
```

---

## Task 15: Rulebook refresh — engineering-methodology.md (U1, U3, U5)

**Files:**
- Modify: `docs/engineering-methodology.md` §5 "Structure Loss — Controlling-Angle Method"

- [ ] **Step 1: Locate the section**

Run:
```bash
grep -n "## 5. Structure Loss" docs/engineering-methodology.md
grep -n "Governing source" docs/engineering-methodology.md
```
Expected: one match each. Note the line numbers.

- [ ] **Step 2: Replace the "Governing source" paragraph (U1)**

Find the paragraph that currently starts with `**Governing source:** the controlling-angle junction procedure is specified verbatim by the *MCDOT Drainage Design Criteria for Montgomery County, MD*...` and replace it with:

```markdown
**Governing source:** the controlling-angle junction procedure is specified verbatim in the *MDSHA Drainage Manual*, Chapter 5 "Storm Drain Systems" (p. 5-26, September 2023 edition), which is the primary state-wide reference for Maryland. The *MCDOT Drainage Design Criteria for Montgomery County, MD* (10th Revised Final, 2014), §4.3.2.3 "Manhole, Inlet and Field Connection Energy Losses — Junctions" (p. 46), adopts MDSHA's procedure word-for-word for Montgomery County. `Hb = Kb × Vf²/2g` is MCDOT's Eq. 4-8 (identical to MDSHA Eq. 4-8 cited by reference), with `Vf` the velocity at the given discharge in the (near-full) outlet pipe. The loss coefficients are MCDOT's Appendix B `Kb` table (sourced from MSHA form 61.1-408.0/408.1), editable in-app; seeded defaults are a published AASHTO bend-loss curve — replace with your agency's Appendix B values before submittal.
```

- [ ] **Step 3: Add the PG County divergence note (U3)**

Immediately after the controlling-angle worked example in §5.2 (just after the "The controlling angle is the smaller loss's angle, not the larger." sentence), insert a new paragraph:

```markdown
**PG County divergence.** The *PG County Stormwater Management Design Manual*, Chapter 8 "Storm Drain Design Criteria" (p. 8-27, Issue Date September 30, 2014), states the opposite rule in a numbered procedure: "If H₂ is greater, Θ₂ is the controlling angle. If H₁ is greater, Θ₁ is the controlling angle" — i.e., the *larger* hypothesized loss's angle controls. Appendix 8-15 Sample Headloss Calculation (DRAFT, July 26 2014) applies the Ch. 8 rule in Example 2 (K₂ = 1.39 used because H₂ > H₁ → Hb = 1.45 ft). Both agencies cite the same upstream MSHA form 61.1-408.0/408.1 Kb table; the divergence is in the *procedure*, not the coefficients. This is a real jurisdictional difference — not a transcription error — and must be honored per the agency reviewing the project. The near-equal Kb values across adjacent angle rows make the arithmetic difference small (~2% in Appendix 8-15 Example 2), but a PG-reviewed project with asymmetric Kb values could see a larger gap. The tool defaults to the MDSHA / MCDOT rule.
```

- [ ] **Step 4: Add the jurisdiction-toggle intent subsection (U5)**

Append a new subsection at the end of §5 (before the "### 5.2 Inflow cases" if the "Validity / notes" bullet list is still open; otherwise after the existing §5.2 content):

```markdown
### 5.3 Jurisdiction toggle (Spec 3)

A project-level setting `junctionAngleRule` selects which rule the structure-loss branch applies to the 2-inflow case. Values:

| Value | Rule | Source |
|---|---|---|
| `"smaller-loss"` (default) | The *smaller* of Lv1/Lv2 → its angle is the controlling angle | MDSHA Ch. 5 p. 5-26; MCDOT §4.3.2.3 p. 46 (identical text) |
| `"larger-loss"` | The *larger* of Lv1/Lv2 → its angle is the controlling angle | PG County SWM Manual Ch. 8 p. 8-27 (Sept 30 2014); example in Appendix 8-15 (DRAFT) |

Scope: single project-level value — never per-structure. Mixing rules inside one project would not pass review. Default stays `"smaller-loss"` regardless of selected county — a county change must not silently alter hydraulics; the toggle stays explicit and auditable. Formulas affected: only the 2-inflow branch of `computeStructureCalc` (Section 5.2 above); the 0-inflow, 1-inflow, and >2-inflow cases are unaffected.

Spec 3 ("Calculator + visualizer two-template compatibility") implements the UI control, project-state field, xlsx round-trip, and calculator branch.
```

- [ ] **Step 5: Verify the edits grep-wise**

Run:
```bash
grep -n "MDSHA Drainage Manual.*5-26" docs/engineering-methodology.md
grep -n "PG County divergence" docs/engineering-methodology.md
grep -n "junctionAngleRule" docs/engineering-methodology.md
```
Expected: one match each.

- [ ] **Step 6: Commit**

```bash
git add docs/engineering-methodology.md
git commit -m "docs(methodology): refresh junction-loss citations + document jurisdiction toggle intent"
```

---

## Task 16: Rulebook refresh — storm-drain-calculator-spec.md (U2 + U5 mirror)

**Files:**
- Modify: `drainage-calculator/storm-drain-calculator-spec.md` §1.4

- [ ] **Step 1: Locate the section**

Run:
```bash
grep -n "### 1.4 Hydraulic Grade Line" drainage-calculator/storm-drain-calculator-spec.md
grep -n "controlling-angle" drainage-calculator/storm-drain-calculator-spec.md
```
Expected: one match for §1.4 heading; one or more for controlling-angle.

- [ ] **Step 2: Add a citation paragraph after §1.4's controlling-angle description**

Immediately after the existing controlling-angle procedure block in §1.4 (after the "the SMALLER loss's angle controls — not the larger" line), insert:

```markdown
**Citations (mirror of `docs/engineering-methodology.md` §5):**

- Primary source: *MDSHA Drainage Manual*, Ch. 5 "Storm Drain Systems" p. 5-26 (September 2023 edition) — states the smaller-loss-angle rule verbatim.
- MoCo adoption: *MCDOT Drainage Design Criteria*, §4.3.2.3 "Manhole, Inlet and Field Connection Energy Losses — Junctions" p. 46 (Revised Final, June 2014) — adopts the MDSHA procedure word-for-word.
- Jurisdictional divergence: *PG County Stormwater Management Design Manual*, Ch. 8 "Storm Drain Design Criteria" p. 8-27 (Issue Date September 30, 2014) — states the opposite larger-loss-angle rule in prose. Appendix 8-15 Sample Headloss Calculation (DRAFT July 26 2014) demonstrates it in Example 2.
- Toggle: `junctionAngleRule` project setting selects between the two rules. Default `"smaller-loss"`; PG-reviewed projects can set `"larger-loss"`. Implementation lives in Spec 3 (two-template calculator compatibility). The toggle round-trips through the golden template's `Config` sheet (Spec 2); legacy xlsx imports default to `"smaller-loss"`.
```

- [ ] **Step 3: Verify the edit**

Run:
```bash
grep -n "MDSHA Drainage Manual" drainage-calculator/storm-drain-calculator-spec.md
grep -n "junctionAngleRule" drainage-calculator/storm-drain-calculator-spec.md
```
Expected: one match each.

- [ ] **Step 4: Commit**

```bash
git add drainage-calculator/storm-drain-calculator-spec.md
git commit -m "docs(spec): mirror methodology citation refresh + junctionAngleRule intent"
```

---

## Task 17: Rulebook refresh — user-design-criteria.md (U4 + U6 + U7)

**Files:**
- Modify: `docs/user-design-criteria.md`

### U4 — Add MCDOT §4.3.3(k) cross-reference to the existing pipe-slope section

- [ ] **Step 1: Locate the section**

Run:
```bash
grep -n "Pipe slope" docs/user-design-criteria.md
```
Expected: one match.

- [ ] **Step 2: Add a parenthetical cross-reference**

In the "Pipe slope (longitudinal)" section, immediately after the slope rationale paragraph (the one ending `...the agency manual's absolute minimum ... may be lower, but designs should aim for the above when feasible.`), append:

```markdown
**Agency cross-reference:** MCDOT Drainage Design Criteria §4.3.3(k) requires "Pipe shall not be designed on a slope less than 0.5 percent. However, to enhance self-cleaning characteristics, 15 and 18 inch diameter pipe are to be designed on an actual slope of 1 percent or greater." PG County DPIE Storm Drain & Paving Design Review Checklist §G-6 states the same rule in the generalized form: "Pipes less than 24" shall be designed for a minimum slope of 1% and pipes 24" or greater may be designed with a minimum slope of 0.5%" — matching our rule verbatim. Our `< 24"` threshold here captures both: MCDOT's explicit 15/18-inch rule generalized to also catch 21" pipe (not explicitly named by MCDOT), and PG's exact threshold.
```

### U6 — Add new sections from PG DPIE Checklist

The PG County DPIE Storm Drain & Paving Design Review Checklist (`docs/dcv4552_design-review-checklist-storm-drain-and-paving-pdf.pdf`, Last Edited June 27, 2013) contains engineering criteria the calculator can honor or flag. Add these new sections to `docs/user-design-criteria.md`, after the existing "Crown matching at junctions" section.

- [ ] **Step 3: Append the PG Citation to the "Crown matching at junctions" section**

At the end of that existing section (just before the "Calculator enforcement" paragraph), append:

```markdown
**Agency cross-reference:** PG County DPIE Checklist §G-10: "Equal crown or greater in structure for incoming and outgoing pipes" — matches our rule verbatim.
```

- [ ] **Step 4: Append a new "Minimum pipe size" section**

At the end of the file, append:

```markdown
## Minimum pipe size

Main-line public storm-drain pipes are **15 inches minimum diameter**. ESD/SWM diversion pipes may be smaller.

Source: PG County DPIE Checklist §C-19. MCDOT §4.3.3(f) carries the same rule.

Calculator enforcement: not currently flagged by the HTML calculator. The user is responsible for selecting an acceptable minimum in the Pipe Sizing table.
```

- [ ] **Step 5: Append a new "Minimum pipe cover" section**

```markdown
## Minimum pipe cover (structural)

Vertical cover above the pipe crown:

| Pipe material | Minimum cover | Notes |
|---|---|---|
| RCP (rigid) | **1 ft** | Above the crown of the pipe. |
| Flexible (HDPE, CMP) | **2 ft** | Above the crown of the pipe. |

Source: PG County DPIE Checklist §G-8.

This is **distinct from** the "9 inch below the gravel subbase of the roadway" rule in the "Minimum cover below roadway" section above. The 9-inch rule governs clearance between the pipe crown and the bottom of the subbase layer in a roadway section; the G-8 rule is the general minimum cover above the crown anywhere along the pipe alignment. The more restrictive of the two governs at any given point.

Calculator enforcement: not currently flagged. A future pass could compare proposed crown elevation against proposed grade and emit a warning when cover drops below the above thresholds.
```

- [ ] **Step 6: Append a new "Minimum drop through structure" section**

```markdown
## Minimum drop through structure

Through every storm-drain structure, provide **≥ 0.1 ft drop** from U/S invert to D/S invert, or a slope of 1% through the structure — whichever yields the larger drop.

Source: PG County DPIE Checklist §G-9 ("A minimum drop of 0.1 foot shall be provided through the structure"); MCDOT §4.2.4(a) ("A minimum slope of 1 percent or 0.1 ft drop, whichever is greater").

Calculator enforcement: not currently flagged. The calculator tracks U/S and D/S inverts of each pipe; a future pass could compare incoming-pipe D/S invert against outgoing-pipe U/S invert at each structure.
```

- [ ] **Step 7: Append a new "Maximum access structure spacing" section**

```markdown
## Maximum access structure spacing

Between manholes or access structures, the pipe run shall be ≤ 400 ft (PG). MCDOT allows longer runs for larger pipe per Table 4-5 below.

| Pipe size | MCDOT Table 4-5 max spacing | PG Checklist C-20 |
|---|---|---|
| 15" through 24" | 400 ft | 400 ft |
| 27" through 42" | 500 ft | 400 ft |
| ≥ 48" | 600 ft | 400 ft |

Sources: PG County DPIE Checklist §C-20; MCDOT §4.2.4(2) Table 4-5.

The reviewing agency controls. If MoCo reviews, MCDOT's size-based limits apply; if PG reviews, PG's flat 400 ft applies regardless of pipe size.

Calculator enforcement: not currently flagged.
```

- [ ] **Step 8: Append a new "Pipe entry angle at flat-wall structures" section**

```markdown
## Pipe entry angle at flat-wall structures

A pipe entering a structure with a flat wall shall deflect no more than **45°** from the outgoing pipe's alignment.

Source: PG County DPIE Checklist §C-21.

This is a geometric clearance constraint for precast structures, not a hydraulic criterion. It constrains layout, not the Hb computation (which runs the controlling-angle method per `engineering-methodology.md` §5).

Calculator enforcement: not currently flagged. The Junction Structure tab already captures pipe deflection angles per `storm-drain-calculator-spec.md` §1.4; a future pass could flag any flat-wall-entering pipe with angle > 45°.
```

- [ ] **Step 9: Append a new "Last pipe reach to outfall" section**

```markdown
## Last pipe reach to outfall

The final pipe reach discharging to an outfall shall have **slope ≤ 1%**. Provide drop structures as needed to achieve this.

Source: PG County DPIE Checklist §H-6.

Rationale: a flatter last reach reduces exit velocity, limiting rip-rap requirements and erosion at the outfall.

Calculator enforcement: not currently flagged. The calculator knows which pipe is the outfall (`forceElev = true` on the downstream structure, or the structure with no outgoing pipe); a future pass could check the slope of the pipe immediately upstream of that node.
```

- [ ] **Step 10: Append a new "Open-channel erosion velocity" section**

```markdown
## Open-channel erosion velocity

For open-channel segments outside of pipe conveyance:

| Fill type | Threshold | Treatment if exceeded |
|---|---|---|
| Cut channel (stable existing material) | **5 fps** | Rip-rap or concrete required. |
| Fill channel (constructed on fill) | **4 fps** | Rip-rap or concrete required. |

Source: PG County DPIE Checklist §L-4.

Calculator enforcement: out of scope for the conveyance-pipe calculator. Document for completeness; the engineer evaluates open-channel segments separately.
```

- [ ] **Step 11: Append a new "HGL clearance — jurisdictional note" section**

```markdown
## HGL clearance — jurisdictional note

| Agency | 10-yr HGL ceiling |
|---|---|
| MDSHA Ch. 5 / MCDOT §4.3.1 | `HGL ≤ crown + 1 ft` **AND** `HGL ≤ rim − 1 ft` (both checks). |
| PG County SWM Ch. 8 / DPIE Checklist §I-2 | `HGL ≤ rim − 12 inches` only. No explicit crown ceiling — pipes may run surcharged within the structure as long as HGL stays ≥ 1 ft below the grate or bottom of curb. |

The HTML calculator currently enforces the MDSHA/MCDOT rule (both checks). The PG rule allows more surcharge above the pipe crown. This divergence is analogous to the `junctionAngleRule` controlling-angle divergence documented in `engineering-methodology.md` §5 — different agencies, different rules in force.

A future Spec 3 may add a project-level `hglCrownCeilingRule` toggle: `"crown-plus-1ft"` (default — MDSHA/MCDOT) vs `"rim-only"` (PG). For now the stricter MDSHA/MCDOT rule is applied uniformly and a PG-reviewed project that fails the MDSHA crown check should document that the PG rim-only rule is the governing criterion.

Calculator enforcement: MDSHA/MCDOT rule only. See `engineering-methodology.md` §6 (HGL propagation) for the clearance checks.
```

### U7 — Small-area Tc lookup and area-weighted composite C

Both MoCo (MCDOT §3.2.1 Table 3-3) and PG County (SWM Ch. 8 §8.2.1 / §8.2.2) allow a C-factor lookup for Tc on drainage areas ≤ 2 acres, and both require area-weighted composite C across subareas.

- [ ] **Step 12: Append "Time of concentration" section**

Append to `docs/user-design-criteria.md`:

```markdown
## Time of concentration — small drainage areas

For drainage areas **≤ 2.0 acres**, Tc may be selected from a lookup keyed on the drainage area's composite runoff coefficient:

| Composite C | Tc (minutes) |
|---|---|
| ≥ 0.80 | 5 |
| 0.65 – 0.79 | 7 |
| 0.40 – 0.64 | 10 |
| ≤ 0.39 | 15 |

Source: MCDOT Drainage Design Criteria §3.2.1 Table 3-3 "Small Drainage Area Time of Concentration". PG County SWM Ch. 8 §8.2.2 carries the same two-track approach (lookup for small areas, segmental TR-55 for larger).

For drainage areas **> 2.0 acres**, compute Tc using TR-55 segmental (sheet flow + shallow concentrated + channel flow) or an equivalent method. MCDOT Eq. 3-1 gives the trailing travel-time segment: `Tc = Tt + (L − 100) / (60 V)`, with `V = 7 fps` for average drainage-area slope ≤ 7 % and `V = 10 fps` for slope > 7 %.

Calculator enforcement: the HTML calculator's Drainage Area tab accepts Tc as either a direct user entry or a TR-55 segmental computation per `engineering-methodology.md` §2. For small areas (≤ 2 acres), the user may enter Tc per the Table 3-3 lookup directly. A future pass could add a Tc-method option that auto-selects the lookup when the entered drainage area is ≤ 2 acres.
```

- [ ] **Step 13: Append "Weighted composite runoff coefficient" section**

```markdown
## Weighted composite runoff coefficient (C)

For a drainage area composed of multiple land-use subareas, the composite C used in the Rational Method is the area-weighted average:

```
C_composite = Σ (Cx × Ax) / Σ Ax
```

where `Cx` is the tabulated runoff coefficient for subarea x (impervious, lawns, woods, etc.) and `Ax` is its area.

Sources: MCDOT §3.4 "Runoff Coefficients" — states the weighting formula explicitly and provides Table 3-5 of C values by land cover. PG County SWM Ch. 8 §8.2.1 — "C factors for development shall represent a weighted average based upon the proportion of the surface area covered by impervious materials, lawns, or woods." Table 8-1 in PG Ch. 8 lists the Rational Method C values by land use.

The composite C feeds the small-area Tc lookup above and the Rational Method `Q = C i A` (`engineering-methodology.md` §1).

Calculator enforcement: the HTML calculator's Drainage Area tab accepts C as a single value per row. For catchments with multiple land uses, enter the composite C computed per the formula above. The WIP xlsx template (`docs/template_wip_new.xlsx`) implements the composite C computation on its `C_FACTOR` sheet (column M across up to eight land-use subareas). A future pass could add a subarea-breakdown UI to the HTML calculator that computes the composite C automatically.
```

### Verification

- [ ] **Step 14: Verify every edit**

Run:
```bash
grep -n "Agency cross-reference" docs/user-design-criteria.md
grep -n "4.3.3(k)" docs/user-design-criteria.md
grep -n "G-10" docs/user-design-criteria.md
grep -n "^## Minimum pipe size" docs/user-design-criteria.md
grep -n "^## Minimum pipe cover" docs/user-design-criteria.md
grep -n "^## Minimum drop through structure" docs/user-design-criteria.md
grep -n "^## Maximum access structure spacing" docs/user-design-criteria.md
grep -n "^## Pipe entry angle" docs/user-design-criteria.md
grep -n "^## Last pipe reach to outfall" docs/user-design-criteria.md
grep -n "^## Open-channel erosion velocity" docs/user-design-criteria.md
grep -n "^## HGL clearance" docs/user-design-criteria.md
grep -n "^## Time of concentration" docs/user-design-criteria.md
grep -n "^## Weighted composite runoff" docs/user-design-criteria.md
```
Expected: one match for each line (13 lines total).

- [ ] **Step 15: Commit**

```bash
git add docs/user-design-criteria.md
git commit -m "docs(criteria): add PG DPIE checklist criteria + small-area Tc/weighted-C (U4+U6+U7)"
```

---

## Task 18: Grep sweep for stale citations across docs/

Find any prior write-ups that cite the controlling-angle rule as "MCDOT §4.3.2.3" standalone (without the new MDSHA primary citation) and update them to reference the refreshed methodology section instead of restating the rule.

**Files:**
- Modify: whichever `docs/**/*.md` files the grep finds (typically 2-5 files among prior design docs and the engineering-methodology / HGL-related docs).

- [ ] **Step 1: Run the grep sweep**

Run:
```bash
grep -rn "MCDOT.*4.3.2.3" docs/ --include="*.md"
grep -rn "controlling-angle" docs/ --include="*.md"
```

- [ ] **Step 2: Review each hit and decide**

For each hit that is NOT in `docs/engineering-methodology.md`, `drainage-calculator/storm-drain-calculator-spec.md`, or `docs/superpowers/specs/2026-11-25-template-wip-audit-design.md`:

- If the hit is a one-line citation like "per MCDOT §4.3.2.3" → add " (and MDSHA Ch. 5 p. 5-26)" after the MCDOT reference.
- If the hit describes the rule in prose → replace with "see `docs/engineering-methodology.md` §5 for the MDSHA/MCDOT vs PG County rule and the `junctionAngleRule` toggle."

Use the `Edit` tool per file. Do not blanket-edit without reading context.

- [ ] **Step 3: Re-run the grep to confirm no outdated citations remain**

Run:
```bash
grep -rn "MCDOT.*4.3.2.3" docs/ --include="*.md" | grep -v "engineering-methodology\|calculator-spec\|template-wip-audit"
```
Expected: zero output (every remaining MCDOT citation is accompanied by the MDSHA primary citation, or is in the three authoritative files that are supposed to carry the full citation).

- [ ] **Step 4: Commit**

```bash
git add -u docs/
git commit -m "docs(citations): add MDSHA primary citation alongside MCDOT in prior write-ups"
```

---

## Task 19: Final acceptance sweep

All deliverables produced. This is the end-to-end gate before closing Spec 1.

- [ ] **Step 1: Verify the full test suite**

Run:
```bash
pytest docs/template-analysis/ -v
```
Expected: every test PASSES.

- [ ] **Step 2: Verify the repaired xlsx one last time**

Run:
```bash
python docs/template-analysis/extract.py docs/template_wip_new.xlsx /tmp/pass_a_post.json 2>/dev/null \
  || python docs/template-analysis/extract.py docs/template_wip_new.xlsx docs/template-analysis/_scratch_post.json
python -c "
import json, sys
p='docs/template-analysis/_scratch_post.json'
try: d=json.loads(open(p).read())
except FileNotFoundError: d=json.loads(open('/tmp/pass_a_post.json').read())
total_ref=sum(s['ref_error_count'] for s in d['sheets'])
print('sheets:', d['sheet_count'])
print('total #REF! formulas:', total_ref)
print('broken defined names:', len(d['broken_defined_names']))
print('duplicate-name ranges:', len(d['duplicate_defined_names']))
assert total_ref==0, f'#REF! still present: {total_ref}'
assert not d['broken_defined_names'], 'broken names remain'
assert not d['duplicate_defined_names'], 'duplicate names remain'
print('clean')
"
rm -f docs/template-analysis/_scratch_post.json
```
Expected: `sheets: 16`, `total #REF! formulas: 0`, `broken defined names: 0`, `duplicate-name ranges: 0`, `clean`.

- [ ] **Step 3: Check all 17 analysis docs exist and reference the rulebook**

Run:
```bash
ls docs/template-analysis/*.md | wc -l
grep -l "engineering-methodology.md" docs/template-analysis/*.md | wc -l
```
Expected: 17 files total (README + 16 tabs). Count of files citing the methodology should be ≥ 4 (the working-engine docs at minimum).

- [ ] **Step 4: Verify CLAUDE.md is still under 200 lines**

Run:
```bash
wc -l CLAUDE.md
```
Expected: ≤ 200.

- [ ] **Step 5: Verify no change was made to the calculator source**

Run:
```bash
git log --since="1 day ago" --name-only --pretty=format: -- drainage-calculator/ | sort -u
```
Expected: shows only `drainage-calculator/storm-drain-calculator-spec.md` (from Task 16); the `.html` files MUST NOT appear.

- [ ] **Step 6: Delete the helper script if it still exists**

Run:
```bash
rm -f _append_plan.py _payload.md
```

- [ ] **Step 7: Final commit (if anything changed in Steps 1–6)**

```bash
git status
# If anything is modified or untracked that belongs in the repo:
git add -u
git commit -m "docs(template): final acceptance pass"
```

Spec 1 complete. Spec 2 (new golden template) and Spec 3 (calculator two-template compatibility, including `junctionAngleRule` implementation) are the next brainstorms when ready.
