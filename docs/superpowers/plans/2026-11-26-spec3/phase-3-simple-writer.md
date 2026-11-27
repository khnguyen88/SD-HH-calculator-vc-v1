# Spec 3 — Phase 3: Simple Writer + Toggle UI (Tasks 14–17)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Implement `buildSimpleWorkbook`, add the Simple/Robust export toggle UI, surface a lossy-export toast when Robust-only state is dropped, and remove `_legacyBuildWorkbook`.

**Spec:** `docs/superpowers/specs/2026-11-26-spec3-three-shape-bidirectional-design.md` §7

**Depends on:** Phase 2 complete (buildRobustWorkbook working; export dispatcher in place).

---

## Task 14: Implement `buildSimpleWorkbook`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`

- [ ] **Step 14.1: Replace the stub**

Find the Task 12 stub. Replace with:

```javascript
async function buildSimpleWorkbook(){
  const wb = await loadGoldenBase();
  const sdc = wb.Sheets["STORM DRAIN COMPS"];
  const cf  = wb.Sheets["C_FACTOR"];
  const cfg = wb.Sheets["Config"];

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

  state.drainage.forEach((d, i) => {
    const row = i + 6;
    if(row > 88) return;
    writeCell(cf, "B"+row, d.structureId, "s");
    writeCell(cf, "C"+row, d.area);
    writeCell(cf, "V"+row, d.tc);
  });

  writeCell(cfg, "B1", state.project || "", "s");
  writeCell(cfg, "B2", new Date().toISOString(), "s");
  writeCell(cfg, "B3", state.hydraulics.junctionAngleRule || "smaller-loss", "s");
  writeCell(cfg, "B4", state.hydraulics.hglCrownCeilingRule || "crown-plus-1ft", "s");
  writeCell(cfg, "B5",
    state.hydraulics.hglMethod === "conservative"
      ? "legacy both-end crown floor"
      : "HEC-22 EGL (d/s crown floor)", "s");
  writeCell(cfg, "B6", "simple", "s");
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

- [ ] **Step 14.2: Browser test**

Build and reload. Seed 2 pipes. In DevTools:

```javascript
state.exportShape = "simple";
exportExcel();
```

Open the downloaded file in Excel. Expected: 17 sheets (Simple layout), no Robust-only extras. STORM DRAIN COMPS rows 10-11 populated. `Config!B6` = "simple".

- [ ] **Step 14.3: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html \
        drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat(calculator): implement buildSimpleWorkbook

Writes SDC + C_FACTOR + Config!B1-B7 (B6='simple'). No Robust-only
sheets. Shares loadGoldenBase styling with buildRobustWorkbook.
Spec 3 Task 14."
```

---

## Task 15: Shape-toggle UI

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`

- [ ] **Step 15.1: Add the radio-button UI**

Find the top-bar HTML containing `<button id="exportBtn">`. Just after the button's closing tag, inject:

```html
<span class="export-shape-toggle" title="Choose export format">
  <label><input type="radio" name="exportShape" value="simple" id="exportShapeSimple"> Simple</label>
  <label><input type="radio" name="exportShape" value="robust" id="exportShapeRobust" checked> Robust</label>
