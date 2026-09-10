# LocalStorage Save / Delete ("Quick Save") — Design Spec

**Date:** 2026-09-10
**Status:** Approved

---

## Overview

Add a lightweight "quick save" system to the header bar so users can snapshot and restore full project states within the browser. The Excel export workflow remains the permanent, portable record. This feature is explicitly browser-local and scoped to up to 5 named saves.

**Note:** This intentionally overrides the spec's prior "no localStorage" rule. That rule was written to prevent implicit/auto-save. This feature is fully explicit — the user triggers every save, load, and delete. The UI will make the browser-local nature clear.

---

## Data Model

**localStorage key:** `sdCalc_saves`

**Value:** JSON array of save objects (max 5 entries):
```json
[
  {
    "id": "<uuid>",
    "name": "My Project — 2026-09-10 14:32",
    "projectName": "My Project",
    "savedAt": 1725977520000,
    "state": { ...full state snapshot... }
  }
]
```

**State snapshot includes:**
- All state arrays: `drainage`, `structures`, `pipes`, `outletStructures`, `outletDevices`, `kb`, `inletSpacing` (and any other top-level arrays on the `state` object)
- `projectName` stored as a top-level field on the save entry (not inside `state`) for clean restoration on Load

**Save name format:** `"<projectName> — <YYYY-MM-DD HH:MM>"` — generated at save time, no user prompt.

---

## Behavior

### Save
- Reads current `state` object + project name field value.
- Appends a new entry to the `sdCalc_saves` array in localStorage.
- If the array is already at 5 entries, the Save button is disabled (tooltip: "Delete a save first").
- No confirmation dialog — immediate write.

### Load
- Replaces the live `state` object with the snapshot's `state`.
- Sets the `#projectName` input value to the save entry's `projectName` field.
- Calls `renderAll()` to redraw the UI.
- Closes the popover.
- No confirmation dialog — the user can save before loading if they want to preserve current state.

### Delete
- Removes the entry from the `sdCalc_saves` array by `id`.
- Writes the updated array back to localStorage.
- Re-renders the popover list in place.
- If the array drops below 5, the Save button re-enables.

---

## UI

### Header bar additions (right of existing Export/Import buttons)

1. **`Save` button** — `btn btn-sm` class, label "Save". Disabled with tooltip when at 5-save limit.
2. **`Saves ▾` button** — `btn btn-sm` class, opens/closes the saves popover. Badge showing current count (e.g., "Saves (3) ▾").

### Saves popover
- Absolutely positioned below the `Saves ▾` button.
- Closes on outside click.
- If no saves: shows a hint line "No saves yet."
- Each save row:
  - Save name + formatted timestamp (monospace)
  - **Load** button (`btn btn-sm`)
  - **✕** delete button (`btn btn-sm btn-danger` or equivalent destructive style)
- Max height with scroll if somehow needed (unlikely at ≤5 entries).

### Styling
- Matches existing dark aesthetic: `var(--panel)` background, `var(--border)` border, `var(--font-mono)` for timestamps.
- No new CSS variables — reuse existing tokens.

---

## Edge Cases

| Scenario | Behavior |
|---|---|
| localStorage unavailable (private browsing, quota exceeded) | Catch error, show a brief inline warning: "Browser storage unavailable." No crash. |
| Corrupt/unparseable saves data | Treat as empty — reset key to `[]`. |
| State shape mismatch on load (future version) | Load proceeds; missing fields default to empty arrays (same resilience as Excel import). |
| At 5 saves, user tries to save | Save button disabled, tooltip explains why. |

---

## Constraints

- Single HTML file — all JS/CSS inline, no new dependencies.
- No auto-save. Every persistence action is explicit user intent.
- UI clearly labels saves as "Saved in this browser only" (subtitle in popover header).
- CLAUDE.md / spec "no localStorage" rule is superseded by this design for this feature only.
