# Spec 3 — Phase 1: Simple Reader (Tasks 3–7)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add a shape detector + Simple-shape reader to the calculator so it can import `template_wip_new.xlsx` and `template_golden.xlsx` in addition to its own native format.

**Spec:** `docs/superpowers/specs/2026-11-26-spec3-three-shape-bidirectional-design.md` §4–§5

**Depends on:** Pre-work complete (DATA2 cleaned, docs corrected, WIP SHA re-pinned).

---

## Task 3: Create `xlsx-shape-reader.js` + `detectShape`

**Files:**
- Create: `drainage-calculator/lib/xlsx-shape-reader.js`
- Create: `docs/template-analysis/test_shape_detect.py`
- Create: `docs/template-analysis/fixtures/robust_minimal.xlsx`

- [ ] **Step 3.1: Write the detectShape test**

Create `docs/template-analysis/test_shape_detect.py`:

```python
"""Verify detectShape returns correct value for all fixture shapes.

detectShape is a JS function in drainage-calculator/lib/xlsx-shape-reader.js.
This test exercises the Python-equivalent logic.
"""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
WIP = HERE.parent / "template_wip_new.xlsx"
GOLDEN = HERE.parent / "template_golden.xlsx"
ROBUST = HERE / "fixtures" / "robust_minimal.xlsx"


def detect_shape_py(sheet_names):
    """Mirrors the JS detectShape logic in xlsx-shape-reader.js."""
    if "STORM DRAIN COMPS" in sheet_names:
        if "Outlet Structures" in sheet_names:
            return "robust"
        return "simple"
    return "unknown"


def test_wip_detects_simple():
    wb = openpyxl.load_workbook(WIP, read_only=True)
    assert detect_shape_py(wb.sheetnames) == "simple"


def test_golden_detects_simple():
    wb = openpyxl.load_workbook(GOLDEN, read_only=True)
    assert detect_shape_py(wb.sheetnames) == "simple"


def test_robust_detects_robust():
    wb = openpyxl.load_workbook(ROBUST, read_only=True)
    assert detect_shape_py(wb.sheetnames) == "robust"


def test_empty_detects_unknown():
    assert detect_shape_py(["Sheet1"]) == "unknown"
```

- [ ] **Step 3.2: Create the minimal Robust fixture generator**

Create `docs/template-analysis/fixtures/build_robust_minimal.py`:

```python
"""Build a minimal Robust-shape xlsx fixture for detectShape tests."""
from pathlib import Path
import openpyxl

OUT = Path(__file__).parent / "robust_minimal.xlsx"


def main():
    wb = openpyxl.Workbook()
    wb.active.title = "STORM DRAIN COMPS"
    wb.create_sheet("Outlet Structures")
    wb.save(OUT)


if __name__ == "__main__":
    main()
```

Generate it:

```bash
mkdir -p docs/template-analysis/fixtures
cd docs/template-analysis/fixtures && python build_robust_minimal.py
```

- [ ] **Step 3.3: Run the test**

```bash
cd docs && pytest template-analysis/test_shape_detect.py -v
```

Expected: 4 tests pass.

- [ ] **Step 3.4: Create `xlsx-shape-reader.js`**

Create `drainage-calculator/lib/xlsx-shape-reader.js`:

```javascript
/* xlsx-shape-reader.js — shared Simple/Robust xlsx reader.
   Inlined into both calculator and visualizer by build.js.
   Exposes window.__xlsxShapeReader with:
     detectShape, readSimpleWorkbook, readRobustWorkbook, hglMethodFromLabel */
(function(){
  "use strict";

  function detectShape(wb){
    const names = wb.SheetNames || Object.keys(wb.Sheets || {});
    const has = (n) => names.indexOf(n) !== -1;
    if(has("STORM DRAIN COMPS")){
      if(has("Outlet Structures")) return "robust";
      return "simple";
    }
    return "unknown";
  }

  function hglMethodFromLabel(label){
    const s = String(label||"").toLowerCase();
    if(s.indexOf("hec-22")!==-1 || s.indexOf("hec22")!==-1) return "hec22";
    if(s.indexOf("legacy")!==-1 || s.indexOf("both-end")!==-1
       || s.indexOf("both end")!==-1 || s.indexOf("conservative")!==-1){
      return "legacy-both-crown";
    }
    return "hec22";
  }

  function readSimpleWorkbook(wb){
    throw new Error("readSimpleWorkbook not yet implemented (Task 4-6)");
  }

  function readRobustWorkbook(wb){
    throw new Error("readRobustWorkbook not yet implemented (Task 21)");
  }

  const api = { detectShape, readSimpleWorkbook, readRobustWorkbook,
                hglMethodFromLabel };
  if(typeof window !== "undefined") window.__xlsxShapeReader = api;
  if(typeof module !== "undefined" && module.exports) module.exports = api;
})();
```

