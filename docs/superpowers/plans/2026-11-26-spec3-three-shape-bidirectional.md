# Three-Shape Bidirectional Calculator + Visualizer — Index

> **For agentic workers:** this plan is split into phase-sized files to keep agent context small. Each phase file is self-contained — an agent dispatched to a single phase does NOT need to read the others.

**Spec:** [`docs/superpowers/specs/2026-11-26-spec3-three-shape-bidirectional-design.md`](../specs/2026-11-26-spec3-three-shape-bidirectional-design.md) is the source of truth for every decision.

**Goal:** Make the HTML calculator and visualizer both read and write Simple (legacy WIP + golden) and Robust (Simple + extras) xlsx shapes, with shape auto-detection on import, a user toggle on export, visual-style parity between templates, and real HGL formula wiring for the `hglMethod` toggle.

**Architecture:** Two shape readers and two shape writers, one shared internal `state`. Robust template built by loading the embedded golden `.xlsx` bytes (base64) as a styled base. HGL formulas branch on the `hglMethod` named range. A shared reader module (`xlsx-shape-reader.js`) is inlined into both calculator and visualizer builds.

**Tech Stack:** HTML + vanilla JS + SheetJS (inlined), Python 3.11 + openpyxl 3.1.5 + pytest, Node.js for `build.js`.

---

## Phase breakdown

Work the phases in order. Each phase ends with a commit sequence and a manual Excel verification; pause for review before the next phase starts.

| Phase | File | Tasks | Ship gate |
|---|---|---|---|
| Pre-work | [`2026-11-26-spec3/phase-pre-work.md`](2026-11-26-spec3/phase-pre-work.md) | 1–2 | DATA2 cleared, docs corrected |
| 1 — Simple reader | [`2026-11-26-spec3/phase-1-simple-reader.md`](2026-11-26-spec3/phase-1-simple-reader.md) | 3–7 | Calculator imports WIP + golden |
| 2 — Robust template rebuild | [`2026-11-26-spec3/phase-2-robust-template.md`](2026-11-26-spec3/phase-2-robust-template.md) | 8–13 | Robust export looks like Simple; extras populate |
| 3 — Simple writer + toggle UI | [`2026-11-26-spec3/phase-3-simple-writer.md`](2026-11-26-spec3/phase-3-simple-writer.md) | 14–17 | Export toggle works both shapes |
| 4 — HGL method wiring | [`2026-11-26-spec3/phase-4-hgl-wiring.md`](2026-11-26-spec3/phase-4-hgl-wiring.md) | 18–20 | Config!B5 flip changes HGL in Excel |
| 5 — Visualizer parity | [`2026-11-26-spec3/phase-5-visualizer.md`](2026-11-26-spec3/phase-5-visualizer.md) | 21–23 | Visualizer imports both shapes |

---

## Shared conventions (read once, apply everywhere)

- **Working directory:** shell commands assume CWD = repo root (`C:\_AAA\WS_HH\SD-HH-calculator-vc-v1`). Paths are relative to that root.
- **After every edit in `drainage-calculator/`:** run `node drainage-calculator/build.js` to regenerate `storm-drain-design-calculator.html`. CLAUDE.md requires this after every dev-file edit.
- **Checkbox tracking:** steps use `- [ ]` syntax so the executing-plans / subagent-driven-development skill can tick off progress.
- **Commits:** no LLM attribution trailers (per project memory).

---

## File structure

### New files

- `docs/template-analysis/cleanup_data2.py` — one-shot DATA2 cleanup script.
- `docs/template-analysis/test_cleanup_data2.py` — DATA2 cleanup invariants.
- `docs/template-analysis/test_hgl_method_formula_branches.py` — HGL formula branch content.
- `docs/template-analysis/test_hgl_method_round_trip.py` — HGL method flip changes values.
- `docs/template-analysis/test_shape_detect.py` — detectShape returns correct values.
- `docs/template-analysis/test_simple_reader.py` — Simple-shape fixture round-trip.
- `docs/template-analysis/test_robust_reader.py` — Robust-shape fixture round-trip.
- `docs/template-analysis/test_simple_writer.py` — Simple writer round-trip.
- `docs/template-analysis/test_robust_writer.py` — Robust writer round-trip.
- `docs/template-analysis/test_visualizer_reader_parity.py` — shared-reader parity.
- `docs/template-analysis/fixtures/build_robust_minimal.py` — minimal Robust fixture generator.
- `docs/template-analysis/fixtures/robust_minimal.xlsx` — generated fixture.
- `docs/template-analysis/fixtures/robust_roundtrip.xlsx` — manual-export fixture.
- `drainage-calculator/lib/xlsx-shape-reader.js` — shared reader module.

