# Spec 4 — Legacy Native xlsx Migration

- **Date:** 2026-11-27
- **Status:** Finalized (Option A chosen autonomously per user instruction after Spec 3 ship-gate).
- **Follow-up to:** Spec 3 verification checklist §7.1.

## Goal

Extend `detectShape` + the shared reader to recognize pre-Spec-3 calculator native xlsx files (sheets `Pipe Sizing` + `Junction Structure` + `Drainage Area`, no `STORM DRAIN COMPS`) and route them through the same state-apply path as Robust files. Users with old exports can import directly; no manual migration needed.

Secondary benefit: fixes 9 of 14 visualizer JS test failures that use `main-app-export.xlsx` fixture (pre-Spec-3 shape).

## Non-goals

- No change to Simple/Robust detection or reader.
- No new xlsx writer for legacy shape (export stays Simple | Robust).
- No Contract-Version bump — this is a read-side extension only.

## Design

### Detection

Third branch added to `detectShape`:

```
1. STORM DRAIN COMPS present:
   a. + Outlet Structures          → "robust"
   b. else                          → "simple"
2. Pipe Sizing + Junction Structure → "legacy-native"
3. else                              → "unknown"
```

### Reader

`readLegacyNativeWorkbook(wb)` parses the pre-Spec-3 sheet layout (documented in `docs/superpowers/notes/2026-11-26-spec3-shape1-audit.md`) and returns an object with the **same shape** as `readRobustWorkbook`:

```
{ _shape: "legacy-native",
  pipes[], structures[], drainage[], config,
  tr55Segments[], outletStructures[], outletDevices[], rainfallSettings,
  hydraulics: { jurisdiction, pipeStorm } }
```

Field-level map (shortened — see audit for full column catalog):

| Source | Target |
|---|---|
| `Pipe Sizing!B` | `pipe.fromId` |
| `Pipe Sizing!C` | `pipe.toId` |
| `Pipe Sizing!D` | `pipe.angle` |
| `Pipe Sizing!F` | `pipe.size` |
| `Pipe Sizing!G` | `pipe.n` |
| `Pipe Sizing!H` / `I` | `pipe.usInvert` / `dsInvert` |
| `Pipe Sizing!K` | `pipe.length` |
| `Pipe Sizing!Q` | `pipe.splitRole` (preserved as `_splitRole`) |
| `Junction Structure!A` | `structure.structureId` |
| `Junction Structure!D` | `structure.type` |
| `Junction Structure!F` | `structure.startElev` |
| `Junction Structure!H` | `structure.rim` |
| `Drainage Area!A` | `drainage.structureId` |
| `Drainage Area!C` | `drainage.area` |
| `Drainage Area!D` | `drainage.C` |
| `Drainage Area!G` | `drainage.tc` |
| `Overview!B2` | `config.projectName` |
| `Rainfall Settings!B6` ("HGL Method") | `config.hglMethod` |

Config toggles (`junctionAngleRule`, `hglCrownCeilingRule`) default to Simple values (pre-Spec-3 files predate the toggles).

### Apply

**No new `applyLegacyNativeReaderResult` function.** The output shape matches `readRobustWorkbook` output, so the existing `applyRobustReaderResult` handles it unchanged. Dispatch in `importExcel` just calls `readLegacyNativeWorkbook(wb)` → `applyRobustReaderResult(result)` → `state.exportShape = "robust"` (nudging the user toward the new format on re-export).

### Visualizer

Same dispatch extension in the visualizer's `importFromXlsxFile`. Reuses the existing state-apply glue.

## Plan

### Task 4.1 — Add legacy detection + reader

**Files:**
- Modify `drainage-calculator/lib/xlsx-shape-reader.js`.

Extend `detectShape` with the third branch. Add `readLegacyNativeWorkbook(wb)` body. Export it in the api object.

### Task 4.2 — Wire into calculator import dispatch

**Files:**
- Modify `drainage-calculator/storm-drain-design-calculator-dev.html`.

In `importExcel`, add a `shape === "legacy-native"` branch that calls `readLegacyNativeWorkbook` + `applyRobustReaderResult` + sets `state.exportShape = "robust"` + toast: `"Imported legacy native format. Re-export as Robust to upgrade to the current layout."`.

### Task 4.3 — Wire into visualizer

**Files:**
- Modify `visualizer/storm-drain-visualizer-dev.html`.

Extend the Spec-3 dispatch block added in Task 22 with a `"legacy-native"` case (same reader call).

### Task 4.4 — Rebuild + test

Run `node drainage-calculator/build.js` and `node visualizer/build-visualizer.js`. Confirm:
- Existing pytest suite still 82 passed / 6 skipped.
- Visualizer `npm test` previously 123 pass / 14 fail; expect 9+ of the 14 to now pass (9 legacy-shape tests). The 5 hash-import harness failures are handled by Spec 5.

### Task 4.5 — Commit

One commit with message referencing Spec 4.

## Known risks

- The pre-Spec-3 column letters depend on the audit being accurate. Spot-check against `main-app-export.xlsx` fixture (which is itself a pre-Spec-3 export) via openpyxl before finalizing column mappings.
- `Drainage Area` ID column is called `ID` in pre-Spec-3 exports (per the audit) — maps to `structureId` field on the state side.
