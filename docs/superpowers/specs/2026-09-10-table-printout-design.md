# Table Printout (Spreadsheet View) — Design Spec

**Date:** 2026-09-10
**Status:** Approved

---

## Overview

Add a "Print Table" button to each major data tab so users can print the tab's data in a compact spreadsheet-style layout — all rows on as few pages as possible. Complement with a "Print All Tables" button in the topbar for a full project dump. The existing per-row detail sheet system is unchanged.

---

## Tabs in Scope (8 total)

| Tab | View div ID | Section title for print header |
|---|---|---|
| Drainage Area | `view-drainage` | "Drainage Area" |
| Junction Structure | `view-structures` | "Junction Structures" |
| Pipe Sizing & Capacity | `view-pipes` | "Pipe Sizing & Capacity" |
| Outlet Control Structure | `view-outlet` | "Outlet — \<active outlet label\>" |
| Inlet Spacing | `view-inlet-spacing` | "Inlet Spacing" |
| HGL | `view-hgl` | "HGL — Primary Design Storm" |
| Pipe Sizing 25-yr | `view-pipe-sizing-25` | "Pipe Sizing & Capacity — 25-yr" |
| HGL 25-yr | `view-hgl-25` | "HGL — 25-yr" |

---

## Architecture

### Core function: `buildTablePrintSheet(viewId, title)`

1. Finds the view div: `document.getElementById(viewId)`
2. Finds the first `<table class="data">` inside it
3. Deep-clones the table: `table.cloneNode(true)`
4. Walks the clone with `clone.querySelectorAll("input, select, textarea, button")`:
   - For `<input>` and `<textarea>`: replace with a text node of `el.value`
   - For `<select>`: replace with a text node of the selected option's text (`el.options[el.selectedIndex].text`)
   - For `<button>`: remove entirely
5. Strips inline `style` attributes that set colors (pass/fail red) — keep them for print since red fail = important signal; do NOT strip them
6. Wraps the cleaned table in a print sheet div:
   ```
   <div class="calc-sheet cs-table-sheet">
     <div class="cs-header">
       <div class="cs-title">[title]</div>
       <div class="cs-sub">[state.project] — printed [YYYY-MM-DD]</div>
     </div>
     [cloned table]
     <div class="cs-footer">Storm Drain Design Calculator — [state.project]</div>
   </div>
   ```
7. Returns the div node.

**Outlet special case:** The outlet tab has multiple outlet structures. `buildTablePrintSheet` for `view-outlet` is not used directly — instead `buildOutletTablePrintSheet()` iterates `state.outletStructures`, finds each outlet's rating curve table (identified by a `data-outlet-id` attribute added to the table during render), and builds one sheet per outlet structure.

### `printTableSheet(viewId, title)`

Calls `buildTablePrintSheet(viewId, title)`, passes result to existing `printNodes([sheet])`.

For the Outlet tab, calls `buildOutletTablePrintSheet()` which returns an array of nodes (one per outlet structure, all of them), passes to `printNodes(nodes)`. The per-tab "Print Table" button and "Print All Tables" both print all outlet structures — there is no "active only" variant.

### `printAllTableSheets()`

Builds all 8 tab sheets in order and calls `printNodes(allNodes)` once. If a tab has no rows (empty table body), skip it with no toast — silently omit from output. If ALL tabs are empty, toast "Nothing to print yet."

---

## UI Changes

### Per-tab "Print Table" buttons

Add `el("button", {class:"btn btn-sm", onclick:()=>printTableSheet(viewId, title)}, "🖨 Print Table")` to each tab's `.section-head` div, alongside the existing "+ Add row" button.

For the Outlet tab, the button goes in `devSection`'s `.section-head` (the devices section header), since that's where the rating curve table lives. Label: "🖨 Print Table".

Tabs that are read-only (HGL, Pipe Sizing 25-yr, HGL 25-yr) get the button in their sole `.section-head`.

### Topbar "Print All Tables" button

Add `el("button", {class:"btn btn-sm", id:"printAllTablesBtn", title:"Print all data tables"}, "🖨 Tables")` to `.topbar-right`, placed between the `saveCompBtn` and the `saves-wrap` div.

Wire in `init()`: `document.getElementById("printAllTablesBtn").addEventListener("click", printAllTableSheets)`.

---

## Print CSS

Add a new `.cs-table-sheet` class to the inline `<style>` block:

```css
.cs-table-sheet table.data{
  font-size:9.5px;
  width:100%;
  table-layout:auto;
}
.cs-table-sheet table.data th,
.cs-table-sheet table.data td{
  padding:2px 5px;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
  max-width:120px;
}
@media print{
  .cs-table-sheet table.data{
    font-size:8.5px;
  }
  .cs-table-sheet table.data th,
  .cs-table-sheet table.data td{
    max-width:90px;
  }
}
```

`printNodes()` gains an optional `landscape` boolean param. When `true`, it injects a `<style id="sdcLandscape">@media print { @page { size: landscape; } }</style>` tag into `<head>` before calling `window.print()`. The existing `afterprint` handler removes the tag by ID if present. `printTableSheet` and `printAllTableSheets` pass `landscape: true`; existing callers (`printAllSheets`, formula reference, etc.) pass nothing (default false).

---

## Outlet Tab: `data-outlet-id` Attribute

During `renderOutlet()`, the rating curve result table (if one exists) gets a `data-outlet-id` attribute set to the outlet structure's `id`. This lets `buildOutletTablePrintSheet()` locate each outlet's table without relying on DOM position.

---

## Edge Cases

| Scenario | Behavior |
|---|---|
| Tab has no rows | `buildTablePrintSheet` returns null; `printTableSheet` toasts "No rows to print." |
| Tab's table not found in DOM | Same: toast "No data to print." |
| All tabs empty on Print All Tables | Toast "Nothing to print yet." |
| Outlet has no outlet structures | Toast "No outlet structures defined." |
| Very wide tables (HGL, Pipe Sizing) | `table-layout:auto` + `max-width` on cells allows horizontal scroll on screen; on print, landscape orientation + 8.5px font compresses to fit letter paper |

---

## Constraints

- Single HTML file — all CSS/JS inline, no new dependencies.
- `printNodes()` signature extended with optional `landscape` bool — existing callers unaffected (default false).
- Existing detail sheet print system (`printAllSheets`, `buildDrainageSheet`, etc.) unchanged.
- Print output matches existing `.calc-sheet` aesthetic: white background, dark header, footer with project name.
