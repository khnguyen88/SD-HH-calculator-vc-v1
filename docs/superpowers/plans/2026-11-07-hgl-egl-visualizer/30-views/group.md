# Group 30: Views — iso + profile SVG renderers

**Purpose:** Render the top-half SVG for both views. Iso = stylized plan with the fixed transform; profile = elevation-vs-station with HGL/EGL/crown/invert polylines.

**Tasks:**
- `task-14-iso-projection.md` — `projectIso(x, y, z, kZ)` pure function
- `task-15-iso-svg-render.md` — `renderIso(svg, state)` populates an SVG with structures and pipes
- `task-16-profile-svg-render.md` — `renderProfile(svg, state, ledger)` draws crown/invert/HGL/EGL along the current path
- `task-17-view-toggle-hotkey.md` — `V` hotkey swaps active view, toolbar button mirrors it

**Group acceptance criteria:**
- Iso SVG contains one `<g data-kind="structure">` per structure and one `<line data-kind="pipe">` per pipe.
- Depth-sort: structures are added to the SVG document in ascending `(x + y)` order.
- Profile SVG contains two polylines (crown, invert), one dashed polyline (EGL), one solid polyline (HGL).
- Pressing `V` toggles `state.ui.view` and re-renders only the active view's SVG.
- Selecting a pipe in iso and pressing `V` leaves the same pipe highlighted in profile.

**Spec references:** §3 (view system), §3.1 (iso), §3.2 (profile), §5.1 key bindings.
