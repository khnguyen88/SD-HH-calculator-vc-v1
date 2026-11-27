# Spec 3 — Phase 2: Robust Template Rebuild (Tasks 8–13)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Rebuild the calculator's native xlsx export so it uses the golden template as a styled base, writes Simple-shape inputs on top, and appends four Robust-only sheets. Visual parity with the Simple template.

**Spec:** `docs/superpowers/specs/2026-11-26-spec3-three-shape-bidirectional-design.md` §6

**Depends on:** Phase 1 complete (Simple reader working).

---

## Task 8: Embed `template_golden.xlsx` as base64 in build.js output

**Files:**
- Modify: `drainage-calculator/build.js`
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`

- [ ] **Step 8.1: Add base64 embed to build.js**

In `drainage-calculator/build.js`, after the shape-reader inline block:

```javascript
const goldenBytes = fs.readFileSync(
  path.join(__dirname, "..", "docs", "template_golden.xlsx")
);
const goldenB64 = goldenBytes.toString("base64");
out = out.replace(
  /<!--\s*TEMPLATE_GOLDEN_B64_PLACEHOLDER\s*-->/,
  "<script>window.__TEMPLATE_GOLDEN_B64 = \"" + goldenB64 + "\";</script>"
);
```

- [ ] **Step 8.2: Add placeholder + dev-mode fetch**

In the dev HTML, immediately after the `XLSX_SHAPE_READER_PLACEHOLDER` block:

```html
<!-- TEMPLATE_GOLDEN_B64_PLACEHOLDER -->
<script>
if(!window.__TEMPLATE_GOLDEN_B64){
  window.__TEMPLATE_GOLDEN_B64_PENDING = fetch("../docs/template_golden.xlsx")
    .then(r => r.arrayBuffer())
    .then(buf => {
      const bytes = new Uint8Array(buf);
      let bin = "";
      for(let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
      window.__TEMPLATE_GOLDEN_B64 = btoa(bin);
    });
}
</script>
```

- [ ] **Step 8.3: Build + verify file-size increase**

```bash
node drainage-calculator/build.js
ls -la drainage-calculator/storm-drain-design-calculator.html
```

Expected: file size grew by ~335 KB.

- [ ] **Step 8.4: Commit**

```bash
git add drainage-calculator/build.js \
        drainage-calculator/storm-drain-design-calculator-dev.html \
        drainage-calculator/storm-drain-design-calculator.html
git commit -m "build(calculator): embed template_golden.xlsx as base64

Golden template bytes inlined so buildSimpleWorkbook and
buildRobustWorkbook can load it as a styled base. Dev mode fetches from
disk; prod inlines. File size +~335 KB. Spec 3 Task 8."
```

---

## Task 9: `loadGoldenBase()` helper

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`

- [ ] **Step 9.1: Add `loadGoldenBase` above `buildWorkbook`**

```javascript
async function loadGoldenBase(){
  if(window.__TEMPLATE_GOLDEN_B64_PENDING){
    await window.__TEMPLATE_GOLDEN_B64_PENDING;
  }
  const b64 = window.__TEMPLATE_GOLDEN_B64;
  if(!b64) throw new Error("Golden template base64 not loaded");
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for(let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return XLSX.read(bytes, {type:"array", cellStyles:true, cellFormula:true, cellDates:true});
}
```

- [ ] **Step 9.2: Browser smoke test**

In DevTools:

```javascript
loadGoldenBase().then(wb => {
  console.log("sheets:", wb.SheetNames);
  console.log("Config B3:", wb.Sheets.Config.B3);
  console.log("named ranges:", wb.Workbook && wb.Workbook.Names);
});
```

Expected: logs 17 sheet names, `Config.B3` shows `{t:"s", v:"smaller-loss"}`, named ranges include `junctionAngleRule`.

- [ ] **Step 9.3: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html \
        drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat(calculator): add loadGoldenBase() helper

Loads the embedded golden-template base64 as a SheetJS workbook with
styling + formulas preserved. Used as the base for buildSimple /
buildRobust. Spec 3 Task 9."
```

---

## Task 10: `buildRobustWorkbook` — fill Simple surface into golden base

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`

- [ ] **Step 10.1: Add `buildRobustWorkbook` scaffold**

Below `loadGoldenBase`:

```javascript
async function buildRobustWorkbook(){
  const wb = await loadGoldenBase();
  const sdc = wb.Sheets["STORM DRAIN COMPS"];

  const writeCell = (ws, addr, value, t) => {
    if(value === "" || value == null) return;
    ws[addr] = { t: t || "n", v: value };
  };

  state.pipes.forEach((p, i) => {
    const row = i + 10;
    if(row > 98) return;
    const fromLabel = (findStructure(p.fromStructureId)||{}).structureId
                      || p.fromStructureId || "";
    const toLabel = (findStructure(p.toStructureId)||{}).structureId
                      || p.toStructureId || "";
    writeCell(sdc, "A"+row, fromLabel, "s");
    writeCell(sdc, "B"+row, toLabel, "s");
    writeCell(sdc, "N"+row, parseFloat(p.size) || "", "n");
    writeCell(sdc, "O"+row, p.length);
    writeCell(sdc, "P"+row, p.upstreamInvert);
    writeCell(sdc, "Q"+row, p.downstreamInvert);
    writeCell(sdc, "R"+row, p.angle);
    writeCell(sdc, "S"+row, pipeEffectiveN(p));
    const s = findStructure(p.fromStructureId);
    if(s){
      writeCell(sdc, "AA"+row, (s.type||"manhole"), "s");
      writeCell(sdc, "AB"+row, s.rim);
      const calc = computeStructureCalc(s.id);
      if(calc && calc.captured){
        writeCell(sdc, "AK"+row, round(calc.captured, 4));
      }
    }
  });

  const cf = wb.Sheets["C_FACTOR"];
  state.drainage.forEach((d, i) => {
    const row = i + 6;
    if(row > 88) return;
    writeCell(cf, "B"+row, d.structureId, "s");
    writeCell(cf, "C"+row, d.area);
    writeCell(cf, "V"+row, d.tc);
  });

  const cfg = wb.Sheets.Config;
  writeCell(cfg, "B1", state.project || "", "s");
  writeCell(cfg, "B2", new Date().toISOString(), "s");
  writeCell(cfg, "B3", state.hydraulics.junctionAngleRule || "smaller-loss", "s");
  writeCell(cfg, "B4", state.hydraulics.hglCrownCeilingRule || "crown-plus-1ft", "s");
  writeCell(cfg, "B5",
    state.hydraulics.hglMethod === "conservative"
      ? "legacy both-end crown floor"
      : "HEC-22 EGL (d/s crown floor)", "s");
  writeCell(cfg, "B6", "robust", "s");
  writeCell(cfg, "B7", 2, "n");

  if(state.hydraulics.jurisdiction){
    writeCell(sdc, "T3", state.hydraulics.jurisdiction, "s");
  }
  if(state.rainfall && state.rainfall.pipeStorm){
    writeCell(sdc, "H3", state.rainfall.pipeStorm, "s");
  }

  return wb;
}
```

- [ ] **Step 10.2: Browser test**

Seed one pipe in UI. In DevTools:

```javascript
buildRobustWorkbook().then(wb => {
  console.log("A10:", wb.Sheets["STORM DRAIN COMPS"].A10);
  console.log("Config B6:", wb.Sheets.Config.B6);
});
```

Expected: A10 shows the fromId; Config B6 = "robust".

- [ ] **Step 10.3: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html \
        drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat(calculator): buildRobustWorkbook fills Simple surface

Loads golden base, writes pipe rows to STORM DRAIN COMPS cols A/B/N/O/
P/Q/R/S/AA/AB/AK, drainage rows to C_FACTOR cols B/C/V, Config B1-B7
including the robust shape marker. Spec 3 Task 10."
```

---

## Task 11: `buildRobustWorkbook` — append Robust-only sheets

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`

- [ ] **Step 11.1: Capture style tokens**

In `buildRobustWorkbook`, after `const wb = await loadGoldenBase();`:

```javascript
  const headerStyle = (sdc["A8"] && sdc["A8"].s) ? sdc["A8"].s : undefined;
```

- [ ] **Step 11.2: Append the TR-55 Segments sheet**

Before `return wb`:

```javascript
  const tr55Header = ["Drainage Area","Order","Type","n","L (ft)","s (ft/ft)",
                      "P2 (in)","Surface","Area a (sf)","Wetted Perimeter Pw (ft)"];
  const tr55Rows = [tr55Header];
  state.drainage.forEach(r => {
    const segs = (r.tr55 && r.tr55.segments) || [];
    segs.forEach((seg, i) => {
      tr55Rows.push([
        r.structureId || "", i+1, seg.type,
        (seg.type==="sheet"||seg.type==="channel") ? (seg.n||"") : "",
        seg.L||"", seg.s||"",
        seg.type==="sheet" ? (seg.P2||"") : "",
        seg.type==="shallow" ? (seg.surface||"unpaved") : "",
        seg.type==="channel" ? (seg.area||"") : "",
        seg.type==="channel" ? (seg.wp||"") : "",
      ]);
    });
  });
  const wsTr55 = XLSX.utils.aoa_to_sheet(tr55Rows);
  wsTr55["!cols"] = [{wch:14},{wch:8},{wch:10},{wch:9},{wch:9},
                     {wch:11},{wch:9},{wch:14},{wch:11},{wch:15}];
  if(headerStyle){
    for(let c = 0; c < tr55Header.length; c++){
      const addr = XLSX.utils.encode_cell({r:0, c});
      if(wsTr55[addr]) wsTr55[addr].s = headerStyle;
    }
  }
  XLSX.utils.book_append_sheet(wb, wsTr55, "TR-55 Segments");
```

- [ ] **Step 11.3: Append Outlet Structures + Outlet Devices**

```javascript
  const osHeader = ["Outlet Structure ID","Label","Description","Precision Mode",
    "Start Elevation (ft)","End Elevation (ft)","Coarse Increment (ft)",
    "Fine Increment (ft)","Fine Band +/- (ft)","Tailwater Mode",
    "Tailwater Fixed Elevation (ft)","Tailwater Linked Structure ID"];
  const osAoa = [osHeader];
  state.outletStructures.forEach(os => {
    osAoa.push([
      os.label||os.id, os.label||"", os.desc||"", os.precisionMode||"uniform",
      os.startElev, os.endElev, os.coarseIncrement||0.5,
      os.fineIncrement||0.05, os.fineBand||0.3,
      os.twMode||"none",
      (os.twFixed===""||os.twFixed==null)?"":os.twFixed,
      os.twStructureId ? ((findStructure(os.twStructureId)||{}).structureId||"") : "",
    ]);
  });
  const wsOs = XLSX.utils.aoa_to_sheet(osAoa);
  wsOs["!cols"] = [{wch:20},{wch:20},{wch:26},{wch:13},{wch:12},
                   {wch:12},{wch:12},{wch:12},{wch:12},{wch:12},
                   {wch:14},{wch:18}];
  if(headerStyle){
    for(let c = 0; c < osHeader.length; c++){
      const addr = XLSX.utils.encode_cell({r:0, c});
      if(wsOs[addr]) wsOs[addr].s = headerStyle;
    }
  }
  XLSX.utils.book_append_sheet(wb, wsOs, "Outlet Structures");

  const devHeader = ["Device ID","Outlet Structure","Label","Type","Invert (ft)",
    "Crest (ft)","Diameter (in)","Diameter Unit","Length (ft)","Length Unit",
    "Weir Shape","Notch Angle (deg)","Coefficient","Fine Override Enabled",
    "Fine Increment Override (ft)","Fine Band Override (ft)","Notes"];
  const devAoa = [devHeader];
  state.outletDevices.forEach(d => {
    const osLabel = ((findOutletStructure(d.outletStructureId)||{}).label) || "";
    devAoa.push([
      d.id, osLabel, d.label||"", d.type,
      d.type!=="weir" ? d.invert : "",
      d.type==="weir" ? d.crest : "",
      d.type!=="weir" ? d.diameter : "",
      d.type!=="weir" ? (d.diameterUnit||"in") : "",
      d.type==="weir" ? d.length : "",
      d.type==="weir" ? (d.lengthUnit||"ft") : "",
      d.type==="weir" ? (d.weirShape||"rect") : "",
      (d.type==="weir" && d.weirShape==="vnotch") ? (d.notchAngle||90) : "",
      d.type==="weir" ? d.coef : d.cd,
      d.fineOverrideEnabled ? "TRUE" : "FALSE",
      (d.fineIncrementOverride===""||d.fineIncrementOverride==null)?"":d.fineIncrementOverride,
      (d.fineBandOverride===""||d.fineBandOverride==null)?"":d.fineBandOverride,
      d.notes||"",
    ]);
  });
  const wsDev = XLSX.utils.aoa_to_sheet(devAoa);
  wsDev["!cols"] = [{wch:10},{wch:20},{wch:18},{wch:10},{wch:10},
                    {wch:10},{wch:12},{wch:9},{wch:10},{wch:9},
                    {wch:10},{wch:12},{wch:11},{wch:13},{wch:14},
                    {wch:14},{wch:26}];
  if(headerStyle){
    for(let c = 0; c < devHeader.length; c++){
      const addr = XLSX.utils.encode_cell({r:0, c});
      if(wsDev[addr]) wsDev[addr].s = headerStyle;
    }
  }
  XLSX.utils.book_append_sheet(wb, wsDev, "Outlet Devices");
```

- [ ] **Step 11.4: Append per-facility Rating sheets + Rainfall Settings**

Reuse the existing `safeSheetName` helper and the rating-curve builder from the current `buildWorkbook` function. Copy the rating-sheet loop (L6386–L6468 in the current dev HTML) and the Rainfall Settings block (L6125–L6158) verbatim into `buildRobustWorkbook`, applying `headerStyle` to the header row of each new sheet.

**Why copy, not call:** `buildWorkbook` is being replaced in Task 12; keeping a single owner of the write logic simplifies the diff.

- [ ] **Step 11.5: Manual Excel verification**

Build (`node drainage-calculator/build.js`), reload. Seed 2 pipes + 1 outlet structure + 1 device. In DevTools:

```javascript
buildRobustWorkbook().then(wb => XLSX.writeFile(wb, "test-robust.xlsx", {bookSST:true}));
```

Open the downloaded file. Verify:
- 17+ sheet tabs.
- STORM DRAIN COMPS rows 10-11 populated.
- Outlet Structures, Outlet Devices, TR-55 Segments, Rainfall Settings populated.
- Row-1 header cells on Robust-only sheets match SDC row 8 styling.
- No repair prompt.

- [ ] **Step 11.6: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html \
        drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat(calculator): buildRobustWorkbook appends Robust-only sheets

TR-55 Segments, Outlet Structures, Outlet Devices, per-facility Rating
curves, Rainfall Settings. Header rows inherit SDC row-8 style for
visual parity with Simple sheets. Spec 3 Task 11."
```

---

## Task 12: Dispatch exports via shape toggle

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`

- [ ] **Step 12.1: Rename `buildWorkbook` → `_legacyBuildWorkbook`**

Find `function buildWorkbook(){` (around L6082). Rename to `function _legacyBuildWorkbook(){`.

- [ ] **Step 12.2: Replace `exportExcel`**

Find `function exportExcel()` (around L6530). Replace body:

```javascript
async function exportExcel(){
  try{
    const shape = state.exportShape || "robust";
    let wb;
    if(shape === "simple"){
      wb = await buildSimpleWorkbook();
    } else {
      wb = await buildRobustWorkbook();
    }
    const name = (state.project||"storm-drain-project")
      .replace(/[^a-z0-9\-_ ]/gi,"").trim()
      .replace(/\s+/g,"-") || "storm-drain-project";
    XLSX.writeFile(wb, name + ".xlsx", { bookSST: true });
    toast("Exported <b>"+escapeHtml(name)+".xlsx</b> ("+shape+")");
  }catch(err){
    console.error(err);
    toast("Export failed: "+escapeHtml(err.message), true);
  }
}
```

- [ ] **Step 12.3: Add temporary `buildSimpleWorkbook` stub**

Above `exportExcel`:

```javascript
async function buildSimpleWorkbook(){
  throw new Error("Simple writer not yet implemented (Phase 3 Task 14)");
}
```

- [ ] **Step 12.4: Manual verification**

Build, reload. Default `state.exportShape = "robust"`. Click Export. Expected: same successful Robust export as Task 11; toast reads `"Exported ... (robust)"`.

- [ ] **Step 12.5: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html \
        drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat(calculator): dispatch exports via shape toggle

exportExcel() routes to buildRobustWorkbook or buildSimpleWorkbook
based on state.exportShape. Legacy buildWorkbook kept as
_legacyBuildWorkbook during Phase 2. Spec 3 Task 12."
```

---

## Task 13: Robust writer round-trip test + ship gate

**Files:**
- Create: `docs/template-analysis/test_robust_writer.py`
- Create: `docs/template-analysis/fixtures/robust_roundtrip.xlsx`

- [ ] **Step 13.1: Write the round-trip test**

Create `docs/template-analysis/test_robust_writer.py`:

```python
"""Confirm a Robust-shape xlsx produced by the calculator opens cleanly
and carries the expected structure."""
from pathlib import Path
import openpyxl
import pytest

FIXTURE = (Path(__file__).parent / "fixtures" / "robust_roundtrip.xlsx")


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Create fixtures/robust_roundtrip.xlsx by "
                           "manually exporting Robust from the calculator")
