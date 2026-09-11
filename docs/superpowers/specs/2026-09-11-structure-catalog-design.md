# Structure Catalog & Standard Selection — Design Spec

**Date:** 2026-09-11
**Feature:** Agency standard structure catalog for junction structures; dynamic K_ah from HEC-22 Table 9.4; remove structureType from inlet spacing tab.

---

## Problem

Junction structures currently require manual entry of all dimensions and use a fixed or uncategorized junction loss coefficient. Engineers working with Maryland agency standards (MCDOT, MDSHA, MDOT, PG County) must look up standard structure sizes separately. The inlet spacing tab has a redundant structure-type field that duplicates data from the junction structures tab.

---

## Scope

- `drainage-calculator/storm-drain-design-calculator.html` only (single-file rule).
- Additive changes to existing Junction Structures and Inlet Spacing tabs.
- No new tabs.

---

## Section 1: Data Model

New fields on every structure state object:

```js
{
  id, linkedInletId, rimElevation, /* existing */
  structureMode: "standard",   // "standard" | "custom"
  agency: "",                  // "mcdot" | "mdsha" | "mdot" | "pgder"
  standardStructureId: "",     // catalog entry id string (e.g. "pgder-mh-48")
  structureCategory: "",       // "inlet" | "access_hole" — for custom mode; derived from catalog for standard
  shape: "",                   // "round" | "rectangular" | "square" — for custom mode
  innerDiameter: "",           // ft — round structures
  innerWidth: "",              // ft — rectangular/square
  innerLength: "",             // ft — rectangular only
}
```

New structures default all new fields to `""` / `"standard"`. Existing structures loaded without these fields behave as if `structureMode: "custom"` with all dimensions blank (backward compatible — K_ah falls back to existing behavior).

**`structureCategory` resolution:**
```js
function resolveStructureCategory(s) {
  if (s.structureMode === "standard") {
    const entry = lookupCatalogEntry(s.agency, s.standardStructureId);
    return entry ? entry.category : "access_hole";
  }
  return s.structureCategory || "access_hole";
}
```

---

## Section 2: Junction Structures Tab UI (`renderStructures`)

### New columns (inserted before existing rim/detail/delete columns)

```
ID | Rim (ft) | Mode | Agency | Standard Structure | Inner Size | K_ah | [detail] | [del]
```

### Mode column

Toggle button: **Standard** / **Custom**. Mutates `structureMode`, clears catalog fields when switching to Custom, clears custom dimension fields when switching to Standard.

### Standard path (inline cascade)

When `structureMode === "standard"`:

1. **Agency dropdown** — `<select>` with options: MCDOT, MDSHA, MDOT, PG County DER. On change: clear `standardStructureId`, re-render.
2. **Structure dropdown** — `<select>` populated from `STRUCTURE_CATALOG[agency]`. Each option shows the entry label (e.g., "48-in MH (SD 21.1)"). On selection: auto-fill `innerDiameter` / `innerWidth` / `innerLength` from catalog entry. User may override dimension fields after auto-fill.
3. **Inner Size display** — read-only `<td class="out computed-cell">` showing populated dimension.

### Custom path

When `structureMode === "custom"`:

1. **Category dropdown** — "Inlet" | "Access Hole (Manhole/JB)". Sets `structureCategory`.
2. **Shape dropdown** — "Round" | "Rectangular" | "Square". Sets `shape`.
3. **Dimension inputs** — Round: `numInput(s, "innerDiameter", 65)`. Rectangular: `numInput(s, "innerWidth", 55)` × `numInput(s, "innerLength", 55)`. Square: single `numInput(s, "innerWidth", 65)`.

### K_ah display column

Read-only computed cell showing `kAhFromAngle(resolveStructureCategory(s), outPipe?.angle ?? 0).toFixed(2)` for the outgoing pipe. Shows `"—"` when no outgoing pipe.

