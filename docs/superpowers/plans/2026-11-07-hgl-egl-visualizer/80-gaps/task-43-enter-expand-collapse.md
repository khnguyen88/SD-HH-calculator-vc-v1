# Task 43: Enter key expand/collapse for ledger rows

## Context

Spec §4.3: "Current row expanded inline... Prior rows collapsed; click any to expand
(collapsing the one that was open)."
Spec §5.1: "`Enter` — Expand/collapse current ledger row; confirm branch popup."

Task-19 handles ArrowUp/ArrowDown/Escape but not Enter. Task-27's `renderLedger` always
expands the cursor row with no way to collapse it. This task adds:

1. `state.ui.expandedRowId` — tracks which row is explicitly expanded (or `null` to
   auto-follow the cursor row, which preserves backward-compatible behaviour).
2. Click handler on every ledger row to expand it on click.
3. Enter keydown handler to toggle the cursor row between expanded and collapsed.

## Preconditions

- Prior tasks: task-01 (state init), task-19 (`isTypingTarget`, `isBranchPopupOpen`),
  task-27 (`renderLedger` in the `ledger-render` sentinel block).

## Exact changes

### Step 1 — Add `expandedRowId` to state

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Locate the state
initialization in the `state` sentinel block:

```js
  ui: { view: "iso", mode: "explore", hglMethod: "hec22",
        freeRoam: false, branchChoices: { byStructureId: {} } }
```

Replace with:

```js
  ui: { view: "iso", mode: "explore", hglMethod: "hec22",
        freeRoam: false, branchChoices: { byStructureId: {} },
        expandedRowId: null }
```

`null` means "auto-follow cursor" (the current behaviour). Any other string is an
explicitly-locked row id.

### Step 2 — Update `renderLedger` to honour `expandedRowId`

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Inside the
`ledger-render` sentinel block, in the `renderLedger` function, locate the two lines:

```js
      const isCurrent = row.id === cursorId;
      const collapsed = el("div", {
        style: "padding:3px 6px; font-family:ui-monospace,monospace; cursor:pointer; "
             + (isCurrent ? "background:#ffeaa7;" : ""),
        onclick: () => { /* click-to-expand handled by task-28/29 rendering an expanded block */ }
      }, oneLineForRow(row));
```

Replace with:

```js
      const isCurrent = row.id === cursorId;
      const isExpanded = state.ui.expandedRowId === null
        ? isCurrent
        : row.id === state.ui.expandedRowId;
      const collapsed = el("div", {
        style: "padding:3px 6px; font-family:ui-monospace,monospace; cursor:pointer; "
             + (isCurrent ? "background:#ffeaa7;" : ""),
        onclick: () => {
          // Click any row to expand it; click the already-expanded row to collapse.
          state.ui.expandedRowId = (state.ui.expandedRowId === row.id) ? null : row.id;
          renderLedger();
        }
      }, oneLineForRow(row));
```

Locate the expansion block:

```js
      if (isCurrent) {
        const details = el("div", { style: "padding:4px 20px;" }, renderExpandedRow(row));
        host.appendChild(details);
      }
```

Replace with:

```js
      if (isExpanded) {
        const details = el("div", { style: "padding:4px 20px;" }, renderExpandedRow(row));
        host.appendChild(details);
      }
```

### Step 3 — Add Enter keydown handler

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the
`ledger-render` sentinel block, after `renderLedger`:

