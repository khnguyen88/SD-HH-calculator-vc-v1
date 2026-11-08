# task-10-01 — Print-All-Detail large-page warning

## Context

Spec Phase 7 says: "warn the user this can genuinely run to 100+ pages with a fine stage
increment across multiple facilities, since that's a real, unsurprising consequence of
the feature." `printAllDetailSheets()` currently calls `printNodes(nodes, "tabloid")`
without any check.

## Preconditions

- `drainage-calculator/storm-drain-design-calculator-dev.html` exists (edit this, not the built file)
- `drainage-calculator/build.js` exists and runs

## Exact changes

**File:** `drainage-calculator/storm-drain-design-calculator-dev.html`

Find `function printAllDetailSheets(){` (line ~5881). Replace the entire function body
with the version below that counts total stage rows and confirms before proceeding:

```js
function printAllDetailSheets(){
  // Guard: warn if the outlet tables would produce a very large printout.
  const totalStageRows = state.outletStructures.reduce((sum, os) => {
    return sum + computeRatingCurve(os.id).rows.length;
  }, 0);
  const estimatedPages = Math.ceil(totalStageRows / 50) +
    state.drainage.length + state.structures.length + state.pipes.length + 4;
  if (estimatedPages > 30) {
    const ok = window.confirm(
      "This print job may produce approximately " + estimatedPages +
      " pages (the outlet rating-curve tables alone account for " + totalStageRows +
      " rows).\n\nProceed anyway?"
    );
    if (!ok) return;
  }
  const nodes = [];
  const drain   = buildDrainageDetailSheet();    if(drain)   nodes.push(drain);
  const structs = buildStructuresDetailSheet();  if(structs) nodes.push(structs);
  const pipes   = buildPipesDetailSheet();       if(pipes)   nodes.push(pipes);
  buildOutletTablePrintSheet().forEach(n=>nodes.push(n));
  const inlet   = buildInletDetailSheet();       if(inlet)   nodes.push(inlet);
  const hgl     = buildHglDetailSheet();         if(hgl)     nodes.push(hgl);
  const pipes25 = buildPipesDetailSheet("25yr"); if(pipes25) nodes.push(pipes25);
  const hgl25   = buildHglDetailSheet("25yr");   if(hgl25)   nodes.push(hgl25);
  if(!nodes.length){ toast("Nothing to print yet — add some rows first.", true); return; }
  printNodes(nodes, "tabloid");
}
```

**Sentinel comment to locate the original function:**
Search for `function printAllDetailSheets(){` — it appears exactly once.

## Build step

```
node drainage-calculator/build.js
```

Expected: `✓ built → storm-drain-design-calculator.html` (or equivalent success line).

## Acceptance test

**Manual check (open the built file in a browser):**

1. Load `drainage-calculator/storm-drain-design-calculator.html`.
2. With the seeded example data loaded, click the topbar `📊 Detail` button.
3. Because the seeded example has a facility with ≥50 stage rows, the `estimatedPages`
   will exceed 30. Verify a `confirm` dialog appears with the page-count estimate.
4. Click Cancel → nothing prints. Click OK on a second attempt → print dialog opens.

**Zero-row check:** With no outlet structures, `totalStageRows = 0`, `estimatedPages`
will be low, no confirm dialog — the function proceeds directly to the toast
"Nothing to print yet."

## Done when

- Build succeeds.
- Confirm dialog appears when estimated pages > 30.
- Cancel aborts, OK proceeds.
- Empty-state path (no rows) still shows toast, not dialog.