All handlers route through `withFocusPreserved(renderAll)`.

---

## Section 3: K_ah Computation (`kAhFromAngle`)

Source: HEC-22, 4th Ed. (FHWA HIF-24-006), Table 9.4 — Approximate Method (Eq. 9.10).

```
H_ah = K_ah × V_o² / 2g
```

`pipe.angle` is the deflection angle (°) of the inflow pipe relative to the outflow pipe (0° = straight through). Interior angle θ = 180° − deflection.

```js
function kAhFromAngle(structureCategory, deflectionDeg) {
  const theta = 180 - (deflectionDeg || 0);   // interior angle
  if (structureCategory === "inlet") {
    // HEC-22 Table 9.4: straight→0.50, 90°→1.50; linear interpolation
    return 0.50 + (1.50 - 0.50) * ((180 - theta) / 90);
  }
  // access_hole: piecewise linear over Table 9.4 breakpoints
  const pts = [[180, 0.15], [157.5, 0.45], [135, 0.75], [120, 0.85], [90, 1.00]];
  for (let i = 0; i < pts.length - 1; i++) {
    const [t1, k1] = pts[i], [t2, k2] = pts[i + 1];
    if (theta >= t2) {
      return k1 + (k2 - k1) * ((t1 - theta) / (t1 - t2));
    }
  }
  return 1.00;  // theta < 90° — clamp at max
}
```

Insert near `calcPipeRow`. Exported on `__sdc` for test access.

### Backward compatibility

Existing structures with no `structureMode` treat as custom/access_hole with default angle 0° → K_ah ≈ 0.15 (straight run). This is a conservative improvement over any prior fixed value.

### Inlet Spacing tab — `renderInletSpacing` and `defaultInletSpacingRow()`

Remove `structureType` field and column entirely. Standalone rows (no linked junction structure) retain manual `W`, `a`, `n` inputs. The linked junction structure's catalog entry provides the inlet type label for display only — it does not auto-populate W/a/n (those remain engineer-entered).

---

## Section 4: Data Flow — HGL, Detail Sheets, Excel

### HGL computation (`calcStructureRow`)

Replace existing fixed K_b with dynamic lookup:

```js
const outPipe = pipes.find(p => p.id === calc.outPipeId);
const K_ah = kAhFromAngle(resolveStructureCategory(structure), outPipe?.angle ?? 0);
const Vo = calc.outPipeVelocity;
const H_ah = K_ah * (Vo * Vo) / (2 * 32.2);
```

No other change to HGL math.

### `buildStructureSheet` / `buildHglRowSheet` additions

In the junction loss section, add two display lines:

```
Structure:  [catalog label, e.g. "PG DER — 60-in MH (SD 21.2)"] or "Custom — Round, 5.0 ft"
K_ah:       0.75  (135° pipe angle, access hole)
H_ah:       0.08 ft
```

### Excel — Structures sheet

Add new columns after existing structure fields (export and import):

```
Structure Mode | Agency | Catalog ID | Category | Shape | Inner Dia (ft) | Inner W (ft) | Inner L (ft)
```

Missing columns on import (old files) silently map to `""`. `structureCategory` for standard-mode entries is re-derived from catalog at load time, not stored.

### Excel — Inlet Spacing sheet

Remove `structureType` column from export. Old files with that column: ignore on import (map to nothing).

---

## Section 5: `STRUCTURE_CATALOG` Constant

Keyed `agency → entries[]`. Each entry:

```js
{
  id: "pgder-mh-48",
  label: "48-in MH (SD 21.1)",
  category: "access_hole",   // "inlet" | "access_hole"
  shape: "round",
  innerDiameter: 4.0,        // ft
  innerWidth: null,
  innerLength: null,
  notes: "For 12–24 in pipes. PG DER SD 21.1 (Jan 2001)"
}
```

### PG County DER (pgder) — from SD Standard Details, Jan 2001

**Manholes (round, access_hole):**

