# Group 50: Edit mode — overrides store, editable fields, JSON export

**Purpose:** Implement local, session-only overrides. Edits never mutate `state.imported`. Live ledger/view recomputation on every keystroke. Export tweaked JSON for later re-import.

**Tasks:**
- `task-23-overrides-store.md` — `setOverride`, `revertOverride`, `resetAllOverrides`, `resolveField`
- `task-24-editable-ledger-fields.md` — render inputs for Hf row (n, slope, length, size), Hb row (type, inflow angles), Start row (TW_elev)
- `task-25-override-badge-reset.md` — toolbar badge + detail panel listing every override with per-row revert
- `task-26-export-tweaked-json.md` — build and download the tweaked JSON with `_overrides` sidecar array

**Group acceptance criteria:**
- Entering edit mode via `E` hotkey flips `state.ui.mode = "edit"`; the expanded ledger row shows editable inputs.
- Typing in a slope input triggers `withFocusPreserved(renderAll)`; `state.overrides.byId["P-02"].slope = <new>`; focus stays in the same input.
- Override badge shows correct count; opening it lists every override with revert buttons.
- Clicking "Reset all" clears `state.overrides`; ledger returns to imported values.
- "Export tweaked JSON" writes a file with `_overrides` array; re-importing restores edit mode and the overrides.
- `state.imported` is byte-identical before and after any override operation.

**Spec references:** §6 (edit mode), §6.3 (export schema).
