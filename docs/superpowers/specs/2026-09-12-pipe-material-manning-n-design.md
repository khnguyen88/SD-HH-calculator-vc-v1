# Pipe Material Manning's n Table — Design Spec

**Date:** 2026-09-12
**Scope:** Add an editable Manning's n pipe-material reference table (new tab), wire a Material dropdown into the Pipe Sizing & Capacity table so selecting a material locks `n` to the table value, and replace all raw `row.n` reads in calculations with a `pipeEffectiveN(row)` helper.

---

## 1. State and Data Model

### 1.1 New state array

```js
state.pipeMaterials = [
  { id: 1, label: "RCP (Reinforced Concrete Pipe)",  n: 0.013 },
  { id: 2, label: "CMP (Corrugated Metal Pipe)",      n: 0.024 },
  { id: 3, label: "CMP w/ Paved Invert",              n: 0.018 },
  { id: 4, label: "HDPE — smooth interior",           n: 0.012 },
  { id: 5, label: "HDPE — corrugated",                n: 0.025 },
  { id: 6, label: "PVC",                              n: 0.011 },
  { id: 7, label: "CPEP",                             n: 0.011 },
  { id: 8, label: "Ductile Iron Pipe",                n: 0.013 },
  { id: 9, label: "Steel Pipe",                       n: 0.012 },
]
```

Values are general industry-standard starting points (AASHTO/HEC-22 style), not pulled from a specific MDSHA or county document. The table is fully editable and resettable so engineers can adjust to their jurisdiction's design manual.

### 1.2 New pipe row field

Each pipe row gains `material: ""` (empty string = no material selected, manual n entry). When non-empty it stores the material's numeric `id`.

Default for new pipe rows: `material: ""`, `n: 0.013` (unchanged from current default).

### 1.3 `pipeEffectiveN(row)` helper

```js
function pipeEffectiveN(row) {
  if (row.material) {
    const mat = state.pipeMaterials.find(m => m.id === row.material);
    if (mat) return parseFloat(mat.n) || 0;
  }
  return parseFloat(row.n) || 0;
}
```

This is the **single source of truth** for Manning's n in all pipe calculations. Every place that currently reads `parseFloat(row.n)` or `parseFloat(pipe.n)` is replaced with `pipeEffectiveN(row/pipe)`. Because it does a live lookup, editing a material's n in the reference table propagates immediately to all pipes using that material on the next render — no per-row sync needed. If `row.material` is set but the id is not found in `state.pipeMaterials` (e.g. the row was deleted), the function falls back to `parseFloat(row.n)` — no crash, no NaN.

### 1.4 Locations to update

All uses of raw `row.n` / `pipe.n` in:
- `calcPipeRow()` — Manning's full-flow capacity
- `manningFullFlow()` call sites in `renderPipeSizing25()`
- `frictionSlope()` / HGL elevation propagation
- `buildPipeSheet()` — detail sheet
- `buildPipesDetailSheet()` — 25-yr detail sheet
- `buildFormulasSheet()` — Formulas & Examples worked example
- Excel export (pipe AOA sheet) — export effective n, not raw `row.n`

---

## 2. Manning's n (Pipe Materials) Tab

### 2.1 Tab registration

Added to `getTabs()` between "Table 4-6 Reference" and "Kb Coefficients":

```js
{ id: "pipe-n", label: "Manning's n (Pipe)" }
```

A corresponding `<div class="view" id="view-pipe-n"></div>` is added to the HTML alongside the other view divs.

### 2.2 Tab content (`renderPipeN()`)

Matches the Kb Coefficients tab pattern:

- Short description note: "General industry-standard Manning's n values. Edit to match your governing agency's design manual. Changes apply immediately to all pipes using that material."
- `+ Add row` button — appends `{ id: nextId(), label: "", n: "" }` to `state.pipeMaterials`
- `Reset to default` button — restores the 9-row seed above, calls `renderAll()`
- Editable two-column table: **Pipe Material** (text input, ~250 px) | **Manning's n** (number input, ~80 px)
- Each row has a delete button
- Every cell has a stable `data-focus-key`: `"pipe-n:" + row.id + ":" + field`
- All inputs route through `withFocusPreserved(renderAll)`

### 2.3 State persistence

`state.pipeMaterials` is included in localStorage snapshots and Excel export/import alongside other state arrays. The `defaultPipeMaterials()` function returns the 9-row seed and is called in state initialisation.

---

## 3. Pipe Sizing & Capacity Table Changes

### 3.1 New Material column

A "Material" dropdown column is inserted immediately **before** the existing "n" column in both the primary Pipe Sizing tab (`renderPipes()`) and the 25-yr tab (`renderPipeSizing25()`).

Dropdown options:
1. `""` → "— (manual)" (first option, selected by default)
2. One option per `state.pipeMaterials` row: value = `mat.id`, label = `mat.label`

`onchange`: sets `row.material` to the selected id (or `""` for manual), calls `withFocusPreserved(renderAll)`.

`data-focus-key`: `"pipes:" + row.id + ":material"`

### 3.2 n cell — locked vs. editable

| `row.material` | n cell renders as |
|---|---|
| `""` (manual) | Normal editable number input (existing behaviour) |
| Any material id | Read-only computed display showing `pipeEffectiveN(row)` to 3 decimal places, styled like other computed cells (dimmed, no input) |

The column header remains **n** — no rename.

### 3.3 Detail sheet

The detail sheet (`buildPipeSheet()`) reports:
- "Material" row: material label (or "Manual" if none)
- "Manning's n" row: `pipeEffectiveN(row)` (not raw `row.n`)

### 3.4 Excel export

The pipe AOA sheet exports `pipeEffectiveN(pipe)` in the n column, not `row.n`. No separate material-label column is added to the export — the effective numeric n is sufficient for the engineering record.

---

## 4. Out of Scope

- No per-pipe n override while a material is selected (locked by design).
- No material assignment to TR-55 channel segments (those use open-channel n, a separate concept).
- No automatic material inference from existing pipe rows on import (imported rows without a material field get `material: ""`).