| id | label | innerDiameter | notes |
|---|---|---|---|
| pgder-mh-48 | 48-in MH (SD 21.1) | 4.0 ft | 12–24 in pipes |
| pgder-mh-60 | 60-in MH (SD 21.2) | 5.0 ft | 27–36 in pipes |
| pgder-mh-72 | 72-in MH (SD 21.3) | 6.0 ft | 42–48 in pipes |
| pgder-mh-84 | 84-in MH (SD 21.4) | 7.0 ft | 54–66 in pipes |
| pgder-mh-96 | 96-in MH (SD 21.5) | 8.0 ft | 72-in pipes |

**Type A Masonry MH (round, access_hole) (SD 20.0):**

| id | label | innerDiameter | notes |
|---|---|---|---|
| pgder-mhA-48 | Type A MH, 4 ft (SD 20.0) | 4.0 ft | 15–24 in pipes |
| pgder-mhA-60 | Type A MH, 5 ft (SD 20.0) | 5.0 ft | 27–36 in pipes |
| pgder-mhA-72 | Type A MH, 6 ft (SD 20.0) | 6.0 ft | 42–48 in pipes |
| pgder-mhA-84 | Type A MH, 7 ft (SD 20.0) | 7.0 ft | 54–60 in pipes |

**Inlets (rectangular, inlet):**

| id | label | innerWidth | innerLength | notes |
|---|---|---|---|---|
| pgder-inlet-yardSD15 | Precast Yard Inlet (SD 15.0) | 4.0 ft | 4.0 ft | Square, SD 15.0 |
| pgder-inlet-typeE | Type E Inlet (SD 16.0) | 5.0 ft | 5.0 ft | Square, SD 16.0 |
| pgder-inlet-typeK | Type K Inlet (SD 17.0) | 3.0 ft | 3.0 ft | Square, SD 17.0 |
| pgder-inlet-typeA | Type A Drop Inlet (SD 10.0) | null | null | Dims from plans |
| pgder-inlet-typeB | Type B Drop Inlet (SD 11.0) | null | null | Dims from plans |
| pgder-inlet-typeCI | Type CI Inlet (SD 13.0) | null | null | Dims from plans |
| pgder-inlet-typeD | Type D Inlet (SD 14.0) | null | null | Dims from plans |

### MCDOT, MDSHA, MDOT

Catalog entries for these agencies require their respective standard detail booklets (not yet in project docs). During implementation, populate entries following the same schema. Seed with empty arrays for now so the agency dropdown options exist without crashing:

```js
const STRUCTURE_CATALOG = {
  mcdot:  [],   // populate from MCDOT standard details
  mdsha:  [],   // populate from MDSHA standard details
  mdot:   [],   // populate from MDOT standard details
  pgder:  [ /* entries above */ ],
};
```

---

## Self-Review

1. **Placeholder scan:** MCDOT/MDSHA/MDOT catalog entries are explicitly deferred with empty arrays — acknowledged gap, not an accidental omission.
2. **Internal consistency:** `kAhFromAngle` is the single K_ah read path. `resolveStructureCategory` is the single category read path. Both called from `calcStructureRow`, detail sheets, and the K_ah display column.
3. **Scope:** No new tabs. Changes confined to Junction Structures tab, Inlet Spacing tab, HGL calc, two detail builders, and Excel export/import.
4. **Ambiguity:** `pipe.angle` = deflection angle (0° = straight); spec explicitly converts to interior angle θ = 180° − Δ inside `kAhFromAngle` — no caller confusion possible.
5. **Backward compat:** Old structures with no `structureMode` fall into custom/access_hole path; K_ah defaults to near-0.15 (straight run) — reasonable default and non-breaking.
6. **PG County inlet dims null:** Several inlet types (A, B, CI, D) have no explicit interior dimensions in the SD sheets — entries included for catalog completeness with null dims, so the user still gets the label/type selection benefit.
