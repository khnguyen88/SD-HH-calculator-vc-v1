# Task 01: Create the dev HTML skeleton

## Context

Create the single dev HTML file that every subsequent task edits. This file is the equivalent of the main app's `storm-drain-design-calculator-dev.html`. It must contain all sentinel comments that later tasks insert code into, so this is the ONE time we write the overall document skeleton.

Implements spec §0 (non-negotiables) and §3.3 (overall screen layout).

## Preconditions

- Prior tasks: none (this is the first task).
- `drainage-calculator/` directory exists in the repo.
- `drainage-calculator/lib/sheetjs-bundle.js` exists (used by task-02 but not by this task).

## Exact changes

**Create** `visualizer/storm-drain-visualizer-dev.html` with the exact contents below. Do not deviate from the sentinel comments — later tasks grep for these literal strings.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Storm Drain HGL/EGL Visualizer</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  /* ==== css: begin ==== */
  :root {
    --bg: #0d1117;
    --bg-elev: #161b22;
    --fg: #e6edf3;
    --fg-dim: #8b949e;
    --accent: #ffd60a;
    --mono: ui-monospace, "Cascadia Mono", "SF Mono", Consolas, "Liberation Mono", monospace;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body {
    background: var(--bg); color: var(--fg);
    font-family: system-ui, sans-serif;
    display: flex; flex-direction: column;
  }
  .topbar { padding: 8px 12px; background: var(--bg-elev);
            border-bottom: 1px solid #30363d; display: flex; gap: 12px; align-items: center; }
  .topbar h1 { font-size: 14px; margin: 0; }
  .viewframe { flex: 1; min-height: 0; display: flex; flex-direction: column; }
  .viewframe .tools { padding: 6px 12px; background: var(--bg-elev); font-size: 12px;
                       color: var(--fg-dim); border-bottom: 1px solid #30363d; }
  .viewframe svg { flex: 1; min-height: 0; background: var(--bg); width: 100%; }
  .ledger { height: 45%; overflow: auto; padding: 10px 14px; background: #f5f3eb;
            color: #1a1a1a; font-family: var(--mono); border-top: 2px solid #30363d; }
  .num { font-family: var(--mono); }
  /* ==== css: end ==== */
</style>
</head>
<body>
<div class="topbar">
  <h1>Storm Drain HGL/EGL Visualizer</h1>
  <input type="file" id="fileInput" accept=".xlsx,.json">
  <span id="fileName" class="num"></span>
  <span style="flex:1"></span>
  <button id="modeToggle" type="button">▸ explore</button>
</div>
<div class="viewframe">
  <div class="tools">
    <span id="viewToggle">[ISO | PROFILE]</span>
    <span style="margin-left: 16px">cursor: <span id="cursorLabel" class="num">(none)</span></span>
  </div>
  <svg id="viewSvg" preserveAspectRatio="xMidYMid meet"></svg>
</div>
<div class="ledger" id="ledger"></div>
<!-- SHEETJS --><!-- build-visualizer.js replaces this with the inlined bundle -->
<script>
  // ==== dom-helpers: begin ====
  // (task-03 inserts el() and withFocusPreserved here)
  // ==== dom-helpers: end ====

  // ==== state: begin ====
  const state = {
    imported: null,   // { structures, pipes, outfall, config, kbTable } | null
    overrides: { byId: {} },
    cursor: { kind: null, id: null, pathStack: [] },
    ui: { view: "iso", mode: "explore", hglMethod: "hec22",
          freeRoam: false, branchChoices: { byStructureId: {} } }
  };
  // ==== state: end ====

  // ==== compute: begin ====
  // (task-08 through task-13 insert pure math here)
  // ==== compute: end ====

  // ==== import: begin ====
  // (task-04 through task-07 insert here)
  // ==== import: end ====

  // ==== views: begin ====
  // (task-14 through task-17 insert here)
  // ==== views: end ====

  // ==== navigation: begin ====
  // (task-18 through task-22 insert here)
  // ==== navigation: end ====

  // ==== edit-mode: begin ====
  // (task-23 through task-26 insert here)
  // ==== edit-mode: end ====

  // ==== ledger-render: begin ====
  // (task-27 through task-30 insert here)
  // ==== ledger-render: end ====

  // ==== bootstrap: begin ====
  function renderAll() {
    // (fleshed out as views/ledger/navigation tasks land)
  }
  document.getElementById("fileInput").addEventListener("change", (ev) => {
    const f = ev.target.files[0]; if (!f) return;
    document.getElementById("fileName").textContent = f.name;
    // (task-05/06 wire the actual import here)
  });
  renderAll();
  // ==== bootstrap: end ====
</script>
</body>
</html>
```

## Acceptance test

Open the file by double-click. Verify:

```
1. Page loads with dark background and title "Storm Drain HGL/EGL Visualizer".
2. The ledger area is visible as a light-paper panel at the bottom.
3. The SVG viewframe is empty (expected).
4. Browser DevTools Console shows no errors.
5. Browser DevTools Network tab (reload with cache disabled) shows ONLY the file:// request for the HTML; no other network activity.
```

No automated test for this task — it's a scaffold file. The group acceptance criteria in `group.md` will be checked after task-03.

## Done when

- `visualizer/storm-drain-visualizer-dev.html` exists with the exact content above.
- All sentinel comment pairs are present and empty between them.
- File opens in a browser with no console errors.
- Commit: `feat(visualizer): task-01 dev HTML skeleton with sentinel comments`.
