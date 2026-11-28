# Spec 5 — Visualizer Test-Suite Cleanup

- **Date:** 2026-11-27
- **Status:** Finalized (Option A: inline xlsx-shape-reader.js in `_harness.js`).
- **Follow-up to:** Spec 3 verification checklist §7.3.

## Goal

Get `visualizer/visualizer-tests/` back to a green suite (all 137 tests passing) so visualizer gh-pages deploys are unblocked.

## Root cause (single)

All 14 pre-fix failures traced to one issue: jsdom couldn't resolve the `<script src="../drainage-calculator/lib/xlsx-shape-reader.js">` tag that Spec 3 Task 22 added to the visualizer dev HTML. Jsdom's `resources: "usable"` fetches relative scripts against the loaded page URL (`http://localhost/...`), which doesn't map to the real filesystem path.

Breakdown of pre-fix failures:
- 5 hash-import tests (45–49): harness couldn't load the shape reader → window.__xlsxShapeReader undefined.
- 2 inverts tests (73–74) + 7 xlsx-import tests (131–137): same cause, surfaced as "reader not loaded" assertions.

## Design

### Harness fix

`visualizer/visualizer-tests/_harness.js` — inline the shape reader source directly into the HTML string before jsdom parses it. Matches the pattern already used for SheetJS. Zero external fetches needed.

### Side effects observed during implementation

Fixing the harness revealed secondary design issues in the visualizer's post-reader apply code that Spec 4 fully resolves (legacy-shape pipe IDs, structure.totalQ/outPipeId/capturedQ/startElev/forceElev, drainage.id separate from structureId, hglMethod "no row = don't overwrite" semantics). These were latent — they only surfaced after the harness let the tests actually run.

The combined Spec 4 + Spec 5 change set takes the suite from **123 pass / 14 fail** → **137 pass / 0 fail**.

## Plan (shipped inline with Spec 4)

- **Task 5.1** — Inline shape reader in `_harness.js`. Done.
- **Task 5.2** — Fix visualizer apply to respect reader-provided fields (legacy shape carries id/splitRole/startElev/forceElev/totalQ/outPipeId/capturedQ). Done.
- **Task 5.3** — Fix hglMethod "absent" semantics: only set `state.ui.hglMethod` when the xlsx provided a recognized value; leave untouched otherwise. Done.

All three tasks landed in the Spec 4 commit sequence.

## No new test files

Rather than add a dedicated `shape-reader.test.js`, the existing tests now exercise the reader via the harness. If future reader changes need coverage beyond what xlsx-import/hash-import/inverts tests give, add a focused unit test file at that time.

## Done

137/137 visualizer tests pass. Visualizer redeploy to gh-pages is now unblocked.