- [ ] **Step 3.5: Commit**

```bash
git add drainage-calculator/lib/xlsx-shape-reader.js \
        docs/template-analysis/test_shape_detect.py \
        docs/template-analysis/fixtures/build_robust_minimal.py \
        docs/template-analysis/fixtures/robust_minimal.xlsx
git commit -m "feat(reader): add xlsx-shape-reader skeleton + detectShape

Shape detection rule:
  STORM DRAIN COMPS + Outlet Structures → robust
  STORM DRAIN COMPS alone               → simple
  otherwise                             → unknown

Simple + Robust reader bodies are stubs, implemented in later tasks.
Spec 3 Phase 1 Task 3."
```

---

## Task 4: Simple reader — pipe-row ingestion

**Files:**
- Modify: `drainage-calculator/lib/xlsx-shape-reader.js`
- Create: `docs/template-analysis/test_simple_reader.py`

- [ ] **Step 4.1: Write the pipe-row test**

Create `docs/template-analysis/test_simple_reader.py`:

```python
"""Simple-shape reader round-trip tests."""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
WIP = HERE.parent / "template_wip_new.xlsx"
GOLDEN = HERE.parent / "template_golden.xlsx"


def read_simple_pipes_py(wb):
    """Mirror of readSimpleWorkbook's pipe-row loop in JS."""
    sdc = wb["STORM DRAIN COMPS"]
    pipes = []
    for r in range(10, 99):
        from_id = sdc[f"A{r}"].value
        to_id = sdc[f"B{r}"].value
        if from_id in (None, ""):
            continue
        pipes.append({
            "fromId": from_id,
            "toId": to_id,
            "size": sdc[f"N{r}"].value,
            "length": sdc[f"O{r}"].value,
            "usInvert": sdc[f"P{r}"].value,
            "dsInvert": sdc[f"Q{r}"].value,
            "angle": sdc[f"R{r}"].value,
            "n": sdc[f"S{r}"].value,
        })
    return pipes


def test_wip_has_populated_pipes():
    wb = openpyxl.load_workbook(WIP, data_only=True)
    pipes = read_simple_pipes_py(wb)
    assert len(pipes) >= 3, f"expected 3+ pipes, got {len(pipes)}"
    first = pipes[0]
    assert first["fromId"] not in (None, "")
    assert first["toId"] not in (None, "")


def test_wip_pipe_r_is_angle_not_manning():
    """Regression: col R is angle (Whole #), col S is Manning's n."""
    wb = openpyxl.load_workbook(WIP, data_only=True)
    pipes = read_simple_pipes_py(wb)
    for p in pipes:
        if p["angle"] is not None:
            assert isinstance(p["angle"], (int, float))
            if isinstance(p["angle"], float):
                assert p["angle"] == int(p["angle"]), (
                    f"Angle {p['angle']} should be whole; is R/S swapped?"
                )
        if p["n"] is not None:
            assert 0.005 <= p["n"] <= 0.03, (
                f"n={p['n']} out of range; is R/S swapped?"
            )
```

- [ ] **Step 4.2: Run the test — expect pass against existing WIP**

```bash
cd docs && pytest template-analysis/test_simple_reader.py -v
```

Expected: both tests pass.

- [ ] **Step 4.3: Fill in `readSimpleWorkbook` pipe-row ingestion**

In `drainage-calculator/lib/xlsx-shape-reader.js`, replace the `readSimpleWorkbook` stub with:

