# Pipe Inverts & Computed Slope — Design Spec

**Date:** 2026-09-11
**Feature:** Add upstream/downstream invert inputs to pipes; auto-compute slope from inverts; display inverts in HGL tab.

---

## Problem

Pipe slope is currently a single manually-entered field. Engineers typically work from pipe invert elevations (set by grade or existing conditions), and computing slope from inverts by hand is error-prone. The HGL tab also has no way to cross-reference pipe inverts against the computed HGL without switching tabs.

---

## Scope

- `drainage-calculator/storm-drain-design-calculator.html` only (single-file rule).
- No new tabs, no new sections — additive changes to existing Pipe Sizing and HGL tabs.

---

## Data Model

Two new fields on every pipe state object:

```js
{
  id, fromStructureId, toStructureId, angle, shape, size, n,
  upstreamInvert: "",    // NEW — ft NAVD (or relative datum), "" when unset
  downstreamInvert: "",  // NEW — ft NAVD (or relative datum), "" when unset
  slope: "",             // KEPT — manual fallback when inverts absent
  length: "",
  splitRole: ""
}
```

New pipes default `upstreamInvert: ""` and `downstreamInvert: ""`. Existing pipes loaded from state without these fields behave as if they are `""` (undefined → empty string via `|| ""`).

---

## `pipeEffectiveSlope(pipe)` Helper

Single source of truth for the active slope value. Inserted near `calcPipeRow`.

```
pipeEffectiveSlope(pipe):
  US = parseFloat(pipe.upstreamInvert)
  DS = parseFloat(pipe.downstreamInvert)
  L  = parseFloat(pipe.length)
  if isFinite(US) AND isFinite(DS) AND isFinite(L) AND L > 0:
    return (US - DS) / L
  else:
    return parseFloat(pipe.slope)   // may be NaN — callers handle gracefully
```

**Callers updated** (replace all `parseFloat(pipe.slope)` / `parseFloat(row.slope)` with `pipeEffectiveSlope()`):
- `calcPipeRow(row)`
- `buildPipeSheet(row, stormOverride)` — display of So in the detail sheet
- `buildPipesDetailSheet(stormOverride)` — So (%) column
- `buildHglDetailSheet(stormOverride)` — So column
- `buildHglRowSheet(structureId, stormOverride)` — friction loss section shows So

---

## Pipe Sizing & Capacity Tab (`renderPipes`)

### Column order

```
ID | From | To | Role | Angle | Shape | Size | n
| US Inv (ft) | DS Inv (ft) | Slope (ft/ft) | Length (ft)
| Design Q | Area (sf) | Qfull (cfs) | V (fps) | Status | [detail] | [del]
```

US Inv and DS Inv are inserted **before** Slope (between `n` and the current Slope column).

### US Inv / DS Inv cells

Standard `numInput(row, "upstreamInvert", 70)` and `numInput(row, "downstreamInvert", 70)`. No special validation. Width ~70px each.

### Slope cell — context-sensitive

```
S = pipeEffectiveSlope(row)
if upstreamInvert AND downstreamInvert AND length are all valid numbers:
  render: el("td", {class:"out computed-cell"}, fmt(S, 4))   // computed display
else:
  render: el("td", {}, numInput(row, "slope", 75))            // editable input
```

The column header remains **"Slope (ft/ft)"** — no header change needed.

### Pipe Sizing 25-yr tab (`renderPipeSizing25`)

Same column additions and slope-cell logic applied for consistency (same pipe data, different storm).

---

## HGL Tab (`renderHgl`)

### New columns — after "Upstream HGL (ft)"

```
... | Upstream HGL (ft) | US Inv (ft) | DS Inv (ft) | Crown (ft) | Crown Check | Rim (ft) | Rim Check | [detail]
```

### Cell values

For each structure row, find the outgoing pipe (`calc.outPipe`):
- **US Inv** → `calc.outPipe ? (pipe.upstreamInvert || "—") : "—"`
- **DS Inv** → `calc.outPipe ? (pipe.downstreamInvert || "—") : "—"`

Both render as plain `el("td", {}, value)` — not computed-cell styled (they are input values, shown for reference).

### HGL 25-yr tab (`renderHgl25`)

Same two columns added in the same position. Invert data is storm-independent.

---

## Excel Export / Import

The workbook builder (`buildWorkbook`) must include `upstreamInvert` and `downstreamInvert` in the Pipes sheet:

- **Export:** add "US Invert (ft)" and "DS Invert (ft)" columns to the Pipes sheet, after the `n` column and before Slope.
- **Import:** read those columns back into `upstreamInvert` / `downstreamInvert` on the pipe objects. Missing columns (old files) silently map to `""`.

---

## Detail Sheets

- **`buildPipeSheet`:** "Design discharge" section shows `So = pipeEffectiveSlope(row)`. If inverts are set, add a note line: `"Slope computed from US invert (X.XX ft) − DS invert (X.XX ft) / L"`.
- **`buildPipesDetailSheet` / `buildHglDetailSheet`:** `So (%)` column uses `pipeEffectiveSlope`.
- **`buildHglRowSheet`:** Friction loss section already shows So — update to `pipeEffectiveSlope`.

---

## Self-Review

1. **Placeholder scan:** None. All fields, helpers, and call sites are named explicitly.
2. **Internal consistency:** `pipeEffectiveSlope` is the single read path — no drift between tabs possible.
3. **Scope:** Focused. No new tabs, no schema migration beyond two new pipe fields.
4. **Ambiguity:** Slope cell header stays "Slope (ft/ft)" whether computed or manual — acceptable because the cell's visual treatment (computed vs input) signals the state. No second label needed.
5. **Edge case — negative slope:** If DS invert > US invert, slope is negative. `manningFullFlow` and `frictionSlope` expect positive S; callers already guard against `S <= 0` returning null/NaN gracefully. No special handling needed beyond what exists.
6. **Excel import backward compat:** Old files without invert columns map to `""` — slope field remains the active value. Confirmed safe.
