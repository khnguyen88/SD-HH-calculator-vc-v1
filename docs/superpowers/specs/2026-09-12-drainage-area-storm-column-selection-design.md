# Drainage Area Storm Column Selection — Design Spec

**Date:** 2026-09-12
**Scope:** Two changes: (1) let users control which storm-event Q columns appear in the Drainage Area table, with smart defaults; (2) remove the unused "Load MoCo preset" button from the Kb Coefficients tab.

---

## 1. Storm Column Selection

### 1.1 Problem

The Drainage Area table currently renders a Q column for every storm returned by `availableStorms()` — up to 8 for NOAA (1yr, 2yr, 5yr, 10yr, 25yr, 50yr, 100yr, 500yr). Most projects need only 2–3 columns. The wide table forces horizontal scrolling and clutters printouts.

### 1.2 State

One new field added to `defaultRainfallSettings()`:

```js
daStormCols: ["2yr", "10yr"]
```

Stores the user's explicit column selections. Persists in localStorage snapshots and in the `State` sheet of the Excel export/import alongside the rest of `state.rainfall`.

Existing saved states that lack this field fall back gracefully: `visibleDaStorms` guards with `|| ["2yr", "10yr"]`.

### 1.3 Computed Visible Columns

A new pure helper function — no side effects, no new state:

```js
function visibleDaStorms(r) {
  const available = availableStorms(r.rainfallSource);
  const cols = new Set(r.daStormCols || ["2yr", "10yr"]);
  cols.add(r.pipeStorm);   // always pinned
  cols.add(r.inletStorm);  // always pinned
  if (r.pipe25Check && available.includes("25yr")) cols.add("25yr"); // forced when 25yr check is on
  const order = ["1yr","2yr","5yr","10yr","25yr","50yr","100yr","500yr"];
  return order.filter(s => available.includes(s) && cols.has(s));
}
```

This replaces the current `availableStorms(state.rainfall.rainfallSource)` call used to build the DA table header and body Q columns.

### 1.4 Pin Rules

| Storm | Condition | Behavior |
|---|---|---|
| `pipeStorm` | Always | Checked + disabled; tooltip: "Always shown (pipe design storm)" |
| `inletStorm` | Always | Checked + disabled; tooltip: "Always shown (inlet design storm)" |
| `25yr` | `pipe25Check` is on | Checked + disabled; tooltip: "Always shown (25-yr check enabled)" |
| All others | — | Interactive checkbox, reads/writes `daStormCols` |

When `pipe25Check` is toggled off, 25yr reverts to interactive (shown only if it's in `daStormCols`).

### 1.5 UI — Rainfall & IDF Tab

A new "Drainage Area Q columns" row added below the existing pipe/inlet storm dropdowns and the 25yr checkbox row. Renders one compact inline checkbox per available storm, applying pin rules above. Changing a checkbox writes to `state.rainfall.daStormCols` via `withFocusPreserved(renderAll)`.

### 1.6 UI — Drainage Area Tab

A `"Show Q columns:"` line immediately above the table, using identical rendering logic (same checkboxes, same pin rules, same state). Both locations share `state.rainfall.daStormCols` — a change in one is immediately reflected in the other.

### 1.7 Rainfall Source Changes

When the user switches `rainfallSource`, `daStormCols` is not reset — `visibleDaStorms` already filters the final list to `availableStorms(source)`, so any storms that don't exist in the new source are silently excluded from rendering. No cleanup needed on source change. The existing logic that resets `pipeStorm` and `inletStorm` to valid values on source change is unchanged.

### 1.8 What Does Not Change

- The IDF table in the Rainfall tab continues to show all available storms.
- The 25yr Pipe Sizing and HGL tabs are unaffected.
- The detail sheet for a DA row continues to report the pipe design storm Q.
- Excel export columns for the Drainage Area sheet are not filtered — all available Q values are exported regardless of `daStormCols`.

---

## 2. Remove "Load MoCo Preset" Button (Kb Coefficients Tab)

### 2.1 What Gets Deleted

| Location | Lines (approx) | Item |
|---|---|---|
| `<script>` block | 1055–1150 | `MOCO_KB_PRESET` constant (91-row array) |
| `renderKb()` | 3347–3352 | The `el("button", ..., "Load MoCo preset")` element |
| Variable export list | 6466 | `MOCO_KB_PRESET,` reference |

### 2.2 What Is Not Removed

`MOCO_INTENSITY` (rainfall IDF data) and all MoCo-related rainfall source logic remain — MoCo is still a valid rainfall source option. Only the Kb preset button and its backing data are deleted.

---

## 3. Out of Scope

- No changes to MoCo as a rainfall source.
- No filtering of Excel export Q columns.
- No per-row DA storm column overrides.
