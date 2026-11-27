# Spec 3 Verification Checklist

> **For agentic workers or human reviewers:** this is the hand-off checklist after Spec 3 was implemented end-to-end on `feature/spec3-three-shape` without per-phase approval. Walk it top-to-bottom. Every unchecked item is a potential bug; mark checks or convert to follow-up tickets.

**Branch:** `feature/spec3-three-shape` (worktree at `.worktrees/spec3-three-shape`). 23 commits ahead of main. Main is untouched.

**Spec:** `docs/superpowers/specs/2026-11-26-spec3-three-shape-bidirectional-design.md`

**Plan:** `docs/superpowers/plans/2026-11-26-spec3-three-shape-bidirectional.md` (and phase files under `docs/superpowers/plans/2026-11-26-spec3/`)

---

## Status snapshot

- **Pytest:** 82 passed, 6 skipped (3 robust-writer + 2 robust-reader + 1 HGL-round-trip; all skipped pending manual-fixture generation).
- **Built HTML files:**
  - `drainage-calculator/storm-drain-design-calculator.html` — ~1.15 MB (embeds golden template base64).
  - `visualizer/storm-drain-visualizer.html` — ~571 KB.
- **Visualizer JS tests:** 123 pass / 14 fail. 9 failures are obsolete-behavior tests (`xlsx-import.test.js`, `inverts.test.js` 73-74); 5 are a test-harness regression (`hash-import.test.js` 45-49). See §7 below.

---

## §1 — Pre-work verification (Tasks 1–2)

**Goal:** DATA2 cols D–L cleared; two per-tab doc corrections landed.

- [ ] **DATA2 in `template_wip_new.xlsx`:** open the xlsx in Excel 365. Confirm A1:C101 preserved (headers + values); D1:L101 all empty.
- [ ] **DATA2 in `template_golden.xlsx`:** same check.
- [ ] **SDC VLOOKUP formulas unchanged:** click `STORM DRAIN COMPS!AZ10`. Formula bar shows `=IFERROR(VLOOKUP(AY10,DATA2!$A$2:$D$101,2),"")`. `BB10` same with col_index `3`.
- [ ] **`repair.py` runs idempotently:** `cd docs/template-analysis && python repair.py ../template_wip_new_pre-repair.xlsx ../template_wip_new.xlsx` exits 0; produces a WIP byte-identical to the current commit.
- [ ] **01-storm-drain-comps.md:** col R described as "Angle Out of Pipe (Deg) - Whole #"; col S as "Manning Coeff". Footnote at bottom cites the empirical verification.
- [ ] **05-c-factor.md:** col I described as "Imp. Area (Ac)"; col W described as Table 3-3 Tc lookup (golden-only, advisory).
- [ ] **Spec-1 U7 citation note:** `docs/superpowers/specs/2026-11-25-template-wip-audit-design.md` line ~163 points to the updated `05-c-factor.md`.

---

## §2 — Phase 1 verification: Simple reader (Tasks 3–7)

**Goal:** calculator auto-detects Simple xlsx and loads it into state.

**Open `drainage-calculator/storm-drain-design-calculator.html` in a browser.**

- [ ] **UI loads without console errors.** Open DevTools → Console.
- [ ] **Import legacy WIP sample:** click Import → pick `docs/template_wip_new_pre-repair.xlsx` (3-pipe I-3 → MH-4 → MH-3 chain).
  - Expected: toast `Imported Simple template. Outlet structures, TR-55 segments, and custom NOAA data were not in the file.`
  - Expected: 3 pipes + 4 structures populate the UI.
  - Shape toggle flips to **Simple**.
- [ ] **Import golden (empty project):** click Import → pick `docs/template_golden.xlsx`.
  - Expected: Simple toast. Empty state in UI. No console errors.
  - Shape toggle flips to **Simple**.
- [ ] **Hydraulics toggles land on state:** in DevTools: `state.hydraulics` should show `junctionAngleRule: "smaller-loss"`, `hglCrownCeilingRule: "crown-plus-1ft"`, `hglMethod: "hec22"` (or the mapped internal flag).
- [ ] **Unknown-shape file rejected:** create a blank xlsx in Excel (no sheets matching the detect names), import it. Expected: `Couldn't detect template shape...` toast.

