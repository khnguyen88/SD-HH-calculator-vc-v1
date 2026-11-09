# HGL/EGL Visualizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps in each task file use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone single-file offline HTML companion to the main storm-drain-design-calculator that visualizes HGL/EGL energy balance step-by-step through an imported pipe network.

**Architecture:** Single `storm-drain-visualizer-dev.html` edited by hand; `build-visualizer.js` inlines SheetJS to produce `storm-drain-visualizer.html` for users. Vanilla JS, SVG for both iso and profile views, equations re-implemented locally with a drift test asserting parity against the main app's exported values. Dark engineering aesthetic matching the main app.

**Tech Stack:** Vanilla JS/HTML/SVG · SheetJS (inlined for .xlsx import) · Node `node --test` runner with jsdom for the test harness · openpyxl + LibreOffice for independent OOXML verification.

**Spec:** `docs/superpowers/specs/2026-11-07-hgl-egl-visualizer-design.md` — the companion to this plan. Each task file references the spec section it implements.

---

## Task group index (execute in order)

Each group has a `group.md` with the group-level acceptance criteria. Each `task-NN-*.md` is self-contained and flash-model-runnable: exact file path, exact code, exact test, exact run command.

### [`00-scaffold/`](00-scaffold/group.md) — Project skeleton & build

- [ ] [`task-01-dev-html-skeleton.md`](00-scaffold/task-01-dev-html-skeleton.md)
- [ ] [`task-02-build-script.md`](00-scaffold/task-02-build-script.md)
- [ ] [`task-03-el-helper-and-focus.md`](00-scaffold/task-03-el-helper-and-focus.md)

### [`10-import/`](10-import/group.md) — Data ingress (JSON + XLSX)

- [ ] [`task-04-json-schema-validator.md`](10-import/task-04-json-schema-validator.md) · depends on 03
- [ ] [`task-05-json-importer.md`](10-import/task-05-json-importer.md) · depends on 04
- [ ] [`task-06-xlsx-importer-sheets.md`](10-import/task-06-xlsx-importer-sheets.md) · depends on 04
- [ ] [`task-07-autolayout-no-coords.md`](10-import/task-07-autolayout-no-coords.md) · depends on 05

### [`20-compute/`](20-compute/group.md) — Pure-math core (Section 7 of spec)

- [ ] [`task-08-pipe-geometry.md`](20-compute/task-08-pipe-geometry.md) · depends on 03
- [ ] [`task-09-manning-friction.md`](20-compute/task-09-manning-friction.md) · depends on 08
- [ ] [`task-10-kb-interpolation.md`](20-compute/task-10-kb-interpolation.md) · depends on 03
- [ ] [`task-11-structure-loss.md`](20-compute/task-11-structure-loss.md) · depends on 09, 10
- [ ] [`task-12-ledger-builder.md`](20-compute/task-12-ledger-builder.md) · depends on 11
- [ ] [`task-13-hgl-method-toggle.md`](20-compute/task-13-hgl-method-toggle.md) · depends on 12

### [`30-views/`](30-views/group.md) — SVG renderers (iso + profile)

- [ ] [`task-14-iso-projection.md`](30-views/task-14-iso-projection.md) · depends on 07
- [ ] [`task-15-iso-svg-render.md`](30-views/task-15-iso-svg-render.md) · depends on 14
- [ ] [`task-16-profile-svg-render.md`](30-views/task-16-profile-svg-render.md) · depends on 12
- [ ] [`task-17-view-toggle-hotkey.md`](30-views/task-17-view-toggle-hotkey.md) · depends on 15, 16

### [`40-navigation/`](40-navigation/group.md) — Cursor, arrow walk, branch popup

- [ ] [`task-18-cursor-state.md`](40-navigation/task-18-cursor-state.md) · depends on 12
- [ ] [`task-19-arrow-walk-upstream.md`](40-navigation/task-19-arrow-walk-upstream.md) · depends on 18
- [ ] [`task-20-branch-popup.md`](40-navigation/task-20-branch-popup.md) · depends on 19
- [ ] [`task-21-free-roam-toggle.md`](40-navigation/task-21-free-roam-toggle.md) · depends on 19
- [ ] [`task-22-shift-arrow-nudge.md`](40-navigation/task-22-shift-arrow-nudge.md) · depends on 15

### [`50-edit-mode/`](50-edit-mode/group.md) — Overrides store, editable fields, JSON export

- [ ] [`task-23-overrides-store.md`](50-edit-mode/task-23-overrides-store.md) · depends on 12
- [ ] [`task-24-editable-ledger-fields.md`](50-edit-mode/task-24-editable-ledger-fields.md) · depends on 23
- [ ] [`task-25-override-badge-reset.md`](50-edit-mode/task-25-override-badge-reset.md) · depends on 23
- [ ] [`task-26-export-tweaked-json.md`](50-edit-mode/task-26-export-tweaked-json.md) · depends on 23

### [`60-ledger-render/`](60-ledger-render/group.md) — Expanded-row formulas & helpers

- [ ] [`task-27-expanded-row-helpers.md`](60-ledger-render/task-27-expanded-row-helpers.md) · depends on 03
- [ ] [`task-28-row-formulas-hf.md`](60-ledger-render/task-28-row-formulas-hf.md) · depends on 27, 09
- [ ] [`task-29-row-formulas-hb.md`](60-ledger-render/task-29-row-formulas-hb.md) · depends on 27, 11
- [ ] [`task-30-two-inflow-detail.md`](60-ledger-render/task-30-two-inflow-detail.md) · depends on 29

