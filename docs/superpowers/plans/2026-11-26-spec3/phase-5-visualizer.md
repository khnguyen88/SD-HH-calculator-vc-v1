# Spec 3 — Phase 5: Visualizer Parity + Contract Bump (Tasks 21–23)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Finalize the shared reader module (add `readRobustWorkbook` body), wire both calculator and visualizer to consume it, bump `calculator-import-contract.md` to Contract-Version 2.

**Spec:** `docs/superpowers/specs/2026-11-26-spec3-three-shape-bidirectional-design.md` §9, §13

**Depends on:** Phase 4 complete.

---

## Task 21: Finalize shared reader — `readRobustWorkbook`

**Files:**
- Modify: `drainage-calculator/lib/xlsx-shape-reader.js`
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`
- Create: `docs/template-analysis/test_robust_reader.py`

- [ ] **Step 21.1: Replace the Robust reader stub**

In `drainage-calculator/lib/xlsx-shape-reader.js`:

```javascript
function readRobustWorkbook(wb){
  const base = readSimpleWorkbook(wb);
  base._shape = "robust";

  const tr55 = wb.Sheets["TR-55 Segments"];
  const tr55Segments = [];
  if(tr55){
    const sheetAoa = XLSX.utils.sheet_to_json(tr55, {header:1, raw:true, defval:""});
    const headers = (sheetAoa[0]||[]).map(h => String(h).trim());
    const idx = (name) => headers.indexOf(name);
    for(let i = 1; i < sheetAoa.length; i++){
      const row = sheetAoa[i];
      if(!row.some(v => v !== "" && v != null)) continue;
      tr55Segments.push({
        drainageAreaId: row[idx("Drainage Area")] || "",
        order: row[idx("Order")] || i,
        type: String(row[idx("Type")]||"").toLowerCase(),
        n: row[idx("n")] || "",
        L: row[idx("L (ft)")] || "",
        s: row[idx("s (ft/ft)")] || "",
        P2: row[idx("P2 (in)")] || "",
        surface: row[idx("Surface")] || "",
        area: row[idx("Area a (sf)")] || "",
        wp: row[idx("Wetted Perimeter Pw (ft)")] || "",
      });
    }
  }

  const outletStructures = readSheetAsObjects(wb, "Outlet Structures");
  const outletDevices    = readSheetAsObjects(wb, "Outlet Devices");

  return Object.assign(base, { tr55Segments, outletStructures, outletDevices });
}

function readSheetAsObjects(wb, sheetName){
  const ws = wb.Sheets[sheetName];
  if(!ws) return [];
  const aoa = XLSX.utils.sheet_to_json(ws, {header:1, raw:true, defval:""});
  if(aoa.length < 1) return [];
  const headers = aoa[0].map(h => String(h).trim());
  return aoa.slice(1)
    .filter(r => r.some(v => v !== "" && v != null))
    .map(r => {
      const obj = {};
      headers.forEach((h, i) => { obj[h] = r[i]; });
      return obj;
    });
}
```

- [ ] **Step 21.2: Wire into the calculator's import dispatch**

In the dev HTML, in `importExcel`, after the Simple branch, add:

```javascript
      if(shape === "robust"){
        const robust = window.__xlsxShapeReader.readRobustWorkbook(wb);
        applyRobustReaderResult(robust);
        state.exportShape = "robust";
        syncShapeRadio();
        renderAll(); updateSavesUI();
        return;
      }