```javascript
function readSimpleWorkbook(wb){
  const sdc = wb.Sheets["STORM DRAIN COMPS"];
  if(!sdc) throw new Error("Missing STORM DRAIN COMPS sheet");

  const cell = (addr) => {
    const c = sdc[addr];
    if(!c) return "";
    return (c.v !== undefined && c.v !== null) ? c.v : "";
  };

  const pipes = [];
  for(let r = 10; r <= 98; r++){
    const fromId = cell("A"+r);
    if(fromId === "" || fromId == null) continue;
    pipes.push({
      fromId: String(fromId),
      toId: String(cell("B"+r)||""),
      size: cell("N"+r),
      length: cell("O"+r),
      usInvert: cell("P"+r),
      dsInvert: cell("Q"+r),
      angle: cell("R"+r),
      n: cell("S"+r),
      _structureType: cell("AA"+r),
      _rim: cell("AB"+r),
      _inflowAngle1: cell("AG"+r),
      _inflowAngle2: cell("AH"+r),
      _capturedQOverride: cell("AK"+r),
    });
  }

  const jurisdiction = cell("T3") || "MCDOT";
  const pipeStorm    = cell("H3") || "10yr";

  return {
    _shape: "simple",
    pipes,
    hydraulics: { jurisdiction, pipeStorm },
    structures: [],
    drainage: [],
    config: {},
  };
}
```

- [ ] **Step 4.4: Commit**

```bash
git add drainage-calculator/lib/xlsx-shape-reader.js \
        docs/template-analysis/test_simple_reader.py
git commit -m "feat(reader): Simple reader pipe-row ingestion

Reads STORM DRAIN COMPS rows 10-98 into pipes[]. Each row carries pipe
hydraulics (size, length, inverts, angle, n) plus structure metadata
attached to the FROM endpoint (type, rim, inflow angles, captured-Q
override). Column R is angle, S is Manning's n (regression-tested).
Spec 3 Phase 1 Task 4."
```

---

## Task 5: Simple reader — materialize structures from pipe rows

**Files:**
- Modify: `drainage-calculator/lib/xlsx-shape-reader.js`
- Modify: `docs/template-analysis/test_simple_reader.py`

- [ ] **Step 5.1: Extend the test with structure-materialization**

Append to `docs/template-analysis/test_simple_reader.py`:

```python
def materialize_structures_py(pipes):
    seen = {}
    for p in pipes:
        for sid in (p["fromId"], p["toId"]):
            if sid and sid not in seen:
                seen[sid] = {
                    "structureId": sid, "type": "manhole",
                    "rim": "", "capturedQOverride": "",
                }
    by_from = {p["fromId"]: p for p in pipes}
    for sid, s in seen.items():
        source = by_from.get(sid)
        if source:
            if source.get("_structureType"):
                s["type"] = str(source["_structureType"]).lower()
            if source.get("_rim") not in (None, ""):
                s["rim"] = source["_rim"]
            if source.get("_capturedQOverride") not in (None, ""):
                s["capturedQOverride"] = source["_capturedQOverride"]
    all_from = {p["fromId"] for p in pipes}
    for sid, s in seen.items():
        if sid not in all_from and s["type"] == "manhole":
            s["type"] = "outfall"
    return list(seen.values())


def test_structures_materialized_from_pipes():
    import openpyxl
    wb = openpyxl.load_workbook(WIP, data_only=True)
    pipes = read_simple_pipes_py(wb)
    sdc = wb["STORM DRAIN COMPS"]
    for p, r_idx in zip(pipes, (r for r in range(10, 99)
                               if sdc[f"A{r}"].value not in (None, ""))):
        p["_structureType"] = sdc[f"AA{r_idx}"].value
        p["_rim"] = sdc[f"AB{r_idx}"].value
        p["_capturedQOverride"] = sdc[f"AK{r_idx}"].value
    structs = materialize_structures_py(pipes)
    all_ids = {s["structureId"] for s in structs}
    all_pipe_ids = {p["fromId"] for p in pipes} | {p["toId"] for p in pipes}
    assert all_ids == all_pipe_ids - {"", None}
    outfalls = [s for s in structs if s["type"] == "outfall"]
    assert len(outfalls) >= 1
```