def test_robust_has_simple_sheets():
    wb = openpyxl.load_workbook(FIXTURE, data_only=False)
    for name in ("STORM DRAIN COMPS", "HGL", "C_FACTOR", "Config"):
        assert name in wb.sheetnames, f"Robust missing {name}"


@pytest.mark.skipif(not FIXTURE.exists(), reason="see fixture setup")
def test_robust_has_robust_only_sheets():
    wb = openpyxl.load_workbook(FIXTURE, data_only=False)
    for name in ("Outlet Structures", "Outlet Devices", "TR-55 Segments",
                 "Rainfall Settings"):
        assert name in wb.sheetnames, f"Robust missing {name}"


@pytest.mark.skipif(not FIXTURE.exists(), reason="see fixture setup")
def test_robust_config_marker():
    wb = openpyxl.load_workbook(FIXTURE, data_only=False)
    assert wb["Config"]["B6"].value == "robust"
    assert wb["Config"]["B7"].value == 2
```

- [ ] **Step 13.2: Produce the fixture manually**

Open the calculator. Import `docs/template_wip_new_pre-repair.xlsx` to seed the 3-pipe sample. In DevTools: `state.exportShape = "robust"; exportExcel();`. Save the downloaded file to `docs/template-analysis/fixtures/robust_roundtrip.xlsx`.

- [ ] **Step 13.3: Run the test**

```bash
cd docs && pytest template-analysis/test_robust_writer.py -v
```

Expected: 3 tests pass.

- [ ] **Step 13.4: Ship gate — manual Excel verification**

Open `robust_roundtrip.xlsx` in Excel 365:
1. Opens cleanly, no repair prompts.
2. HGL + print sheets populate without manual refresh.
3. Visual styling of Robust-only sheet headers matches SDC row 8.
4. `Config!B6` = `robust`, `B7` = `2`.
5. Re-import into the calculator — Robust detection triggers (STORM DRAIN COMPS + Outlet Structures); existing native reader loads extras.

- [ ] **Step 13.5: Commit**

```bash
git add docs/template-analysis/test_robust_writer.py \
        docs/template-analysis/fixtures/robust_roundtrip.xlsx
git commit -m "test(robust): round-trip fixture + shape-tag assertions

Phase 2 ship gate. Fixture is a Robust export seeded from the pre-repair
3-pipe sample. Spec 3 Task 13."
```

---

## Phase 2 ship gate

- [ ] Robust export opens cleanly in Excel.
- [ ] HGL + print sheets auto-populate (iterate=True from Spec 2).
- [ ] Robust-only sheets styled consistently with Simple sheets.
- [ ] Round-trip: Robust export → re-import → extras restored.
- [ ] Pytest green.

Pause for user review. Hand off to [`phase-3-simple-writer.md`](phase-3-simple-writer.md).