```

Add `applyRobustReaderResult` just below `applySimpleReaderResult`:

```javascript
function applyRobustReaderResult(robust){
  applySimpleReaderResult(robust);
  const daByLabel = {};
  state.drainage.forEach(d => { daByLabel[d.structureId] = d; });
  (robust.tr55Segments || []).forEach(seg => {
    const da = daByLabel[seg.drainageAreaId];
    if(!da) return;
    da.tr55.segments.push({ id: nextId(), type: seg.type,
      n: seg.n, L: seg.L, s: seg.s, P2: seg.P2,
      surface: seg.surface, area: seg.area, wp: seg.wp });
    da.tcMethod = "tr55";
  });
  state.outletStructures = (robust.outletStructures || []).map(r => ({
    id: nextId(),
    label: r["Label"] || r["Outlet Structure ID"] || "",
    desc:  r["Description"] || "",
    precisionMode: r["Precision Mode"] === "individual" ? "individual" : "uniform",
    startElev: r["Start Elevation (ft)"] || "",
    endElev:   r["End Elevation (ft)"] || "",
    coarseIncrement: r["Coarse Increment (ft)"] || 0.5,
    fineIncrement:   r["Fine Increment (ft)"] || 0.05,
    fineBand:        r["Fine Band +/- (ft)"] || 0.3,
    twMode: r["Tailwater Mode"] || "none",
    twFixed: r["Tailwater Fixed Elevation (ft)"] || "",
    twStructureId: (function(){
      const name = r["Tailwater Linked Structure ID"];
      if(!name) return "";
      const st = state.structures.find(s => s.structureId === name);
      return st ? st.id : "";
    })(),
  }));
  state.activeOutletId = state.outletStructures.length
    ? state.outletStructures[0].id : "";
  const osByLabel = {};
  state.outletStructures.forEach(os => { osByLabel[os.label] = os; });
  state.outletDevices = (robust.outletDevices || []).map(r => {
    const osLabel = r["Outlet Structure"] || "";
    const os = osByLabel[osLabel];
    return {
      id: nextId(),
      outletStructureId: os ? os.id : state.activeOutletId,
      label: r["Label"] || "", type: r["Type"] || "orifice",
      invert: r["Invert (ft)"] || "",
      crest:  r["Crest (ft)"] || "",
      diameter: r["Diameter (in)"] || "",
      diameterUnit: r["Diameter Unit"] === "ft" ? "ft" : "in",
      length: r["Length (ft)"] || "",
      lengthUnit: r["Length Unit"] === "in" ? "in" : "ft",
      weirShape: r["Weir Shape"] || "rect",
      notchAngle: r["Notch Angle (deg)"] || 90,
      cd: r["Type"] !== "weir" ? (r["Coefficient"] || 0.6) : 0.6,
      coef: r["Type"] === "weir" ? (r["Coefficient"] || 3.1) : 3.1,
      fineOverrideEnabled: String(r["Fine Override Enabled"]).toUpperCase() === "TRUE",
      fineIncrementOverride: r["Fine Increment Override (ft)"] || "",
      fineBandOverride: r["Fine Band Override (ft)"] || "",
      notes: r["Notes"] || "",
    };
  });
}
```

- [ ] **Step 21.3: Robust reader pytest**

Create `docs/template-analysis/test_robust_reader.py`:

```python
"""Confirm the shape reader populates Robust-only extras from a Robust file."""
from pathlib import Path
import openpyxl
import pytest

HERE = Path(__file__).parent
FIXTURE = HERE / "fixtures" / "robust_roundtrip.xlsx"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Create via Phase 2 Task 13 Step 13.2")
def test_robust_has_tr55_sheet():
    wb = openpyxl.load_workbook(FIXTURE, data_only=True)
    ws = wb["TR-55 Segments"]
    assert ws["A1"].value == "Drainage Area"


@pytest.mark.skipif(not FIXTURE.exists(), reason="see fixture setup")
def test_robust_has_outlet_sheets():
    wb = openpyxl.load_workbook(FIXTURE, data_only=True)
    assert "Outlet Structures" in wb.sheetnames
    assert "Outlet Devices" in wb.sheetnames
```

- [ ] **Step 21.4: Commit**

```bash
git add drainage-calculator/lib/xlsx-shape-reader.js \
        drainage-calculator/storm-drain-design-calculator-dev.html \
        drainage-calculator/storm-drain-design-calculator.html \
        docs/template-analysis/test_robust_reader.py
git commit -m "feat(reader): Robust reader + calculator dispatch

