# Main Calculator Gap Audit — Design Spec

**Date:** 2026-11-08  
**App:** `drainage-calculator/storm-drain-design-calculator-dev.html` (~6 741 lines)  
**Spec:** `drainage-calculator/storm-drain-calculator-spec.md`

---

## Goal

Produce atomic, flash-model-runnable fix task MDs for every identified gap in the main
calculator. Each task must be self-contained enough for an open-source LLM to execute
without reading sibling tasks.

---

## Scope

| # | Gap type | Description |
|---|----------|-------------|
| 1 | Spec compliance | Spec requirement present but absent or incomplete in the app |
| 2 | Engineering correctness | Equation in spec differs from code implementation |
| 3 | Data consistency | UI display, Excel export, or detail sheets compute the same field differently |
| 4 | Validation / edge cases | Computed output with no guard against NaN, division-by-zero, or out-of-range input |

**Out of scope (separate spec):** HEC-22 vs legacy conservative HGL toggle — see
`docs/superpowers/specs/2026-11-08-hgl-method-toggle-design.md` (to be authored).

---

## Audit methodology

For each spec section (Phase 1 → Phase 1B → Phase 2 → Phase 3 → Phase 4–6):

1. Read the governing equations and requirements in the spec.
2. Grep the app for the corresponding implementation.
3. Compare: does the code match the spec?  Are shared computed values consistent across
   UI rendering, Excel export (`buildWorkbook`), and detail-sheet builders?
4. Flag each mismatch as a gap entry.

---

## Output structure

```
docs/superpowers/plans/2026-11-08-main-calc-gaps/
  plan.md                     ← task index (same format as visualizer plan.md)
  10-compliance/
    group.md
    task-NN-<slug>.md
  20-correctness/
    group.md
    task-NN-<slug>.md
  30-consistency/
    group.md
    task-NN-<slug>.md
  40-validation/
    group.md
    task-NN-<slug>.md
```

---

## Task MD format (each task must contain)

1. **Context** — which spec section, what the gap is.
2. **Preconditions** — prior tasks that must be complete.
3. **Exact changes** — file path, sentinel comment or line number, complete replacement
   code (no partial snippets; open-source models must not guess missing context).
4. **Acceptance test** — exact command (`node drainage-calculator/build.js` succeeds +
   specific manual or automated check).
5. **Done when** — build passes, test passes, no prior-task regressions.

---

## Related specs / deferred

- HEC-22 vs legacy HGL toggle → own brainstorm + spec (Stream 2, deferred)
- Visualizer gap tasks (40–44) → `docs/superpowers/plans/2026-11-07-hgl-egl-visualizer/80-gaps/`