</span>
```

- [ ] **Step 15.2: Style the toggle**

In the `<style>` block:

```css
.export-shape-toggle {
  display: inline-flex;
  gap: 0.6em;
  margin-left: 0.6em;
  font-size: 0.85em;
  color: var(--muted, #aaa);
}
.export-shape-toggle label { cursor: pointer; }
.export-shape-toggle input[type="radio"] { margin-right: 0.3em; }
@media (max-width: 720px) {
  .export-shape-toggle { display: none; }
}
```

- [ ] **Step 15.3: Lift `syncShapeRadio` to module scope**

Above `init()`:

```javascript
function syncShapeRadio(){
  const v = state.exportShape || "robust";
  document.querySelectorAll("input[name=exportShape]").forEach(r => {
    r.checked = (r.value === v);
  });
}
```

- [ ] **Step 15.4: Wire the radio buttons in `init()`**

Inside `init()`:

```javascript
  document.querySelectorAll("input[name=exportShape]").forEach(r => {
    r.addEventListener("change", () => {
      if(r.checked) state.exportShape = r.value;
    });
  });
  syncShapeRadio();
```

- [ ] **Step 15.5: Sync on import**

In the `importExcel` dispatch (added in Phase 1 Task 7.4), after the line `state.exportShape = "simple";` add `syncShapeRadio();`. Same after the Robust fall-through completes: `state.exportShape = "robust"; syncShapeRadio();`.

- [ ] **Step 15.6: Add hamburger-menu entries for mobile**

Find `<div id="mobileNavPanel">`. Add:

```html
<button class="mobile-nav-item" data-export-shape="simple">Export shape: Simple</button>
<button class="mobile-nav-item" data-export-shape="robust">Export shape: Robust</button>
```

In `init()`:

```javascript
  document.querySelectorAll("[data-export-shape]").forEach(btn => {
    btn.addEventListener("click", () => {
      state.exportShape = btn.dataset.exportShape;
      syncShapeRadio();
      closeMobileNav();
    });
  });
```

- [ ] **Step 15.7: Browser verification**

Build, reload. Expected: Simple/Robust radio pair visible next to Export. Click Simple, click Export. File downloads with `(simple)` in toast. Click Robust, click Export. File downloads with `(robust)`. Import a Simple file: radio flips to Simple.

- [ ] **Step 15.8: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html \
        drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat(ui): add shape toggle next to Export button

Radio pair (Simple | Robust) persists in state.exportShape. Default
Robust for new sessions; auto-flips to the shape of the last imported
file. Mobile: two buttons in the hamburger menu. Spec 3 Task 15."
```

---

## Task 16: Lossy-export toast + drop `_legacyBuildWorkbook`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`

- [ ] **Step 16.1: Emit the lossy toast on Simple export**

In `exportExcel()`, after the successful `XLSX.writeFile(...)`:

```javascript
    if(shape === "simple" && hasRobustState()){
      toast("Exported Simple template. Outlet structures, TR-55 segments, "
            +"custom NOAA data, and splitter settings are not stored in "
            +"this format — export as Robust to preserve them.");
    }
```

Add the helper above `exportExcel`:

```javascript
function hasRobustState(){
  return (state.outletStructures && state.outletStructures.length > 0)
      || (state.outletDevices && state.outletDevices.length > 0)
      || (state.rainfall && state.rainfall.fetchedNoaa)
      || state.drainage.some(d => d.tr55 && d.tr55.segments && d.tr55.segments.length > 0)
      || state.structures.some(s => s.type === "splitter"
                                    && (s.splitCapacity || s.splitRatio !== 0.5));
}
```

- [ ] **Step 16.2: Remove `_legacyBuildWorkbook`**

Delete `function _legacyBuildWorkbook(){...}`. Grep for any remaining references:

```bash
grep -n "_legacyBuildWorkbook\|setFormula\|setCellNum\|colLetter" drainage-calculator/storm-drain-design-calculator-dev.html
```

Only remove helpers (`setFormula`, `setCellNum`, `colLetter`) that are now truly orphaned. If any are still used by `buildRobustWorkbook`, leave them.

```bash
node drainage-calculator/build.js
```

Expected: build completes with no errors.

- [ ] **Step 16.3: Ship-gate verification matrix**

| Action | Expected |
|---|---|
| Import `template_wip_new_pre-repair.xlsx` | 3 pipes load. Toggle flips to Simple. |
| Export (Simple) | `.xlsx` ~250 KB with 17 sheets. Opens cleanly. |
| Add Outlet Structure, Export (Simple) | Lossy toast appears. File has no Outlet Structures sheet. |
| Toggle to Robust, Export | `.xlsx` with 17+ Robust sheets. Opens cleanly. |
| Re-import Robust file | Toggle flips to Robust. Outlet work restored. |

- [ ] **Step 16.4: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html \
        drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat(calculator): lossy-export toast + drop legacy writer

Simple export emits a lossy-conversion warning when state carries
Robust-only data. Legacy buildWorkbook removed. Spec 3 Phase 3 ship
gate."
```

---

## Task 17: Phase 3 wrap

- [ ] Manual sign-off that Phases 1–3 together deliver a working bidirectional calculator.

Hand off to [`phase-4-hgl-wiring.md`](phase-4-hgl-wiring.md).
