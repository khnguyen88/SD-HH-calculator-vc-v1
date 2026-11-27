# Spec 4 (DRAFT) — Legacy Native xlsx Migration

- **Date:** 2026-11-27
- **Status:** **DRAFT.** Framing only — NOT brainstormed with the user. This document poses the problem and sketches options so a future brainstorming session can finalize.
- **Author:** Claude (autonomous draft at user's request after Spec 3 ship-gate)
- **Precedent:** [`2026-11-26-spec3-shape1-audit.md`](../notes/2026-11-26-spec3-shape1-audit.md) — the full schema of the legacy native shape.
- **Follow-up to:** Spec 3 verification checklist §7.1.

---

## Problem statement

The Spec 3 `detectShape` rule keys off `STORM DRAIN COMPS`:

```
STORM DRAIN COMPS present + Outlet Structures present  → "robust"
STORM DRAIN COMPS present + Outlet Structures absent   → "simple"
otherwise                                               → "unknown"
```

Pre-Spec-3 calculator exports used a different sheet layout entirely — sheets named `Pipe Sizing`, `Junction Structure`, `Drainage Area`, `Rainfall Settings`, etc., with **no** `STORM DRAIN COMPS` sheet. The Spec 3 audit (`docs/superpowers/notes/2026-11-26-spec3-shape1-audit.md`) called this "shape #1."

**Impact:** any user with a pre-Spec-3 xlsx file sees `Couldn't detect template shape. This file should be a WIP template, golden template, or calculator export.` on import. The file is unusable until manually migrated.

**Side effect on tests:** 9 of the 14 failing visualizer JS tests (`xlsx-import.test.js` tests 131–137 + `inverts.test.js` tests 73–74) use legacy-native fixtures. They fail for the same reason real user files would.

---

## Options

### A. Add a third detection branch + legacy reader

- Extend `detectShape`:
  ```
  STORM DRAIN COMPS present → simple/robust (as today)
  Pipe Sizing + Junction Structure both present → "legacy-native"
  otherwise → unknown
  ```
- Add `readLegacyNativeWorkbook(wb)` in `xlsx-shape-reader.js` that parses the pre-Spec-3 layout and returns the SAME state shape as `readRobustWorkbook`.
- Users importing legacy files see the same experience as Robust imports (full data, outlet structures, TR-55 segments).
- **Pros:** zero user friction. Transparent migration.
- **Cons:** permanent carrying cost of a third reader. Pre-Spec-3 column layout must be documented and tested.

### B. Add a detection branch + migration-warning toast

Same detection as A, but `readLegacyNativeWorkbook` returns a minimal state (pipes + structures only, dropping outlet work). Shows a toast:

> *"Imported a legacy xlsx format. Outlet structures and TR-55 segments were not read. Re-export as Robust to upgrade."*

Users can continue; data loss is documented.
- **Pros:** cheaper reader (~30 lines vs ~150). Encourages migration.
- **Cons:** silent data loss on outlet work.

### C. One-shot migration script, no in-app support

Write a standalone `docs/template-analysis/migrate_legacy_native.py` that reads a pre-Spec-3 xlsx and emits a Robust-shape xlsx. Document the manual migration path. Calculator detection unchanged.
- **Pros:** no calculator code changes. Clean separation.
- **Cons:** users must know the script exists and run it from CLI. Visualizer JS tests stay failing.

---

## Recommended path (for brainstorm starter)

**Option A.** Reasons:
- Fixes 9 of the 14 failing visualizer JS tests as a side effect (they feed legacy fixtures through the reader; A makes the reader handle them).
- Lowest user friction.
- Pre-Spec-3 column layout is already documented in the shape #1 audit note.

Estimated implementation: ~150 lines across `xlsx-shape-reader.js` (reader), the calculator's `applyLegacyNativeReaderResult` (new), the visualizer's dispatch (one new branch), and a pytest fixture + assertions.

---

## Open questions

- Does the pre-Spec-3 shape have a Config sheet? (Audit says no — toggles default.)
- Should the migration auto-set `state.exportShape = "robust"` so re-export writes the new format?
- Lossy fields: anything the pre-Spec-3 shape held that the new state model can't represent?

---

## Deliverables (if Option A selected)

1. `readLegacyNativeWorkbook(wb)` in `drainage-calculator/lib/xlsx-shape-reader.js`.
2. `applyLegacyNativeReaderResult(legacy)` in the calculator dev HTML.
3. Detection branch update in `detectShape`.
4. Visualizer dispatch update.
5. `docs/template-analysis/test_legacy_native_reader.py` with ~3 tests.
6. Fixture: use one of the 7 broken `xlsx-import.test.js` fixtures as the pytest fixture.
7. Entry in `calculator-import-contract.md` (bump to Contract-Version 3).

---

**Next step (future session):** User runs `/brainstorm` against this draft, converts it to a finalized Spec 4 design doc, then plan + implement.
