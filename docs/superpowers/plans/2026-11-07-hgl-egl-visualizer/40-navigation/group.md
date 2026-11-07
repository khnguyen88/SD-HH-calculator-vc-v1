# Group 40: Navigation — cursor, arrow walk, branch popup

**Purpose:** Wire the keyboard-first navigation model. Cursor walks the network upstream by default; branch popup handles multi-inflow junctions; free-roam toggle and Shift+Arrow nudging live here too.

**Tasks:**
- `task-18-cursor-state.md` — `initialCursor`, `advanceCursor`, `retreatCursor` state helpers
- `task-19-arrow-walk-upstream.md` — document-level `keydown` handler for `↑/↓/Enter/Esc`
- `task-20-branch-popup.md` — modal when a structure has >1 upstream pipes
- `task-21-free-roam-toggle.md` — settings toggle + click-to-start behavior
- `task-22-shift-arrow-nudge.md` — `Shift+Arrow` in edit mode moves selected structure in iso

**Group acceptance criteria:**
- `↑` at outfall advances the cursor onto the first upstream pipe; the ledger grows from 1 to 2 rows.
- At a 2-inflow junction, `↑` opens the branch popup; `↑/↓` cycle options; `Enter` closes popup and advances.
- `↓` pops the last row; ledger shrinks.
- `Esc` with branch popup open: closes popup without changing cursor; without popup: resets walk to start.
- Chosen branch is remembered in `state.ui.branchChoices.byStructureId`; retracing does not re-prompt.
- Free-roam mode: cursor starts wherever the user first clicks; `↑/↓` move by graph direction; branch popup never fires.
- Shift+Arrow (edit mode only): moves selected structure's world x/y by 10 ft/step; iso re-renders; `state.overrides.byId[sid].x/.y` set.

**Spec references:** §5 (navigation), §5.1 (key bindings), §5.2 (branch popup).
