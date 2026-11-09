# Group 00: Scaffold — project skeleton & build

**Purpose:** Create the dev HTML, the build script, and the two foundational JS helpers (`el()`, `withFocusPreserved`) that every subsequent task depends on.

**Tasks:**
- `task-01-dev-html-skeleton.md` — create `storm-drain-visualizer-dev.html` with all sentinel comments
- `task-02-build-script.md` — create `build-visualizer.js` that inlines SheetJS
- `task-03-el-helper-and-focus.md` — inject `el()` and `withFocusPreserved` into the dev file

**Group acceptance criteria** (verify after all three tasks):
- `visualizer/storm-drain-visualizer-dev.html` exists and opens in a browser (blank page with dark background and title "Storm Drain HGL/EGL Visualizer").
- `node visualizer/build-visualizer.js` runs, produces `storm-drain-visualizer.html`, prints `visualizer: built OK (<N> KB)`.
- Built file size ≥ 800 KB (SheetJS inlined; if under 800 KB, SheetJS wasn't inlined).
- Opening the built file by double-click shows the same dark page with no network requests (verify in browser DevTools Network tab).
- `el("div", {hidden: null}, "x").outerHTML === "<div>x</div>"` — null guard works.

**Spec references:** §0 (non-negotiable constraints), §A.1/A.2 (main spec helpers).