- [ ] **Step 5.2: Run the tests**

```bash
cd docs && pytest template-analysis/test_simple_reader.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5.3: Add structure materialization to `readSimpleWorkbook`**

In `readSimpleWorkbook`, before the `return`:

```javascript
  const seen = Object.create(null);
  for(const p of pipes){
    for(const sid of [p.fromId, p.toId]){
      if(sid && !seen[sid]){
        seen[sid] = {
          structureId: sid, type: "manhole", rim: "", capturedQOverride: "",
        };
      }
    }
  }
  const byFrom = Object.create(null);
  for(const p of pipes) byFrom[p.fromId] = p;
  for(const sid of Object.keys(seen)){
    const src = byFrom[sid];
    if(src){
      if(src._structureType) seen[sid].type = String(src._structureType).toLowerCase();
      if(src._rim !== "" && src._rim != null) seen[sid].rim = src._rim;
      if(src._capturedQOverride !== "" && src._capturedQOverride != null){
        seen[sid].capturedQOverride = src._capturedQOverride;
      }
    }
  }
  const allFrom = new Set(pipes.map(p => p.fromId));
  for(const sid of Object.keys(seen)){
    if(!allFrom.has(sid) && seen[sid].type === "manhole"){
      seen[sid].type = "outfall";
    }
  }
  const structures = Object.values(seen);
```

Update the `return` to include `structures`:

```javascript
  return {
    _shape: "simple",
    pipes, structures,
    hydraulics: { jurisdiction, pipeStorm },
    drainage: [], config: {},
  };
```

- [ ] **Step 5.4: Commit**

```bash
git add drainage-calculator/lib/xlsx-shape-reader.js \
        docs/template-analysis/test_simple_reader.py
git commit -m "feat(reader): Simple reader materializes structures from pipes

Three-pass derivation: collect unique fromId/toId, enrich from the pipe
row where A == structureId (type on AA, rim on AB, captured-Q override
on AK), promote terminal nodes to outfalls. Spec 3 Phase 1 Task 5."
```

---

## Task 6: Simple reader — drainage rows + Config toggles

**Files:**
- Modify: `drainage-calculator/lib/xlsx-shape-reader.js`
- Modify: `docs/template-analysis/test_simple_reader.py`

- [ ] **Step 6.1: Append the drainage-rows and Config-toggles test**

Append to `docs/template-analysis/test_simple_reader.py`:

```python
def test_cfactor_drainage_rows():
    import openpyxl
    wb = openpyxl.load_workbook(GOLDEN, data_only=True)
    cf = wb["C_FACTOR"]
    rows = []
    for r in range(6, 89):
        b = cf[f"B{r}"].value
        if b in (None, ""):
            continue
        rows.append({
            "structureId": b,
            "area": cf[f"C{r}"].value,
            "C": cf[f"M{r}"].value,
            "tc": cf[f"V{r}"].value,
        })
    assert isinstance(rows, list)


def test_config_toggles_golden():
    import openpyxl
    wb = openpyxl.load_workbook(GOLDEN, data_only=True)
    cfg = wb["Config"]
    assert cfg["B3"].value == "smaller-loss"
    assert cfg["B4"].value == "crown-plus-1ft"
    assert cfg["B5"].value == "HEC-22 EGL (d/s crown floor)"


def test_config_toggles_absent_in_wip():
    import openpyxl
    wb = openpyxl.load_workbook(WIP, data_only=True)
    assert "Config" not in wb.sheetnames, (
        "Legacy WIP must not carry a Config sheet (defaults apply)"
    )