### Modified files

- `drainage-calculator/storm-drain-design-calculator-dev.html` — import dispatch; `buildSimpleWorkbook` + `buildRobustWorkbook`; shape toggle UI; embed base64 golden bytes.
- `drainage-calculator/build.js` — inline `xlsx-shape-reader.js` + base64-encode `docs/template_golden.xlsx` into dev HTML.
- `visualizer/storm-drain-visualizer-dev.html` — import dispatch via shared reader.
- `docs/template-analysis/repair.py` — add DATA2-cleanup pass.
- `docs/template-analysis/build_golden.py` — add HGL method wiring edit.
- `docs/template-analysis/01-storm-drain-comps.md` — correct R/S column labels.
- `docs/template-analysis/05-c-factor.md` — correct I vs W Tc lookup citation.
- `docs/template-analysis/calculator-import-contract.md` — bump Contract-Version to 2.
- `docs/template-analysis/conftest.py` — re-pin `WIP_SHA256` after cleanup.
- `docs/template_wip_new.xlsx` — regenerated after DATA2 cleanup.
- `docs/template_golden.xlsx` — regenerated after DATA2 cleanup + HGL wiring.

### Not modified

`drainage-calculator/lib/sheetjs-bundle.js` (SheetJS source); the other per-tab analysis markdowns; the backup `template_wip_new_pre-repair.xlsx` (frozen reference).

---

## Final self-review checklist

Run at the end, after Phase 5 Task 23:

- [ ] Grep every phase file for `TBD`, `TODO`, `FIXME`, `fill in` — zero hits.
- [ ] Every file-path reference matches reality after Task 7 scaffolding.
- [ ] `state.exportShape` set in all three places: initial state (Task 7), Simple-import branch (Task 7), Robust-import branch (Task 21).
- [ ] `syncShapeRadio()` called from all three locations.
- [ ] `_legacyBuildWorkbook` deleted (Task 16 Step 16.2) — not dead code.
- [ ] Pytest total: 64 pre-existing + 2 cleanup + 4 shape-detect + 6+ simple-reader + 3 robust-writer + 2 HGL branch + 2 robust-reader + 1 visualizer-parity ≈ 84+ tests, all passing.

---

## Cross-reference: spec sections → phase files

| Design doc section | Implementation |
|---|---|
| Spec §3 Pre-work | [phase-pre-work.md](2026-11-26-spec3/phase-pre-work.md) |
| Spec §4 Architecture | [phase-1-simple-reader.md](2026-11-26-spec3/phase-1-simple-reader.md) Task 3, [phase-2-robust-template.md](2026-11-26-spec3/phase-2-robust-template.md) Task 12 |
| Spec §5 Simple reader | [phase-1-simple-reader.md](2026-11-26-spec3/phase-1-simple-reader.md) |
| Spec §6 Robust template structure | [phase-2-robust-template.md](2026-11-26-spec3/phase-2-robust-template.md) |
| Spec §7 Simple writer + toggle | [phase-3-simple-writer.md](2026-11-26-spec3/phase-3-simple-writer.md) |
| Spec §8 HGL method wiring | [phase-4-hgl-wiring.md](2026-11-26-spec3/phase-4-hgl-wiring.md) |
| Spec §9 Visualizer parity | [phase-5-visualizer.md](2026-11-26-spec3/phase-5-visualizer.md) |
| Spec §13 Contract version bump | [phase-5-visualizer.md](2026-11-26-spec3/phase-5-visualizer.md) Task 23 |
