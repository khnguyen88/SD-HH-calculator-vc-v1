# Structure Linking, HGL Tab & Tab Reorganization — Design Spec

## 1. Goal

Three interconnected improvements:

1. **Inlet Spacing ↔ Junction Structure link** — each inlet spacing row can optionally reference an
   `type="inlet"` junction structure. When linked, `area`, `C`, and `Tc` auto-fill from that
   structure's attached drainage area row. The user may override any auto-filled value.
2. **Drainage Area reverse display** — the DA table gains a read-only "Structure" column showing
   which junction structure references each DA row.
3. **HGL tab** — split the Junction Structures tab into (a) inputs-only "Junction Structures" and
   (b) a new "HGL" tab showing computed hydraulic results (HGL elevation, headloss, crown/rim checks).
4. **Pipe Sizing renamed** to "Pipe Sizing & Capacity" everywhere (tab label, 25-yr tab label,
   detail sheet headers).
5. **Tab reorder** — Inlet Spacing moves from tab 10 to tab 5 (immediately after Junction
   Structures); HGL becomes tab 7 (after Pipe Sizing & Capacity).

---

## 2. Data Model Changes

### 2.1 Inlet Spacing row — new field

Add to `defaultInletSpacingRow()`:

```js
linkedStructureId: "",   // internal id (state.structures[].id) of a type="inlet" structure, or "" = custom
```

Existing fields `label`, `area`, `C`, `tc`, `iOverride` are unchanged in storage. Their effective
values when `linkedStructureId` is set follow the resolution rules in §4.

**Import migration:** if an imported inlet spacing row has no `linkedStructureId` field, default to `""`.

### 2.2 No changes to Junction Structures or Drainage Area state

The `drainageAreaId` field on structures remains the canonical link. The DA table's "Structure"
column is a computed display — no new stored field.

---

## 3. UI Changes

### 3.1 Inlet Spacing tab — "Structure" column

Add a new **first column** "Structure" to the inlet spacing table header and body rows.

**Dropdown contents:**
- First option: `["", "Custom"]` — free-text label behavior (current default)
- Then one option per `state.structures` entry where `type === "inlet"`, formatted as:
  `structureId` (e.g. "ST-1")
- Options rendered in the order structures appear in `state.structures`

**onchange behavior:**
```js
oninput: (e) => {
  row.linkedStructureId = e.target.value;
  // if linking, auto-clear area/C/tc only if they were previously auto-filled
  // (do not wipe user-typed overrides — leave existing values as overrides)
  withFocusPreserved(renderAll);
}
```

**`label` field behavior:**
- When `linkedStructureId !== ""`: `label` auto-shows the linked structure's `structureId`.
  The label input is rendered read-only (disabled, dimmed).
- When `linkedStructureId === ""`: `label` is editable free-text as before.

**`area`, `C`, `tc` field behavior:**
- Use `resolvedInletFields(row)` (§4) to get effective values.
- If the value is auto-filled from the linked DA (`fromDA === true` for that field) and the row's
  stored field is blank: render the input with `placeholder = resolved value` and dimmed style
  + a small `← DA` badge next to the field.
- If the user has typed a value (stored field is non-blank): render with orange border
  (`.i-override` pattern), indicating a manual override.
- If no structure linked or structure has no DA: render as plain inputs (current behavior).

### 3.2 Drainage Area table — "Structure" column (read-only)

Add a read-only **last computed column** "Structure" before the detail/delete buttons.

**Value:** look up which `state.structures` entry has `drainageAreaId === row.id`. Display that
structure's `structureId`. If none references this DA row, display `"—"`.

This is a pure display — no stored field, computed fresh each render.

### 3.3 Junction Structures tab — remove HGL output columns

Remove from the Junction Structures table:
- Upstream HGL elevation column
- Headloss Hm column
- Crown check column
- Rim check column

Keep in Junction Structures:
- Structure ID, Description, Type (inputs)
- Drainage Area link dropdown (`drainageAreaId`)
- Crown (ft), Rim (ft), Start Elevation inputs
- Kb selection
- Total flow Q (computed display — useful context while defining structures)
- Detail sheet button, Delete button

### 3.4 New "HGL" tab — `renderHgl()`

New function `renderHgl()` renders `<div id="view-hgl">`.

**Banner:** none (primary design tab, not read-only).

**Table columns:**

| Column | Source |
|---|---|
| Structure ID | `row.structureId` |
| Type | `row.type` |
| Total Q (cfs) | `computeTotalFlow(row.id).Q` |
| Upstream HGL (ft) | `computeStructureCalc(row.id).elevation` |
| Headloss Hm (ft) | `computeStructureCalc(row.id).Hm` (if available) |
| Crown (ft) | `row.crown` (input) |
| Crown Check | HGL ≤ crown + 1.0 ft → ✓ else ✗ > crown+1 |
| Rim (ft) | `row.rim` (input) |
| Rim Check | HGL ≤ rim − 1.0 ft → ✓ else ✗ FLOOD |

Crown/Rim check failures render in red (`color:#e05; font-weight:700`).

**Empty state:** "No structures defined." hint.

No inputs on this tab — all values are computed from Junction Structures + Pipe Sizing data.

### 3.5 HGL — 25-yr tab updates