```

- [ ] **Step 6.2: Run the tests**

```bash
cd docs && pytest template-analysis/test_simple_reader.py -v
```

Expected: 6 tests pass.

- [ ] **Step 6.3: Add drainage + config reading to `readSimpleWorkbook`**

In `readSimpleWorkbook`, after the structure-materialization and before the `return`:

```javascript
  const drainage = [];
  const cf = wb.Sheets["C_FACTOR"];
  if(cf){
    const cellCf = (addr) => {
      const c = cf[addr];
      if(!c) return "";
      return (c.v !== undefined && c.v !== null) ? c.v : "";
    };
    for(let r = 6; r <= 88; r++){
      const sid = cellCf("B"+r);
      if(sid === "" || sid == null) continue;
      drainage.push({
        structureId: String(sid),
        area: cellCf("C"+r),
        C:    cellCf("M"+r),
        tc:   cellCf("V"+r),
      });
    }
  }

  const config = {
    junctionAngleRule:   "smaller-loss",
    hglCrownCeilingRule: "crown-plus-1ft",
    hglMethod:           "HEC-22 EGL (d/s crown floor)",
    projectName:         "",
    templateShape:       "simple",
    contractVersion:     1,
  };
  const cfg = wb.Sheets["Config"];
  if(cfg){
    const cellCfg = (addr) => {
      const c = cfg[addr];
      if(!c) return "";
      return (c.v !== undefined && c.v !== null) ? c.v : "";
    };
    if(cellCfg("B1")) config.projectName         = String(cellCfg("B1"));
    if(cellCfg("B3")) config.junctionAngleRule   = String(cellCfg("B3"));
    if(cellCfg("B4")) config.hglCrownCeilingRule = String(cellCfg("B4"));
    if(cellCfg("B5")) config.hglMethod           = String(cellCfg("B5"));
    if(cellCfg("B6")) config.templateShape       = String(cellCfg("B6"));
    if(cellCfg("B7")) config.contractVersion     = Number(cellCfg("B7"));
  }
```

Update the `return`:

```javascript
  return {
    _shape: "simple",
    pipes, structures, drainage, config,
    hydraulics: { jurisdiction, pipeStorm },
  };
```

- [ ] **Step 6.4: Commit**

```bash
git add drainage-calculator/lib/xlsx-shape-reader.js \
        docs/template-analysis/test_simple_reader.py
git commit -m "feat(reader): Simple reader reads C_FACTOR + Config toggles

C_FACTOR rows 6-88 populate drainage[]. Config!B1-B7 populates config{}
when present (golden). Legacy WIP returns defaults. Spec 3 Phase 1 Task 6."
```

---

## Task 7: Wire Simple reader into calculator's `importExcel()`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`
- Modify: `drainage-calculator/build.js`

- [ ] **Step 7.1: Confirm build.js's inline pattern**

Open `drainage-calculator/build.js`. Note how it reads `lib/sheetjs-bundle.js` and inlines it. Extend to also inline `lib/xlsx-shape-reader.js`.

- [ ] **Step 7.2: Extend `build.js` to inline the shape reader**

Edit `drainage-calculator/build.js`. Find the sheetjs-inline block. Immediately below it, add:

```javascript
const shapeReaderSrc = fs.readFileSync(
  path.join(__dirname, "lib", "xlsx-shape-reader.js"), "utf8"
);
out = out.replace(
  /<!--\s*XLSX_SHAPE_READER_PLACEHOLDER\s*-->/,
  "<script>\n" + shapeReaderSrc + "\n</script>"
);
```

(`out` is the dev-HTML string variable in build.js. Adapt if build.js uses a different name.)

- [ ] **Step 7.3: Add the placeholder to the dev HTML**

Open `drainage-calculator/storm-drain-design-calculator-dev.html`. Find `<script src="lib/sheetjs-bundle.js"></script>` (or the inlined sheetjs block). Below it, add:

```html
<!-- XLSX_SHAPE_READER_PLACEHOLDER -->
<script src="lib/xlsx-shape-reader.js"></script>
```

- [ ] **Step 7.4: Dispatch inside `importExcel()`**

In the dev HTML, find `importExcel(file)` (around L6739). At the top of its `reader.onload` body, after `const wb = XLSX.read(data, {type:"array", cellFormula:false});`, insert:

