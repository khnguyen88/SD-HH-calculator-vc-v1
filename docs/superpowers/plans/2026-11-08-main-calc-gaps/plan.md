# Main Calculator Gap Audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix every identified gap between the main storm-drain calculator and its spec, and fill missing test coverage mandated by the spec.

**Architecture:** All fixes target `drainage-calculator/storm-drain-design-calculator-dev.html`. After each dev-file edit, run `node drainage-calculator/build.js` to regenerate the deployable file. Tests live in `tests/run-tests.mjs` (jsdom + node --test harness, already set up).

**Tech Stack:** Vanilla JS/HTML · Node `--test` runner · jsdom · xlsx npm package

**Spec:** `docs/superpowers/specs/2026-11-08-main-calc-gap-audit-design.md`

---

## Audit findings — what was checked and what was found

The full app (~6 741 lines) was audited section by section against `storm-drain-calculator-spec.md`.

**No gaps found in:**
- Manning's equation, friction slope, Hb controlling-angle (spec §1.4)
- TR-55 travel-time equations — sheet, shallow, channel (spec §1B.2)
- TR-55 sanity warnings (spec §1B.5)
- Flow-splitter primary/secondary Q, Hf/Hb split (spec Phase 2)
- Circular-segment geometry and orifice/weir regimes (spec §3.2–3.4)
- Stage-list generation and truncation warning (spec §3.5)
- Excel export: `bookSST:true`, `setFormula` with cached values, `safeSheetName`, hidden-not-grouped columns (spec §B.1–B.3, B.5)
- Focus preservation — every `oninput`/`onchange` that calls a render function is wrapped in `withFocusPreserved` (spec §A.2)
- Scroll-wheel blur handler on number inputs (spec §5.3)
- Spinner CSS hidden (spec §5.3)
- Jensen's inequality disclosure in Outlet Structure UI (spec §3.2)
- Formulas & Examples tab uses live functions (spec Phase 6)

**Gaps found (5 tasks):**

| Group | Task | Spec ref |
|-------|------|----------|
| 10-compliance | task-10-01: Print-All-Detail large-page warning | Phase 7 |
| 30-consistency | task-30-01: TR-55 detail sheet formulas not substituted | §1B.6 |
| 40-validation | task-40-01: Missing unit tests (circularSegment, frictionSlope, TR-55 eqs) | §C.1 |
| 40-validation | task-40-02: OOXML structural test | §B.4, §C.5 |
| 40-validation | task-40-03: Export/import round-trip test | §C.4 |

---

## Task group index

### [`10-compliance/`](10-compliance/group.md) — Spec compliance fixes
- [ ] [`task-10-01-print-large-warning.md`](10-compliance/task-10-01-print-large-warning.md)

### [`20-correctness/`](20-correctness/group.md) — Engineering correctness
*(No gaps found — all core equations match spec)*

### [`30-consistency/`](30-consistency/group.md) — Data consistency
- [ ] [`task-30-01-tr55-formula-substitution.md`](30-consistency/task-30-01-tr55-formula-substitution.md)

### [`40-validation/`](40-validation/group.md) — Validation / test coverage
- [ ] [`task-40-01-unit-tests-formula.md`](40-validation/task-40-01-unit-tests-formula.md)
- [ ] [`task-40-02-ooxml-structural-test.md`](40-validation/task-40-02-ooxml-structural-test.md)
- [ ] [`task-40-03-round-trip-test.md`](40-validation/task-40-03-round-trip-test.md)

---

## Execution notes

- Run `node drainage-calculator/build.js` after every dev-file change.
- Run `cd tests && node --test run-tests.mjs` to run the full test suite.
- One gap = one commit. Format: `fix(calculator): <slug>` or `test(calculator): <slug>`.
- **Never add LLM attribution trailers** to commits.
- Tasks 40-01, 40-02, 40-03 all modify `tests/run-tests.mjs` — serialize these; don't run in parallel.