---

## §3 — Phase 2 verification: Robust template rebuild (Tasks 8–13)

**Goal:** calculator's native Robust export is styled like Simple + Robust-only extras appended.

- [ ] **Built-file size check:** `ls -la drainage-calculator/storm-drain-design-calculator.html` reports ~1.15 MB. (Pre-Spec-3 was ~793 KB.)
- [ ] **Base64 payload present:** `grep -c "__TEMPLATE_GOLDEN_B64" drainage-calculator/storm-drain-design-calculator.html` returns ≥ 1.
- [ ] **`buildRobustWorkbook` present:** `grep -c "async function buildRobustWorkbook" drainage-calculator/storm-drain-design-calculator.html` returns 1.

**Produce the Robust round-trip fixture (manual):**

- [ ] Import `template_wip_new_pre-repair.xlsx` (3-pipe seed).
- [ ] In DevTools: `state.exportShape = "robust"; exportExcel();` → file downloads.
- [ ] Save as `docs/template-analysis/fixtures/robust_roundtrip.xlsx`.

**Open the fixture in Excel 365:**

- [ ] Opens without a repair prompt.
- [ ] Sheet tabs include all Simple sheets AND these Robust-only ones: `TR-55 Segments`, `Outlet Structures`, `Outlet Devices`, `Rating - <label>` (one per facility), `Rainfall Settings`.
- [ ] HGL + print sheets auto-populate — no manual refresh needed (iterate=True from Spec 2).
- [ ] Row-1 headers on the 4 Robust-only tabular sheets have the SAME dark background + white text as `STORM DRAIN COMPS!A8`. Visual styling matches.
- [ ] `Config!B1` = project name; `B6` = `robust`; `B7` = `2`.

**Un-skip the pytest fixture tests:**

- [ ] From the worktree: `pytest docs/template-analysis/ -q` now shows 85 passed, 3 skipped (robust writer + robust reader tests both find the fixture).

---

## §4 — Phase 3 verification: Simple writer + toggle UI (Tasks 14–17)

**Goal:** calculator exports Simple (golden shape) on toggle; lossy toast fires when dropping Robust-only state.

- [ ] **Toggle UI present:** radio pair labeled Simple/Robust next to the Export button; Robust selected by default.
- [ ] **Mobile (resize browser < 720 px):** radio pair hides; hamburger menu shows "Export shape: Simple" and "Export shape: Robust" buttons.
- [ ] **Simple export (no Robust-only data):** fresh session, no outlet structures. Select Simple, click Export.
  - Expected: file downloads with `(simple)` in the generic success toast.
  - **No** lossy-export toast appears.
- [ ] **Simple export (with Robust-only data):** add at least one Outlet Structure and one Outlet Device in the UI. Select Simple, click Export.
  - Expected: generic success toast AND the lossy toast: `Exported Simple template. Outlet structures, TR-55 segments, custom NOAA data, and splitter settings are not stored in this format — export as Robust to preserve them.`
  - Open the exported file in Excel: 17 sheets only (Simple layout); `Config!B6` = `simple`; no `Outlet Structures` tab.
- [ ] **Robust export:** toggle to Robust, click Export.
  - Expected: file downloads with `(robust)`; opens in Excel with 17+ sheets including Outlet Structures.
- [ ] **Import auto-flips toggle:** import the Robust file → toggle flips to Robust. Import the Simple file → toggle flips to Simple.
- [ ] **Legacy writer gone:** `grep -c "_legacyBuildWorkbook\|^function buildWorkbook" drainage-calculator/storm-drain-design-calculator.html` returns 0.

---

## §5 — Phase 4 verification: HGL method wiring (Tasks 18–20)

**Goal:** `Config!B5` flip actually changes HGL col K values in Excel.

**Open `docs/template_golden.xlsx` in Excel 365.**

