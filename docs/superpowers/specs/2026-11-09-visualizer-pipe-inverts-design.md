# Visualizer Pipe Inverts — Design Spec

**Date:** 2026-11-09
**App:** `visualizer/storm-drain-visualizer-dev.html`
**Status:** approved design — pipe-end crown floors, confirmed in session

---

## Goal

Bring pipe invert elevations (US and DS) into the visualizer so the profile
draws true geometry (including drop structures) and the HGL/EGL walk clamps
at the physically correct pipe-end crowns instead of the neighboring
structure's outgoing-pipe crown. Also surface drop structures and
slope/invert inconsistencies as warning-banner items.

Motivating case (user-supplied): a manhole whose outgoing pipe has
US invert 90 and whose incoming pipe has DS invert 100 — a 10-ft drop inside
the structure. Today the incoming pipe's HGL floor is taken from the *wrong*
pipe's crown (the MH's outgoing 24″ crown ≈ 92 ft instead of the incoming
pipe's own soffit ≈ 101.5 ft), and the profile silently floats on
EGL-relative fallbacks (`invert = EGL − 3`).

---

## Background — current behavior (verified)

- **Profile** (`profileStations`, lines 1258–1305): stations advance by pipe
  `length` only. Vertical anchors come from structure fields
  (`startElev`, `crown`, `rim`) with EGL-relative fallbacks
  (`invert = row.after − 3`, `crown = row.after`, `rim = row.after + 3`).
  Slope is never used for vertical geometry. Pipe rows take invert/crown from
  the **From** structure (lines 1283–1291).
- **HGL walk** (`annotateLedgerHgl`, lines 546–549): each pipe step passes
  `crownDn = crownOf(pipe.toId)` and `crownUp = crownOf(pipe.fromId)` — the
  To/From structure's `crown` field, which the calculator defines as the
  crown of that structure's **outgoing** pipe. `hglWalkStep` (509–516):
  `hglDn = max(EGL_dn − V²/2g, crownDn)` in both methods;
  `hglUp = max(hglDn + Hf, crownUp)` only under `legacy-both-crown`.
- **xlsx importer** (pipe mapping, lines 886–899): reads `ID`, `From
  Structure`, `To Structure`, `Angle (deg)`, `Shape`, `Size`, `n`, `Slope`,
  `Length`, `Design Q`, `Split Role`, `Hf (ft)` — drops the calculator's
  exported `US Invert (ft)` / `DS Invert (ft)` columns.
- **JSON schema** (`validateImportedJson`, 574–648): pipes have no invert
  fields.
- **Calculator export** already includes `US Invert (ft)` (col H) and
  `DS Invert (ft)` (col I) on the Pipe Sizing sheet — no calculator change
  is needed.

---

## Data model

### Pipe fields (optional, backward compatible)

```js
{ id, fromId, toId, shape, size, n, slope, length, angle, splitRole, designQ,
  usInvert: <number|null>, dsInvert: <number|null> }
```

- **xlsx importer**: `usInvert: pickNum(r["US Invert (ft)"], r.usInvert)`,
  `dsInvert: pickNum(r["DS Invert (ft)"], r.dsInvert)` in the pipe object
  literal (lines 886–899). Blank cells → undefined → stored as absent.
- **JSON schema**: if present, `usInvert`/`dsInvert` must be finite numbers
  (same validation style as `designQ`, line 632). Absent on old files — no
  breakage.
- **`_overrides` sidecar**: inverts participate in override handling like any
  other pipe field (no special-casing; `isSafeOverrideKey` already guards
  prototype pollution).

### Derived structure flowline (no new structure field)

A structure's flowline/invert is derived for drawing and display, never
stored on the structure:

```
flowline(S) = outgoing pipe usInvert            (if present)
            else min(incoming pipes' dsInvert)  (if any present)
            else null (fall through to existing EGL-relative fallback)
```

For an outfall (no outgoing pipe) the incoming pipes' dsInvert applies.
Rationale: pipes already carry both ends; a separate structure invert field
would be redundant data that can silently disagree with the pipes.

### Barrel height helper

New small helper `pipeBarrelHeightFt(shape, size)`:
circular → `size / 12` (size in inches); elliptical → RISE portion of the
`SPANxRISE` string `/ 12` (e.g. `"38x24"` → 2.0 ft). Used by the walk floors
and the profile crown derivation.

---

## Profile drawing — true geometry

`profileStations` gains invert awareness:

- **Pipe rows with inverts**: each pipe contributes its true elevations at
  both ends — at the To-structure station `invert = dsInvert`, at the
  From-structure station `invert = usInvert`; `crown = invert +
  pipeBarrelHeightFt(shape, size)` at the same stations. A 10-ft drop
  structure draws as the vertical invert step it really is.
- **Structure stations**: the invert polyline point uses the derived
  flowline (above) instead of the current `startElev`-or-`EGL − 3` when
  inverts exist. Rim bars and crown anchors keep their current sources
  (`rim`, `crown` fields), which the calculator already exports.
- **Fallbacks unchanged**: when no inverts are present anywhere, the
  profile behaves exactly as today (structure fields → EGL-relative
  fallbacks). Mixed networks (some pipes with inverts) use per-pipe
  fallbacks independently.

---

## HGL walk — pipe-end crown floors

`annotateLedgerHgl` (call site lines 546–549) changes to:

