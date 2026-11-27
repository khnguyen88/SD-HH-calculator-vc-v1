# Spec 5 (DRAFT) — Visualizer JS Test Suite Cleanup

- **Date:** 2026-11-27
- **Status:** **DRAFT.** Framing only — NOT brainstormed with the user.
- **Author:** Claude (autonomous draft at user's request after Spec 3 ship-gate)
- **Follow-up to:** Spec 3 verification checklist §7.3.

---

## Problem statement

After Spec 3 shipped, `visualizer/visualizer-tests/` runs **123 pass / 14 fail**. The runbook (`docs/deployment-runbook.md`) explicitly says *"a red suite blocks deployment"* for the visualizer. **The visualizer cannot be redeployed to `gh-pages` until these 14 failures are resolved or explicitly test-skipped.**

Breakdown:

| File | Failing tests | Root cause |
|---|---|---|
| `xlsx-import.test.js` | 7 (tests 131–137) | Feed pre-Spec-3 native xlsx (Pipe Sizing + Junction Structure, no STORM DRAIN COMPS). `detectShape` returns `unknown`. |
| `inverts.test.js` | 2 (tests 73–74) | Same cause — legacy native shape. |
| `hash-import.test.js` | 5 (tests 45–49) | Harness regression: `_harness.js` loads the visualizer dev HTML into jsdom with `resources: "usable"`; the new `<script src="../drainage-calculator/lib/xlsx-shape-reader.js">` tag references a path jsdom can't resolve from `http://localhost/...`. Downstream script initialization aborts. |

---

## Interaction with Spec 4

The 9 xlsx-import + inverts failures share a root cause with **Spec 4 §7.1** (legacy-native migration). If Spec 4 lands first with Option A, the shape reader learns to parse the legacy shape, and these 9 tests auto-pass without modification.

**Recommendation: brainstorm Spec 4 FIRST. Re-measure visualizer test failures. Spec 5's scope shrinks to just the 5 hash-import harness failures.**

---

## Options (for the harness failures, assuming Spec 4 handles the other 9)

### A. Inline the shape reader in `_harness.js`

Extend `visualizer/visualizer-tests/_harness.js` to inline `drainage-calculator/lib/xlsx-shape-reader.js` into the loaded HTML string, matching the pattern it (kind-of) uses for SheetJS.

- **Pros:** tests run against the real inlined reader. One-file change.
- **Cons:** harness grows a bit; maintenance point for future reader changes.

### B. Switch harness to load the BUILT HTML instead of the dev HTML

The built visualizer HTML already has the shape reader inlined by `build-visualizer.js`. Loading it skips the script-src issue entirely.

- **Pros:** tests exercise production artifact.
- **Cons:** build must run before each test session; violates TDD cycle.

### C. Skip the 5 hash-import tests

Mark `test.skip(...)` with a comment pointing to Spec 5. Documents the issue without fixing it.

- **Pros:** cheapest. Unblocks deploy.
- **Cons:** test coverage drops. Likely to be forgotten.

---

## Recommended path

**Option A + delete the 9 obsolete tests** (assuming Spec 4 Option A is in flight — those tests are moot once the legacy reader exists).

Estimated implementation:
- Harness update: ~20 lines in `_harness.js`.
- Delete 9 obsolete tests: `xlsx-import.test.js` tests 131–137 + `inverts.test.js` tests 73–74. May be simpler to delete the entire xlsx-import.test.js file if all its tests become obsolete.
- Add new test coverage for the shape-aware reader (Simple/Robust) in a fresh `shape-reader.test.js`.

---

## Blocker for deployment

**Until Spec 5 ships, the visualizer `gh-pages` deployment is frozen at its pre-Spec-3 state.** The main branch has the shape-aware visualizer; the deployed site does not. `main` ↔ `gh-pages` divergence is expected.

For the record: if the user wants the visualizer deployed ahead of Spec 5, they can:
- Confirm the test failures are documentation-only (not real regressions), and
- Explicitly override the runbook rule for one deploy.

That decision is theirs; I'm not making it autonomously.

---

## Deliverables

1. `_harness.js` extended to inline `xlsx-shape-reader.js`.
2. `xlsx-import.test.js` deleted (or 9 tests removed, file renamed).
3. `shape-reader.test.js` new — covers Simple/Robust/unknown detection + a sample Simple + Robust fixture.
4. Full `npm test` run shows 0 failures.

---

**Next step (future session):** User runs `/brainstorm` against this draft (after or alongside Spec 4), converts it to a final design doc, then plan + implement.