### [`70-tests/`](70-tests/group.md) — Test harness, drift test, DOM tests

- [ ] [`task-31-jsdom-harness.md`](70-tests/task-31-jsdom-harness.md) · can start early
- [ ] [`task-32-unit-pipe-geometry.md`](70-tests/task-32-unit-pipe-geometry.md) · depends on 31, 08
- [ ] [`task-33-unit-friction.md`](70-tests/task-33-unit-friction.md) · depends on 31, 09
- [ ] [`task-34-unit-structure-loss.md`](70-tests/task-34-unit-structure-loss.md) · depends on 31, 11
- [ ] [`task-35-drift-test-fixture.md`](70-tests/task-35-drift-test-fixture.md) · depends on 31, 12
- [ ] [`task-36-import-roundtrip.md`](70-tests/task-36-import-roundtrip.md) · depends on 31, 26
- [ ] [`task-37-dom-event-tests.md`](70-tests/task-37-dom-event-tests.md) · depends on 31, 20

### [`80-gaps/`](80-gaps/group.md) — Focused gap fixes & tests

- [ ] [`task-40-hgl-method-dropdown.md`](80-gaps/task-40-hgl-method-dropdown.md) · HGL method `<select>` (spec §4.2)
- [ ] [`task-41-kb-unit-tests.md`](80-gaps/task-41-kb-unit-tests.md) · `kbAt` node tests (spec §8.1)
- [ ] [`task-42-svg-integrity-tests.md`](80-gaps/task-42-svg-integrity-tests.md) · SVG cross-view/depth-sort tests (spec §8.5)
- [ ] [`task-43-enter-expand-collapse.md`](80-gaps/task-43-enter-expand-collapse.md) · Enter expand/collapse (spec §4.3, §5.1)
- [ ] [`task-44-splitter-banner.md`](80-gaps/task-44-splitter-banner.md) · splitter detection + banner (spec §9.2)

### `81-v1-gaps/` — v1 gap features (design: `specs/2026-11-08-visualizer-v1-gaps-design.md`)

No per-task MDs; implementer prompts carry the design §3–§4 text verbatim.

- [ ] 81.1 analysis pass + import additions (§3.1–§3.3)
- [ ] 81.2 unified warning banner — splitter + missing Design Q (§4.1, §4.4)
- [ ] 81.3 walk-from switcher (§4.2)
- [ ] 81.4 splitter primary path in ledger (§4.3)
- [ ] 81.5 TR-55 callout cards + toggle (§4.5)
- [ ] 81.6 iso flow arrows + selection glow (§4.6–§4.7)
- [ ] 81.7 print current path calc-sheets (§4.8)
- [ ] 81.8 feature tests — analysis/xlsx/gap-ui (§6)
- [ ] 81.9 final build + verify (§7)

### [`90-deploy/`](90-deploy/group.md) — Build verification & GitHub Pages

- [ ] [`task-38-build-and-verify.md`](90-deploy/task-38-build-and-verify.md) · depends on all above
- [ ] [`task-39-ghpages-publish.md`](90-deploy/task-39-ghpages-publish.md) · depends on 38

---

## Execution notes for flash-model workers

Each task MD contains, in order:

1. **Context** — why this task exists, which spec section it implements.
2. **Preconditions** — prior tasks completed, files that must exist.
3. **Exact changes** — file paths, sentinel-comment insertion points, complete code.
4. **Acceptance test** — a self-contained test and the exact command to run it.
5. **Done when** — build succeeds, test passes, no prior-tests regressed.

**Do not** improvise beyond what the task MD says. If a task appears incomplete, flag it in a review comment rather than filling in details. The spec is reference material; the task MD is the instruction.

**Commit after every task.** One task = one commit. Commit message format: `feat(visualizer): task-NN <slug>` or `test(visualizer): task-NN <slug>` for test-only tasks.

**Never bypass hooks** (`--no-verify`) or add LLM attribution trailers.

---

## Gap closure — groups 80 & 81 (in scope)

The v1 gap audit found the seven items below. **All are in scope** and are
executed, after group 70, as two groups:

**Group 80 (task MDs in `80-gaps/`)** — focused fixes and tests:
HGL method dropdown (task-40), `kbAt` tests (task-41), SVG integrity tests
(task-42), Enter expand/collapse (task-43), splitter banner (task-44).

**Group 81 (design: `specs/2026-11-08-visualizer-v1-gaps-design.md`)** —
the seven verified v1 gaps:

1. **Splitter detection + warning banner** (§9.2, §4.1) — primary path only.
2. **Missing Design Q warning** (§4.4) — banner explains the flat segment.
3. **Multi-outfall detection + "Walk from…" switcher** (§4.2).
4. **TR-55 segment callout cards on profile** (§4.5).
5. **Printable current-path calc-sheets** (§4.8).
6. **Iso flow-direction arrows** (§4.6).
7. **Selection glow** (§4.7).

Groups 80 and 81 overlap only on the splitter banner; task-44's simple banner
is superseded by the richer group-81 banner that also covers missing Design Q.
Tasks in 81 are ordered by dependency (analysis first).