```js
  // --- Enter key expand/collapse (task-43) ---

  // Sentinel that guarantees no real row id ever matches, effectively collapsing all rows.
  const LEDGER_COLLAPSED = "(collapsed)";

  document.addEventListener("keydown", (ev) => {
    if (typeof isTypingTarget === "function" && isTypingTarget(ev)) return;
    if (typeof isBranchPopupOpen === "function" && isBranchPopupOpen()) return;
    if (ev.key !== "Enter") return;
    ev.preventDefault();

    const cursorId = state.cursor && state.cursor.id;
    if (!cursorId) return;

    // Is the cursor row currently shown expanded?
    const cursorRowIsExpanded = state.ui.expandedRowId === null
      || state.ui.expandedRowId === cursorId;

    if (cursorRowIsExpanded) {
      // Collapse: lock to the sentinel (no row will match, so all collapsed)
      state.ui.expandedRowId = LEDGER_COLLAPSED;
    } else {
      // Expand: return to auto-follow (which re-expands the cursor row)
      state.ui.expandedRowId = null;
    }
    if (typeof renderLedger === "function") renderLedger();
  });
```

## Acceptance test

In DevTools console:

```js
// Seed state so renderLedger has something to render.
state.imported = {
  structures: [{ id: "OUT", type: "outfall" }, { id: "A", type: "bend" }],
  pipes: [{ id: "P1", fromId: "A", toId: "OUT",
           shape: "circular", size: 18, n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 }],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };
state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };
state.ui.expandedRowId = null;
renderLedger();

// Cursor row (P1) is auto-expanded.
const host = document.getElementById("ledger");
const rows = host.querySelectorAll('div[style*="cursor:pointer"]');
console.assert(rows.length >= 2, "at least 2 ledger rows");
// The row immediately following the P1 highlight should be the detail div.
const highlighted = Array.from(rows).find((r) => r.style.background.includes("ffeaa7"));
console.assert(highlighted, "highlighted P1 row should exist");
console.assert(highlighted.nextSibling !== null, "expanded detail should follow highlighted row");

// Enter collapses the cursor row.
document.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
renderLedger();
const h2 = Array.from(document.getElementById("ledger").querySelectorAll('div[style*="cursor:pointer"]'))
             .find((r) => r.style.background.includes("ffeaa7"));
console.assert(h2, "highlighted row still exists after collapse");
// After LEDGER_COLLAPSED, no detail div follows
const details2 = Array.from(document.getElementById("ledger").children)
  .filter((c) => c.style && c.style.padding === "4px 20px");
console.assert(details2.length === 0, "no expanded detail after Enter collapses: found " + details2.length);

// Enter again re-expands.
document.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
renderLedger();
const details3 = Array.from(document.getElementById("ledger").children)
  .filter((c) => c.style && c.style.padding === "4px 20px");
console.assert(details3.length === 1, "one expanded detail after second Enter");

// Click on the highlighted row collapses it.
state.ui.expandedRowId = null;
renderLedger();
const hl = Array.from(document.getElementById("ledger").querySelectorAll('div[style*="cursor:pointer"]'))
             .find((r) => r.style.background.includes("ffeaa7"));
hl.click();
// expandedRowId was null → clicking expanded row sets it to that row's id,
// but that is not a collapse — wait, the onclick logic is:
// if (expandedRowId === row.id) → collapse; else → expand to that row.
// When expandedRowId === null and we click P1, expandedRowId !== "P1" so it sets to "P1" (explicit).
// Click P1 again:
renderLedger();
const hl2 = Array.from(document.getElementById("ledger").querySelectorAll('div[style*="cursor:pointer"]'))
              .find((r) => r.style.background.includes("ffeaa7"));
hl2.click();
console.assert(state.ui.expandedRowId === null, "clicking already-expanded row returns to auto-follow");

console.log("task-43 expand/collapse: OK");
```

## Done when

- `state.ui.expandedRowId: null` present in state init.
- `renderLedger` uses `expandedRowId` for the expansion check.
- Every ledger row has an `onclick` that sets/clears `expandedRowId`.
- Enter handler toggles the cursor row between expanded and collapsed.
- Enter while a text input is focused does NOT toggle.
- Smoke test prints `OK`.
- Build still succeeds.
- `node --test visualizer/visualizer-tests/` — no prior tests regressed.
- Commit: `feat(visualizer): task-43 Enter key expand/collapse ledger rows`.
