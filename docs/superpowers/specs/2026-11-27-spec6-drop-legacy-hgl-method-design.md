# Spec 6 — Drop Legacy Both-End Crown Floor HGL Method

- **Date:** 2026-11-27
- **Status:** Finalized (per user directive: "stick with the MDSHA/HEC22/Montgomery County HGL calculator rule").
- **Scope:** Product simplification. Removes the PG-County "legacy both-end crown floor" HGL option from both apps and the xlsx template.

## Rationale

MDSHA, MCDOT, and HEC-22 use the same HGL walking rule (downstream crown floor only). PG County SWM Ch. 8 specifies a stricter both-end crown pin. Spec 1/2/3 carried support for both to serve PG County reviewers. User's project does not need PG support, so the toggle is dead weight: carrying it adds UI complexity, formula branches in xlsx, dead code in both apps, and tests that gate nothing useful.

## Changes

### 1. xlsx template (`build_golden.py`)

- `wire_hgl_method` renamed to `simplify_hgl_method`: rewrites HGL and HGL(25YEAR) col K formulas (the only col with a us_crown term to strip) to plain `=IFERROR(IF(A{r}="","",MAX(J{r}+G{r})),"")` — HEC-22 only, no IF-wrap.
- Cols G and M are left UNCHANGED (they had no us_crown to drop; the Spec 3 Task 18 IF-wrap on them was defensive and now redundant — simplify_hgl_method also unwraps them to their original bodies).
- `Config!B5` data validation dropdown drops the "legacy both-end crown floor" option; default stays `"HEC-22 EGL (d/s crown floor)"`.
- `Config!B5` named range `hglMethod` stays defined (compat for old readers), but no formula references it anymore.

### 2. Calculator

- Remove the `<select>` UI that toggles `state.hydraulics.hglMethod`.
- Hardcode `state.hydraulics.hglMethod = "hec22"` in initial state and quick-save restore.
- Remove the conservative crown-pin branch in the HGL compute path.
- Writers (`buildSimpleWorkbook` + `buildRobustWorkbook`) always write `Config!B5 = "HEC-22 EGL (d/s crown floor)"`.
- `hglMethodFromLabel` / `hglMethodLabel` helpers simplify: always `"hec22"` / `"HEC-22 (standard)"`.
- Print-header labels drop the "Method:" suffix (always HEC-22, no value to display).

### 3. Visualizer

- Remove the `hglMethodSelect` DOM injection + label.
- Hardcode `state.ui.hglMethod = "hec22"` in initial state.
- Remove the legacy branch in `buildLedger` (lines 538, 550 in current dev HTML) — only the HEC-22 walk remains.
- Sample projects: `bburg` sample's `config.hglMethod` flips from `"legacy-both-crown"` to `"hec22"`.

### 4. Shared reader (`xlsx-shape-reader.js`)

- `hglMethodFromLabel` simplifies to always return `"hec22"`. Kept as a function for backwards-compat with existing callers that pass through the result.
- Default `config.hglMethod = "HEC-22 EGL (d/s crown floor)"` unchanged.

### 5. Tests

- `test_hgl_method_formula_branches.py` — rewritten: assert HGL col K formulas are plain `=IFERROR(IF(A{r}="","",MAX(J{r}+G{r})),"")`, no `hglMethod` literal. Delete the "branches differ" test.
- `test_hgl_method_round_trip.py` — delete (no toggle = no round-trip to test).
- `test_config_toggles_golden` in `test_simple_reader.py` — assertion on B5 unchanged (still "HEC-22 EGL (d/s crown floor)").
- Visualizer `xlsx-import.test.js` — delete the four HGL-method tests (134–137). They test a feature that no longer exists.

### 6. Docs

- Update `calculator-import-contract.md` §2 toggles table: drop `hglMethod` row entirely (or mark as deprecated-but-persisted). Bump Contract-Version to 3.
- Update `CLAUDE.md` if any mention of the toggle exists.
- Spec 3 design doc gets a one-line correction note at the bottom pointing here.

## Non-goals

- No cleanup of the `state.hydraulics.hglMethod` state field itself — it stays as a string field for forward-compat (future "add another HGL method" would reuse it). It's just always `"hec22"` now.
- No deletion of the `hglMethod` named range in the xlsx template — leaves a hook for future methods.
- No migration of old xlsx files that still carry `Config!B5 = "legacy both-end crown floor"` — on import, the value is ignored (treated as HEC-22).

## Testing

- `pytest docs/template-analysis/` — expect current 82 passed to drop by 1 (round-trip test deleted) + updated branch test. Net ≈ 81 passed, 5 skipped.
- `npm test` from `visualizer/visualizer-tests/` — expect 137 - 4 = 133 passed, 0 failed.

## Deployment

Merge to main, build, redeploy both apps via `../gh-pages-deploy`.