- [ ] **Opens without repair prompt.**
- [ ] **Formula shape on HGL!K10:K20:** click a populated cell → formula bar shows `=IF(hglMethod="legacy both-end crown floor",IFERROR(IF(A{r}="","",MAX(D{r},J{r}+G{r})),""),IFERROR(IF(A{r}="","",MAX(J{r}+G{r})),""))`. Legacy branch retains `D{r}` (us_crown); HEC-22 branch omits it.
- [ ] **Formula shape on HGL!M10:M20:** both IF branches identical in body (defensive wrap). `hglMethod` named range still in the IF.
- [ ] **Formula shape on HGL!G10 (ArrayFormula):** `{=IF(hglMethod="...",IFERROR(IF(A7="","",MAX(F7,Q7,MAX(IF($A$7:$A$91=$B7,$M$7:$M$91)))),""),<same body>)}` — curly braces indicate CSE array. Both branches identical.
- [ ] **HGL(25YEAR) same pattern:** click a cell on each of G/K/M; same IF-branch structure.
- [ ] **Flip toggle, check values:** change `Config!B5` from `HEC-22 EGL (d/s crown floor)` to `legacy both-end crown floor`. Observe HGL col K values on populated rows. **At least one row** should show a different value (any row where `D{r}` us_crown was higher than `J{r}+G{r}` and higher than the HEC-22 floor).
- [ ] **Flip back:** Config!B5 → `HEC-22`. Values revert.
- [ ] **Baseline cross-check:** with Config!B5 = legacy, HGL col M should match `docs/template-analysis/hgl-reference-values.md` row-for-row within rounding.

**Optional: un-skip the round-trip pytest.**

- [ ] Save golden with B5 = HEC-22 → `docs/template-analysis/fixtures/golden_hec22_cached.xlsx`.
- [ ] Re-open original, flip B5 = legacy, save → `docs/template-analysis/fixtures/golden_legacy_cached.xlsx`.
- [ ] Re-run pytest. `test_hgl_k_values_differ_between_methods` passes (col K values differ between the two cached workbooks).

---

## §6 — Phase 5 verification: Visualizer parity (Tasks 21–23)

**Goal:** visualizer imports both Simple and Robust xlsx via the shared reader.

**Open `visualizer/storm-drain-visualizer.html` in a browser.**

- [ ] **UI loads without console errors.** `window.__xlsxShapeReader` is defined (check in DevTools Console).
- [ ] **Import Simple file:** click Import → `docs/template_wip_new_pre-repair.xlsx`.
  - Expected: HGL profile renders with 3 pipes + 4 structures.
  - DevTools: `state.hglMethod` reflects HEC-22 default (WIP has no Config sheet).
- [ ] **Import Robust file:** `docs/template-analysis/fixtures/robust_roundtrip.xlsx`.
  - Expected: same profile renders. Config's `hglMethod` drives the visualizer's HGL walk.
- [ ] **Import unknown-shape xlsx:** empty xlsx → expected: unknown-shape error.
- [ ] **Shape reader inlined in built file:** `grep -c "__xlsxShapeReader\|detectShape" visualizer/storm-drain-visualizer.html` returns ≥ 4.
- [ ] **Contract version bumped:** `docs/template-analysis/calculator-import-contract.md` header shows `**Contract-Version:** 2`. §3a, §4a, §7.1/7.2 sections present.

---

## §7 — Deferred issues and follow-up tickets

These were discovered during implementation and NOT fixed in Spec 3. Open as follow-up tickets.

### §7.1 — Pre-Spec-3 native xlsx files can't be imported

**Impact:** medium. Users with old calculator exports (Pipe Sizing + Junction Structure, no STORM DRAIN COMPS) will see `Couldn't detect template shape...` on import into either calculator or visualizer.

**Root cause:** the new detectShape rule keys off `STORM DRAIN COMPS`. The old native shape (pre-Spec-3 "shape #1" from the audit) doesn't have that sheet.