`renderStructures25()` (the existing 25-yr HGL tab) already shows the same columns as the new HGL
tab. Its label changes from "Junction Structures — 25-yr" to "HGL — 25-yr". No logic changes needed.

---

## 4. `resolvedInletFields(row)` helper

```js
function resolvedInletFields(row) {
  const out = { area: row.area, C: row.C, tc: row.tc,
                areaFromDA: false, CFromDA: false, tcFromDA: false };
  if (!row.linkedStructureId) return out;
  const st = state.structures.find(s => s.id === row.linkedStructureId); // internal id
  if (!st || !st.drainageAreaId) return out;
  const da = findDrainage(st.drainageAreaId);
  if (!da) return out;
  if (row.area === "" || row.area == null) { out.area = da.area; out.areaFromDA = true; }
  if (row.C   === "" || row.C   == null) { out.C   = da.C;    out.CFromDA   = true; }
  if (row.tc  === "" || row.tc  == null) { out.tc  = da.tc;   out.tcFromDA  = true; }
  return out;
}
```

Note: the lookup uses `st.id` (the internal UUID-style id), not `st.structureId` (the user-visible label string). The existing `findStructure(id)` helper searches by internal id — use it directly.

`computeInletRow(row, settings, bypassQIn, bypassCAIn)` calls `resolvedInletFields(row)` to get
effective `area`, `C`, `tc` before computing — replacing direct reads of `row.area`, `row.C`,
`row.tc`.

`renderInletSpacing()` calls `resolvedInletFields(row)` to determine which field values to show
as auto-filled vs. overridden.

---

## 5. Tab Order

Replace the `getTabs()` function tab list:

| # | ID | Label | Visibility |
|---|---|---|---|
| 1 | `overview` | Overview | always |
| 2 | `rainfall` | Rainfall & IDF | always |
| 3 | `drainage` | Drainage Area (Q=CiA) | always |
| 4 | `structures` | Junction Structures | always |
| 5 | `inlet-spacing` | Inlet Spacing | always |
| 6 | `pipes` | Pipe Sizing & Capacity | always |
| 7 | `hgl` | HGL | always |
| 8 | `outlet` | Outlet Structure | always |
| 9 | `formulas` | Formulas & Examples | always |
| 10 | `table46` | Table 4-6 Reference | always |
| 11 | `kb` | Kb Coefficients | always |
| 12 | `pipe-sizing-25` | Pipe Sizing & Capacity — 25-yr | conditional |
| 13 | `hgl-25` | HGL — 25-yr | conditional |

**Tab id notes:** The `"pipes"` tab id stays `"pipes"` — only its label string changes. The `"structures"` tab id stays `"structures"`. Rename: tab id `"structures-25"` → `"hgl-25"`. The view div id changes from
`view-structures-25` to `view-hgl-25`. The `renderStructures25()` function renames to
`renderHgl25()`.

**Active tab guard:** if `state.active` is `"pipes"` and the tab id changes — keep `"pipes"` valid
since the id stays. If `state.active === "structures-25"`, reset to `"hgl"`.

---

## 6. Rename "Pipe Sizing" → "Pipe Sizing & Capacity"

Update these strings:
- `getTabs()` label for `"pipes"`: `"Pipe Sizing & Capacity"`
- `getTabs()` label for `"pipe-sizing-25"`: `"Pipe Sizing & Capacity — 25-yr"`
- `renderPipeSizing()` heading `<h1>`: `"Pipe Sizing & Capacity"`
- `renderPipeSizing25()` heading `<h1>`: `"Pipe Sizing & Capacity — 25-yr"`
- Overview step list entry for Pipe Sizing

No logic changes.

---

## 7. Excel Export / Import

### 7.1 Inlet Spacing sheet — new `Linked Structure` column in settings rows

Add a settings row in the inlet spacing sheet header block:

```
# Linked Structure | ST-1
```

For each inlet row data row, add a `Linked Structure` column showing the linked structure's
`structureId` (user-visible), or `""` if custom.

**Import:** on import, for each inlet row, look up `state.structures` by `structureId` string to
resolve the internal `linkedStructureId`. If no match found, leave `linkedStructureId = ""`.

### 7.2 Drainage Area sheet — "Structure" column (computed, export-only)

Add a read-only `Structure` column to the Drainage Area export (rightmost, before Q columns),
showing the structure `structureId` that references this DA row. Import ignores this column.

---

## 8. `renderHgl()` view div and wiring

Add `<div class="view" id="view-hgl"></div>` to the HTML alongside the other view divs.

Wire `renderHgl()` into `renderAll()` — call it after `renderPipeSizing()` and before `renderOutlet()` (matching tab order).

Also add `renderHgl25()` call in `renderAll()` (replacing the old `renderStructures25()` call).

The existing `<div class="view" id="view-structures-25"></div>` renames to
`<div class="view" id="view-hgl-25"></div>`.

---

## 9. Known Limitations (out of scope)

- A junction structure can be referenced by at most one inlet spacing row (the dropdown
  shows all inlets regardless of whether they're already linked elsewhere — no uniqueness
  enforcement). Duplicate linking produces no error; both rows auto-fill from the same DA.
- The HGL tab has no detail sheets or Print All integration in this pass.
- The DA "Structure" column shows only the first structure referencing that DA if multiple
  structures share the same `drainageAreaId` (unusual but possible).