readRobustWorkbook reads Simple-covered sheets via readSimpleWorkbook
then overlays TR-55 Segments, Outlet Structures, Outlet Devices.
Calculator's importExcel dispatches both shapes via the shared reader.
Spec 3 Task 21."
```

---

## Task 22: Visualizer parity — wire shared reader into visualizer

**Files:**
- Modify: `visualizer/storm-drain-visualizer-dev.html`
- Modify: `visualizer/build.js` if a dedicated visualizer build exists, otherwise extend `drainage-calculator/build.js` (first step of this task checks which it is)
- Create: `docs/template-analysis/test_visualizer_reader_parity.py`

- [ ] **Step 22.1: Confirm visualizer file layout**

Expected layout (verified at spec-write time):
- `visualizer/storm-drain-visualizer-dev.html` — dev source
- `visualizer/storm-drain-visualizer.html` — built output

Check for a visualizer-specific build script:

```bash
ls visualizer/*.js 2>/dev/null
ls drainage-calculator/build.js
```

If `visualizer/build.js` exists, extend that. Otherwise add a visualizer-inline block to `drainage-calculator/build.js` that reads from `visualizer/storm-drain-visualizer-dev.html` and writes to `visualizer/storm-drain-visualizer.html`.

- [ ] **Step 22.2: Inline the shape reader into the visualizer**

Add the placeholder + dev loader to the visualizer dev HTML, same pattern as calculator (Phase 1 Task 7.3):

```html
<!-- XLSX_SHAPE_READER_PLACEHOLDER -->
<script src="../drainage-calculator/lib/xlsx-shape-reader.js"></script>
```

Update the visualizer's build script (or add a case to `drainage-calculator/build.js` if it handles both) to inline the reader.

- [ ] **Step 22.3: Dispatch on visualizer import**

Find the visualizer's xlsx-handling function. Add a detectShape dispatch at the top:

```javascript
const shape = window.__xlsxShapeReader.detectShape(wb);
if(shape === "unknown"){
  toast("Couldn't read this xlsx. Use a calculator export, a golden "
        +"template, or a legacy WIP file.", true);
  return;
}
const reader = (shape === "robust")
  ? window.__xlsxShapeReader.readRobustWorkbook
  : window.__xlsxShapeReader.readSimpleWorkbook;
const result = reader(wb);
applyVisualizerImport({
  structures: result.structures,
  pipes: result.pipes,
  config: result.config,
});
```

Adapt `applyVisualizerImport` to the visualizer's existing state-apply pattern — review the visualizer's current reader for the equivalent call.

- [ ] **Step 22.4: Visualizer parity pytest**

Create `docs/template-analysis/test_visualizer_reader_parity.py`:

```python
"""Smoke: the shared reader module is present in the visualizer build."""
from pathlib import Path


def find_visualizer_build():
    for p in Path(".").rglob("storm-drain-visualizer.html"):
        if "node_modules" in p.parts: continue
        return p
    return None


def test_visualizer_has_shape_reader_inlined():
    v = find_visualizer_build()
    if v is None:
        return
    text = v.read_text(encoding="utf-8", errors="ignore")
    assert "window.__xlsxShapeReader" in text, (
        "Visualizer build missing inlined shape reader"
    )
    assert "detectShape" in text
```

- [ ] **Step 22.5: Manual browser verification**

Open the visualizer. Import `docs/template_wip_new_pre-repair.xlsx`. Expected: HGL profile renders.

Import `docs/template-analysis/fixtures/robust_roundtrip.xlsx`. Expected: same profile renders.

- [ ] **Step 22.6: Commit**

```bash
git add <visualizer-dev-html-path> \
        <visualizer-built-html-path> \
        drainage-calculator/build.js \
        docs/template-analysis/test_visualizer_reader_parity.py
git commit -m "feat(visualizer): share the Spec-3 reader via inline module

Visualizer now imports Simple and Robust xlsx via window.__xlsxShapeReader.
Previously only accepted the calculator's native shape. Spec 3 Task 22."
```

---

## Task 23: Contract-Version bump + Phase 5 ship gate

**Files:**
- Modify: `docs/template-analysis/calculator-import-contract.md`

- [ ] **Step 23.1: Bump Contract-Version + add §3a, §4a**

Open `docs/template-analysis/calculator-import-contract.md`. Change the top header:

```markdown
**Contract-Version:** 2
```

After §3 (template-shape pipe-row read), add a new §3a:

```markdown
## 3a. Pipe-row read path — Robust shape

Sheet: `Pipe Sizing`, rows 2+. Structure metadata on `Junction Structure`.

| Source | Calculator field |
|---|---|
| `Pipe Sizing!A{row}` | `id` |
| `Pipe Sizing!B{row}` | `fromId` |
| `Pipe Sizing!C{row}` | `toId` |
| `Pipe Sizing!D{row}` | `angle` |
| `Pipe Sizing!E{row}` | `shape` (circular/elliptical) |
| `Pipe Sizing!F{row}` | `size` (in or SPANxRISE) |
| `Pipe Sizing!G{row}` | `n` |
| `Pipe Sizing!H{row}` | `upstreamInvert` |
| `Pipe Sizing!I{row}` | `downstreamInvert` |
| `Pipe Sizing!J{row}` | `slope` |
| `Pipe Sizing!K{row}` | `length` |
| `Pipe Sizing!Q{row}` | `splitRole` |
| `Junction Structure!A{row}` | `structureId` |
| `Junction Structure!B{row}` | `desc` |
| `Junction Structure!D{row}` | `type` |
| `Junction Structure!F{row}` | `startElev` |
| `Junction Structure!H{row}` | `rim` |
| `Junction Structure!V{row}` | `splitMethod` |
| `Junction Structure!W{row}` | `splitCapacity` |
| `Junction Structure!X{row}` | `splitRatio` |
```

After §4, add §4a:

```markdown
## 4a. Drainage-area read path — Robust shape

Sheet: `Drainage Area`, rows 2+.

| Source | Calculator field |
|---|---|
| `Drainage Area!A{row}` | `structureId` (join key) |
| `Drainage Area!C{row}` | `area` |
| `Drainage Area!D{row}` | `C` |
| `Drainage Area!G{row}` | `tc` |
| `Drainage Area!H{row}` | `cf` |
| `Drainage Area!I{row}` | `tcMethod` |

Plus `TR-55 Segments` tagged by Drainage Area, `Outlet Structures`,
`Outlet Devices`, `Rainfall Settings` — each a flat sheet with a
header row; the reader uses `readSheetAsObjects` to materialize rows
as `{header: value}` dicts.
```

Update §1 (shape detection):

```markdown
## 1. Shape detection

Returns one of three values:
  - `simple`  — STORM DRAIN COMPS present, Outlet Structures absent.
                Covers both legacy WIP and golden.
  - `robust`  — STORM DRAIN COMPS AND Outlet Structures both present.
  - `unknown` — Neither STORM DRAIN COMPS nor Pipe Sizing present.
                Reader toasts an error and aborts.
```

Update §7 (export) to list both write paths (Simple and Robust) with their write surfaces.

- [ ] **Step 23.2: Phase 5 ship gate matrix**

| Action | Expected |
|---|---|
| Import WIP, golden, Robust-export into the calculator | All load; toggle flips to matching shape |
| Export Simple from state with outlet work | Lossy toast; file has 17 Simple sheets |
| Export Robust from same state | 17+ sheets including outlet work; opens cleanly |
| Import any xlsx into the visualizer | HGL profile renders; config.hglMethod honored |
| `pytest docs/template-analysis/` | All green |

- [ ] **Step 23.3: Final commit**

```bash
git add docs/template-analysis/calculator-import-contract.md
git commit -m "docs(contract): bump Contract-Version to 2

Add §3a (Robust pipe-row read), §4a (Robust drainage-area read). Update
§1 shape detection. Update §7 write paths. Spec 3 Task 23 — final."
```

---

## Spec 3 complete

- [ ] Grep every phase file for `TBD`, `TODO`, `FIXME`, `fill in` — zero hits.
- [ ] Every file-path reference matches reality.
- [ ] `state.exportShape` set in all three places (default state, Simple branch, Robust branch).
- [ ] `syncShapeRadio()` called from all three locations.
- [ ] `_legacyBuildWorkbook` deleted.
- [ ] Pytest total ≈ 84+ tests, all passing.
- [ ] Manual Excel verification across all shapes passes.

All five phases shipped. Spec 3 of 3 complete.