**Mitigation path for affected users:** no in-tool migration exists. Open the old xlsx in the pre-Spec-3 build of the calculator, re-export, then re-import into the new build. OR: add a third detection branch for the legacy shape with a migration-focused reader. The audit at `docs/superpowers/notes/2026-11-26-spec3-shape1-audit.md` has the full old-shape schema.

**Verification that this is the current behavior:** load an old native-xlsx file into the new calculator — expected: unknown-shape toast.

### §7.2 — Robust round-trip drops custom NOAA, Kb overrides, inlet-spacing data

**Impact:** medium. `buildRobustWorkbook` (Task 11) emits a Rainfall Settings sheet, but `readRobustWorkbook` (Task 21) does NOT read it back. Same silent drop for `state.kb` overrides and `state.inletSpacing` rows if those were ever Robust-only.

**Flagged by:** Task 21 implementer.

**Fix sketch:** extend `readRobustWorkbook` in `drainage-calculator/lib/xlsx-shape-reader.js` to parse:
- `Rainfall Settings` sheet (key/value rows) into `base.rainfall`.
- `Kb Coefficients` sheet (if present) into `base.kb`.
- `Inlet Spacing` tab rows into `base.inletSpacing`.

Then extend `applyRobustReaderResult` in the calculator dev HTML to map those back onto state. One commit; ~50 lines.

**Verification that this is the current behavior:** add a custom NOAA override in UI → export as Robust → re-import → check `state.rainfall.customNoaa` in DevTools. It should NOT contain the override.

### §7.3 — Visualizer JS tests: 14 failures (123 pass)

Run `cd visualizer/visualizer-tests && npm test` to see current state.

**Breakdown:**

| File | Failing tests | Root cause |
|---|---|---|
| `xlsx-import.test.js` | 7 (tests 131–137) | All feed pre-Spec-3 native xlsx (Pipe Sizing + Junction Structure, no STORM DRAIN COMPS). `detectShape` now returns `unknown`. |
| `inverts.test.js` | 2 (tests 73–74) | Same cause — legacy native shape. |
| `hash-import.test.js` | 5 (tests 45–49) | Test-harness regression: `_harness.js` loads the visualizer dev HTML into jsdom with `resources: "usable"`; the new `<script src="../drainage-calculator/lib/xlsx-shape-reader.js">` tag references a path jsdom can't resolve. Downstream script initialization aborts. |

**Fix sketch:**
- (7+2) **Obsolete-behavior tests:** rewrite them against Simple/Robust fixtures (or delete if truly obsolete). Legacy shape is no longer supported; pin those tests to a new Simple-format fixture.
- (5) **Harness fix:** extend `visualizer/visualizer-tests/_harness.js` to inline `xlsx-shape-reader.js` just like it (kind-of) inlines SheetJS. Then the hash-import tests that only care about `#data=` JSON parsing (not xlsx parsing) can proceed.

**Workaround for CI:** mark the 14 tests `test.skip(...)` with a comment pointing to this checklist §7.3 until fixed. Do NOT skip silently.

### §7.4 — Manual fixtures still needed to un-skip 6 pytest tests

| Test | Fixture needed | How to produce |
|---|---|---|
| `test_robust_writer.py` (×3) | `docs/template-analysis/fixtures/robust_roundtrip.xlsx` | Browser: import pre-repair xlsx; `state.exportShape = "robust"; exportExcel()`; save download. |
| `test_robust_reader.py` (×2) | Same fixture as above. | — |
| `test_hgl_method_round_trip.py` (×1) | `docs/template-analysis/fixtures/golden_hec22_cached.xlsx` AND `docs/template-analysis/fixtures/golden_legacy_cached.xlsx` | Open golden in Excel at each `Config!B5` setting, Save As each. |

Follow the procedures in §3 and §5 above.

### §7.5 — WIP SHA pin continues to drift