```js
const step = hglWalkStep(row.before, V,
  pipe ? pipeCrownAt("dn", pipe) : null,   // dsInvert + barrel height, else crownOf(pipe.toId)
  pipe ? pipeCrownAt("up", pipe) : null,   // usInvert + barrel height, else crownOf(pipe.fromId)
  row.delta, method);
```

where `pipeCrownAt` prefers the pipe's own end invert + barrel height and
falls back to the current structure-`crown` value when that end's invert is
absent. Per-end independence: a pipe with only `dsInvert` gets the corrected
downstream floor and the old upstream floor.

Method semantics are unchanged: the downstream floor
(`hglDn = max(EGL_dn − V²/2g, crownDn)`) continues to apply in **both**
methods; the upstream pin (`hglUp = max(hglDn + Hf, crownUp)`) remains
**legacy-both-crown only**. With inverts, both floors are the pipe's own
soffits — for the motivating example, the incoming pipe's downstream floor
becomes `100 + 1.5 = 101.5 ft`, not the outgoing pipe's `≈ 92 ft` crown.

The EGL chain itself (boundary selection, Hf, Hb) is untouched — inverts
never add an elevation-drop term to the energy walk (see the drop-structure
discussion in the session record: the drop enters through the crown floor,
not the loss equation).

---

## Warnings

Both computed in the analysis pass (`analyzeImported`, ~lines 1043–1089) and
rendered through the existing warning banner
(`renderWarningBanner` 2646–2731, signature-based skip, dismiss +
reset-on-reimport semantics unchanged).

### Drop structures

For every non-outfall structure with an outgoing pipe and ≥ 1 incoming pipe
carrying inverts:

```
dropFt = min(incoming dsInvert) − outgoing usInvert
```

If `dropFt > 0.5`, record
`{ structureId, dropFt, fromInvert, toInvert, incomingPipeIds, outgoingPipeId }`.

Banner line, e.g.:
> *Drop structure MH-1: 10.00 ft drop inside structure (invert 100.00 →
> 90.00) — incoming pipe treated as free outfall; HGL floored at the pipe
> crown.*

### Slope / invert consistency

For each pipe with `usInvert`, `dsInvert`, and `length > 0`: computed slope =
`(usInvert − dsInvert) / length`. Flag when
`|computed − declared| > max(0.002, 0.2 × |declared|)`. Banner line names
the pipe and both slopes. (Advisory only — never mutates data.)

---

## Built-in samples

- **calculator-demo**: the 5 pipes gain the demo's real inverts —
  P1 102.00/101.00, P2 101.96/101.00, P3 101.00/100.60, P4 100.60/100.00,
  P5 97.60/97.00 (US/DS). The drift test maps
  `Number(p.upstreamInvert)` / `Number(p.downstreamInvert)` from the
  calculator's `seedExample()` state (blank → null) and pins them, so the
  sample can never drift from the calculator demo.
- **bburg-simplified**: B1 (I-1→MH-1, 15″) 68.15/67.35; B2 (MH-1→CULVERT,
  24″) 67.35/67.00 — the values already implied by the spec's crown math
  (67.0 + 0.35 drop; 68.15 + 1.25 dia), now explicit.

---

## Testing (`visualizer/visualizer-tests/`)

Harness: existing `_harness.js` (`loadVisualizer`, `fn(name)`), node:test,
CommonJS.

1. **Schema** — `usInvert`/`dsInvert` optional: absent passes; present
   finite number passes; non-number fails with a field-named error.
2. **xlsx import** — a synthetic workbook row with `US Invert (ft)` /
   `DS Invert (ft)` imports into `usInvert`/`dsInvert`; the real main-app
   export fixture round-trips unchanged.
3. **Walk floors** — the motivating network: OUT (outfall, tailwater 89),
   MH, UP; pipe A MH→OUT 24″ usInv 90/dsInv 89, pipe B UP→MH 18″
   usInv 101/dsInv 100, both n 0.013. Assert pipe B's downstream HGL floors
   at `100 + 1.5 = 101.5` (not at the MH's structure crown ≈ 92), in both
   HEC-22 (via the crownDn floor) and legacy (also the upstream pin at
   `101 + 1.5`). Assert a pipe without inverts still uses the structure
   crown (old behavior).
4. **Profile stations** — with inverts, station points carry true pipe-end
   inverts (assert B's To-station invert = 100 and From-station invert =
   101); without inverts, fallback values match today's output.
5. **Warnings** — drop banner fires at a 10-ft drop with correct text and
   stays silent at a 0.4-ft drop; slope-mismatch banner fires on
   `(usInv − dsInv)/L` disagreeing with `slope`, silent when consistent.
6. **Drift guard** — extended mapping pins the calculator-demo sample's
   inverts against `seedExample()`.
7. **Regression** — all 99 existing tests stay green (old imports without
   inverts are byte-for-byte the same behavior).

---

## Scope

- Visualizer only (dev HTML + tests). No calculator changes — the export
  already carries the inverts; no changes to the accepted file formats
  (additions are optional fields/columns).
- Out of scope: iso-view elevation labels (iso already draws structures at
  `z = rim`); changing HEC-22 loss equations; a partial-flow analysis
  engine for free-drop pipes (the crown floor is the conservative
  treatment, consistent with the MoCo workbook's max(crown, HGL) rule and
  with the calculator's planned conservative crown-pin toggle).
- Deployment unchanged: `visualizer/build-visualizer.js`, gh-pages runbook.