```javascript
      const shape = window.__xlsxShapeReader.detectShape(wb);
      if(shape === "unknown"){
        toast("Couldn't detect template shape. This file should be a WIP "
              +"template, golden template, or calculator export.", true);
        return;
      }
      if(shape === "simple"){
        const simple = window.__xlsxShapeReader.readSimpleWorkbook(wb);
        applySimpleReaderResult(simple);
        state.exportShape = "simple";
        toast("Imported Simple template. Outlet structures, TR-55 "
              +"segments, and custom NOAA data were not in the file.");
        renderAll(); updateSavesUI();
        return;
      }
      // Fall through to the existing Robust-native read path.
```

- [ ] **Step 7.5: Add `applySimpleReaderResult()`**

Just above `function importExcel(file)`, add:

```javascript
function applySimpleReaderResult(simple){
  state.structures = simple.structures.map(s => ({
    id: nextId(), structureId: s.structureId, desc: "",
    type: s.type || "manhole", drainageAreaId: "",
    rim: s.rim === "" ? "" : s.rim,
    startElev: "", forceElev: false,
    splitMethod: "capacity", splitCapacity: "", splitRatio: 0.5,
    structureMode: "", agency: "", standardStructureId: "",
    structureCategory: "", shape: "", innerDiameter: "",
    innerWidth: "", innerLength: "",
  }));
  const idByLabel = {};
  state.structures.forEach(s => { idByLabel[s.structureId] = s.id; });
  state.pipes = simple.pipes.map(p => ({
    id: nextId(),
    fromStructureId: idByLabel[p.fromId] || "",
    toStructureId:   idByLabel[p.toId]   || "",
    angle: p.angle || 0,
    shape: "circular",
    size: p.size || "",
    n: (p.n === "" || p.n == null) ? 0.013 : p.n,
    material: "",
    upstreamInvert:   p.usInvert === "" ? "" : p.usInvert,
    downstreamInvert: p.dsInvert === "" ? "" : p.dsInvert,
    slope: "", length: p.length || "",
    splitRole: "",
  }));
  state.drainage = simple.drainage.map(d => ({
    id: nextId(), structureId: d.structureId,
    desc: "", area: d.area || "", C: d.C || "",
    iOverride: "", tc: d.tc || "", cf: 1,
    tcMethod: "direct",
    tr55: { segments: [] },
  }));
  state.outletStructures = [];
  state.outletDevices = [];
  state.activeOutletId = "";
  state.rainfall.customNoaa = {};
  state.rainfall.fetchedNoaa = null;
  state.hydraulics.junctionAngleRule   = simple.config.junctionAngleRule;
  state.hydraulics.hglCrownCeilingRule = simple.config.hglCrownCeilingRule;
  state.hydraulics.hglMethod = window.__xlsxShapeReader.hglMethodFromLabel(
    simple.config.hglMethod
  );
  if(simple.config.projectName) state.project = simple.config.projectName;
}
```

- [ ] **Step 7.6: Add `state.exportShape` to the default state**

Find the initial `state = {` object. Add:

```javascript
  exportShape: "robust", // "simple" | "robust"; see Task 15 UI toggle
```

- [ ] **Step 7.7: Build and test**

```bash
node drainage-calculator/build.js
```

Open the dev HTML. Click Import; choose `docs/template_wip_new_pre-repair.xlsx` (has 3-pipe sample). Expected: toast about Simple import; three pipes + four structures load.

Try again with `docs/template_golden.xlsx`. Expected: empty state (golden ships empty); toast appears; no errors.

- [ ] **Step 7.8: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html \
        drainage-calculator/storm-drain-design-calculator.html \
        drainage-calculator/build.js
git commit -m "feat(calculator): dispatch imports via shape reader

importExcel() now auto-detects Simple vs Robust. Simple branch maps
reader output onto state (clearing Robust-only fields) and flips the
exportShape toggle to 'simple'. Robust branch falls through to the
existing native-format reader. Spec 3 Phase 1 Task 7."
```

---

## Phase 1 ship gate

- [ ] Import `template_wip_new_pre-repair.xlsx` → 3 pipes + 4 structures load; Simple toast.
- [ ] Import `template_golden.xlsx` → empty state; Simple toast; no errors.
- [ ] Import a known-Robust file → falls through to existing Robust reader.
- [ ] Pytest green.

Pause for user review. Hand off to [`phase-2-robust-template.md`](phase-2-robust-template.md).