Known pre-existing noise (per outstanding-todos §5). Every pytest session that touches the `repaired_wb` fixture rewrites `template_wip_new.xlsx` to slightly different bytes (openpyxl's zip output is non-deterministic across runs). The `WIP_SHA256` pin in `conftest.py` is re-pinned whenever the WIP is intentionally changed; it will drift again on the next pytest run. The SHA-drift warning is informational, not a test failure. No action needed.

### §7.6 — Pre-existing working-tree modifications

Running `git status` on the worktree shows two files modified but not staged:
- `docs/template-analysis/pass_a.json`
- `docs/template_wip_new.xlsx`

These were already dirty when the worktree was created from main. They're known pytest-session noise (`pass_a.json` regenerates on test runs; WIP is rewritten by the `repaired_wb` fixture). Not Spec 3's responsibility; don't commit them without checking they're not intentional divergence from main.

---

## §8 — Final merge gate

Only merge `feature/spec3-three-shape` → `main` when ALL of the following are true:

- [ ] §1 through §6 all checked (no regressions in behavior).
- [ ] §7.1 and §7.2 either fixed or filed as follow-up tickets with issue numbers.
- [ ] §7.3 visualizer JS tests either fixed or explicitly `test.skip`'d with a comment pointing here.
- [ ] §7.4 pytest fixtures produced and all 88 pytest tests pass (82 current + 6 formerly-skipped).
- [ ] Phase 5 Task 20 manual Excel verification matrix in `phase-4-hgl-wiring.md` passes.
- [ ] `node drainage-calculator/build.js && node visualizer/build-visualizer.js` both exit 0 cleanly from the worktree.
- [ ] `git log --oneline main..HEAD | wc -l` shows 23 (no accidental extra commits).

After merge:
- [ ] Deploy per `docs/deployment-runbook.md`: copy built HTML files to the `gh-pages` branch via the `../gh-pages-deploy` worktree. (Project memory: `project_gh_pages_worktree`.)
- [ ] Verify deployed URL https://khnguyen88.github.io/SD-HH-calculator-vc-v1/ shows the new shape toggle and imports both Simple and Robust.
- [ ] Clean up the feature worktree: `git worktree remove .worktrees/spec3-three-shape`.

---

## Commit log (reference)

```
aed59ac  docs(contract): bump Contract-Version to 2                      (Task 23)
7d633a8  feat(visualizer): share the Spec-3 reader via inline module      (Task 22)
34e795f  feat(reader): Robust reader + calculator dispatch                (Task 21)
6fb3610  test(hgl): recognize ArrayFormula cells on HGL col G             (Task 19 fix)
d4b12f8  test(hgl): formula-branch + round-trip tests for hglMethod       (Task 19)
73d3d49  feat(template): wire hglMethod to actual HGL formulas            (Task 18)
0be534a  feat(calculator): lossy-export toast + drop legacy writer        (Task 16)
9fc3577  feat(ui): add shape toggle next to Export button                 (Task 15)
ddc8a54  feat(calculator): implement buildSimpleWorkbook                  (Task 14)
b1f02ae  test(robust): round-trip fixture + shape-tag assertions          (Task 13)
d89deb0  feat(calculator): dispatch exports via shape toggle              (Task 12)
d0b6b88  feat(calculator): buildRobustWorkbook appends Robust-only sheets (Task 11)
75a2b1e  feat(calculator): buildRobustWorkbook fills Simple surface       (Task 10)
727db7f  feat(calculator): add loadGoldenBase() helper                    (Task 9)
ffe6bdb  build(calculator): embed template_golden.xlsx as base64          (Task 8)
e8aafa7  feat(calculator): dispatch imports via shape reader              (Task 7)
ac82f1e  feat(reader): Simple reader reads C_FACTOR + Config toggles      (Task 6)
f306736  feat(reader): Simple reader materializes structures from pipes   (Task 5)
5f10ba5  feat(reader): Simple reader pipe-row ingestion                   (Task 4)
690c2e8  feat(reader): add xlsx-shape-reader skeleton + detectShape       (Task 3)
2291e84  docs(template-analysis): correct col labels (Spec 3 pre-work)    (Task 2)
5b41fc1  docs(template): fix Task 1 SHA pin + C101 assertion              (Task 1 fix)
945a72c  docs(template): DATA2 cleanup — clear unused cols D-L             (Task 1)
```
