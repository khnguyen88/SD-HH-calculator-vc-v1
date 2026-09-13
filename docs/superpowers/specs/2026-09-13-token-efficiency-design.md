# Token Efficiency — SheetJS Extraction + Render Compression

**Date:** 2026-09-13
**Goal:** Cut LLM context cost per editing session and slim the app JS, without changing the deployed single-file offline HTML.

---

## Problem

`storm-drain-design-calculator.html` is 6,588 lines / 781 KB:

| Section | Lines | Size |
|---|---|---|
| SheetJS library (minified) | 17 | ~437 KB |
| App JS | 5,963 | ~317 KB |
| CSS | 516 | ~16 KB |
| HTML | ~92 | ~8 KB |

SheetJS (56% of the file by bytes) is pure noise for editing sessions. The app JS contains copy-pasted local helpers repeated across render functions.

---

## Constraints

- The deployed file must remain a single self-contained HTML — no CDN, no internet required, works by double-clicking.
- Data tables (NOAA Atlas 14, pipe dimensions, inlet library) are out of scope — they are reference data that must stay readable and verifiable.
- The `withFocusPreserved` / state-mutation patterns from the spec must not be disturbed.

---

## Section 1 — Dev/Deploy File Split

Two files live in `drainage-calculator/`:

| File | Contains SheetJS? | Purpose |
|---|---|---|
| `storm-drain-design-calculator-dev.html` | **No** (placeholder) | What developers and Claude edit — lean, LLM-friendly. Never shared with end users. |
| `storm-drain-design-calculator.html` | **Yes** (fully inlined) | Built output. What users download, clone, or open offline. Committed to `main`. Never hand-edited. |

`storm-drain-design-calculator.html` keeps its current name so anyone who clones the repo gets a working file immediately. The dev file is a new artifact that only the developer touches.

The SheetJS placeholder in the dev file:
```html
<script>/* SHEETJS_BUNDLE */</script>
```

SheetJS source extracted to `drainage-calculator/lib/sheetjs-bundle.js` and checked in as-is.

### Build script

`drainage-calculator/build.js` — Node.js, no dependencies beyond `fs`:

1. Read `storm-drain-design-calculator-dev.html`
2. Read `lib/sheetjs-bundle.js`
3. Replace `/* SHEETJS_BUNDLE */` with the bundle contents
4. Write (overwrite) `storm-drain-design-calculator.html`

Run with: `node drainage-calculator/build.js`

Always run the build and commit both files together. `storm-drain-design-calculator.html` in the repo is always the built output of `storm-drain-design-calculator-dev.html`.

### Deploy workflow update

`docs/deployment-runbook.md` must be updated to reflect:
1. Run `node drainage-calculator/build.js` before deploying
2. Copy `storm-drain-design-calculator.html` → `index.html` on `gh-pages` (unchanged from current workflow, just adds the build step first)

### Expected gain

~437 KB / ~56% reduction in context per editing session.

---

## Section 2 — Render/Logic Compression

### Target: copy-pasted local helper closures

At least three render functions independently define structurally identical `txt(row, field, w)` and `num(row, field, w)` closures:

| Location | Lines |
|---|---|
| Inside `renderDrainage()` | ~2537–2543 |
| Inside `renderStructures()` | ~2623–2629 |
| Inside `renderOutlet()` | ~3163–3169 |

`txtInput(row, field, w)` and `numInput(row, field, w)` are similarly duplicated inside `renderPipes()` (~2883–2889) and `renderOutlet()` (~3356–3364).

**Fix:** Extract to module-level utilities accepting a `rows` (state array) parameter. Each render function's local copy is deleted and replaced with a call to the shared version.

### Target: inline button markup

`delBtn` and `detailBtn` already exist at module level (lines 2332–2340). Any render functions that inline equivalent button markup instead of calling these get refactored to use the existing functions.

### Target: buildXxx detail sheet functions

`buildDrainageDetailSheet`, `buildStructuresDetailSheet`, `buildPipesDetailSheet`, `buildHglDetailSheet` (lines ~5392–5697) likely repeat the same `csSection` / `csTable` / `csFormula` skeleton. Where structure is truly identical, extract a shared builder. Where each is genuinely different, leave alone.

### Out of scope

- Data tables (NOAA Atlas 14, pipe dimensions, inlet library)
- Computation logic (`computeXxx`, `calcXxx`, `tr55Xxx`)
- `buildWorkbook` / Excel export block
- Print / CSS layer

### Expected gain

800–1,400 lines removed from app JS (~15–25% reduction).

---

## Section 3 — Section Markers for LLM Navigation

Add structured divider comments to the dev file's app JS so an LLM can be directed to a specific section by line range without loading the full file.

```
// ====== SECTION: Data Tables ======
// ====== SECTION: Hydrology / Rational Method ======
// ====== SECTION: TR-55 Travel Time ======
// ====== SECTION: Network Graph / Flow ======
// ====== SECTION: Pipe Hydraulics ======
// ====== SECTION: Outlet Rating Curves ======
// ====== SECTION: DOM Utilities ======
// ====== SECTION: State / Persistence ======
// ====== SECTION: Render — Overview ======
// ====== SECTION: Render — Drainage ======
// ====== SECTION: Render — Structures ======
// ====== SECTION: Render — Pipes ======
// ====== SECTION: Render — Outlet ======
// ====== SECTION: Render — Rainfall ======
// ====== SECTION: Render — Pipe Sizing ======
// ====== SECTION: Render — HGL ======
// ====== SECTION: Render — Inlet Spacing ======
// ====== SECTION: Calc Sheets ======
// ====== SECTION: Print ======
// ====== SECTION: Excel Export ======
// ====== SECTION: Excel Import ======
// ====== SECTION: Init ======
```

These markers go in the dev file (`storm-drain-design-calculator-dev.html`). The built `storm-drain-design-calculator.html` inherits them verbatim (~1 KB overhead, negligible).

---

## Combined Expected Outcome

| Metric | Before | After |
|---|---|---|
| Dev file (`-dev.html`) size | — (new file) | ~344 KB |
| Dev file lines | — | ~4,400–4,800 |
| LLM context per session | ~781 KB | ~344 KB (full dev file) or far less (targeted section read) |
| User-facing file (`storm-drain-design-calculator.html`) | ~781 KB, fully working | ~781 KB, fully working (unchanged for users) |
| Deployed GitHub Pages file | unchanged | unchanged |
