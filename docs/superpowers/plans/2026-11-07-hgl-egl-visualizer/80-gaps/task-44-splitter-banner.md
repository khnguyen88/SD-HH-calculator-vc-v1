# Task 44: Splitter detection and non-blocking warning banner

## Context

Spec §9.2 defers splitter branching to v2 but requires a non-blocking warning banner:
"If an imported file contains a splitter, show a non-blocking warning banner and render
only the primary path." `plan.md` notes this as the follow-up gap most likely to confuse
users.

A **splitter** is a structure that has more than one outgoing pipe (i.e., two or more
pipes share that structure as their `fromId`). This differs from a multi-inflow junction
(already handled by `structureLoss`).

## Preconditions

- Prior tasks: task-01, task-03 (`el`), task-05 (`importFromJsonFile`),
  task-06 (`importFromXlsxFile`).

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the
`import` sentinel block, after the task-07 code:

```js
  // --- Splitter detection (task-44) ---

  // Returns an array of structure IDs that have more than one outgoing pipe.
  function detectSplitters(imported) {
    if (!imported || !Array.isArray(imported.pipes) || !Array.isArray(imported.structures)) return [];
    const outflowCount = {};
    for (const p of imported.pipes) {
      outflowCount[p.fromId] = (outflowCount[p.fromId] || 0) + 1;
    }
    return imported.structures
      .filter((s) => (outflowCount[s.id] || 0) > 1)
      .map((s) => s.id);
  }

  // Shows a banner below the topbar listing splitter structure IDs; removes itself when
  // the list is empty.
  function renderSplitterBanner(splitterIds) {
    const existing = document.getElementById("splitterBanner");
    if (existing) existing.parentNode.removeChild(existing);
    if (!splitterIds || splitterIds.length === 0) return;

    const banner = el("div", {
      id: "splitterBanner",
      role: "alert",
      style: "padding:6px 12px; background:#ffd60a; color:#0d1117; font-size:12px; "
           + "font-family:var(--mono); border-bottom:1px solid #d4a800; "
           + "display:flex; gap:8px; align-items:baseline;"
    }, [
      el("span", { style: "font-weight:700;" }, "Flow splitter detected:"),
      el("span", null,
        splitterIds.join(", ")
        + " — only the primary outgoing pipe is walked. Splitter branching is v2."),
      el("button", {
        type: "button",
        style: "margin-left:auto; background:transparent; border:none; cursor:pointer; font-size:14px;",
        "aria-label": "Dismiss",
        onclick: () => {
          const b = document.getElementById("splitterBanner");
          if (b) b.parentNode.removeChild(b);
        }
      }, "×")
    ]);

    const topbar = document.querySelector(".topbar");
    if (topbar && topbar.nextSibling) {
      topbar.parentNode.insertBefore(banner, topbar.nextSibling);
    } else if (topbar) {
      topbar.parentNode.appendChild(banner);
    }
  }
```

**Modify** `importFromJsonFile` (task-05) to show the banner after import. Locate the
last line of the function body:

```js
    if (imported.config && (imported.config.hglMethod === "hec22" || imported.config.hglMethod === "legacy-both-crown")) {
      state.ui.hglMethod = imported.config.hglMethod;
    }
  }
```

Append after the `if` block, still inside the function:

```js
    renderSplitterBanner(detectSplitters(state.imported));
```

**Modify** `importFromXlsxFile` (task-06) similarly. Locate the last statement inside
the function body:

```js
    state.ui.mode = "explore";
  }
```

Append before the closing brace:

```js
    renderSplitterBanner(detectSplitters(state.imported));
```

## Acceptance test

In DevTools console:

```js
// Clean network — no banner.
state.imported = {
  structures: [{ id: "OUT", type: "outfall" }, { id: "A", type: "bend" }],
  pipes: [{ id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
           n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 }],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
renderSplitterBanner(detectSplitters(state.imported));
console.assert(document.getElementById("splitterBanner") === null, "no banner for clean network");

// Network with a splitter: S-B has two outgoing pipes.
state.imported.structures.push({ id: "B", type: "manhole" });
state.imported.pipes.push({ id: "P2", fromId: "B", toId: "OUT",
  shape: "circular", size: 15, n: 0.013, slope: 0.005, length: 80, angle: 45, designQ: 3 });
state.imported.pipes.push({ id: "P3", fromId: "B", toId: "A",
  shape: "circular", size: 12, n: 0.013, slope: 0.005, length: 60, angle: 30, designQ: 2 });

const splitters = detectSplitters(state.imported);
console.assert(splitters.length === 1 && splitters[0] === "B",
  "expected B as splitter, got: " + JSON.stringify(splitters));

renderSplitterBanner(splitters);
const banner = document.getElementById("splitterBanner");
console.assert(banner !== null, "banner should appear for splitter network");
console.assert(banner.textContent.includes("B"), "banner should mention structure B");

// Dismiss button removes the banner.
const dismissBtn = banner.querySelector("button");
console.assert(dismissBtn, "dismiss button should exist");
dismissBtn.click();
console.assert(document.getElementById("splitterBanner") === null, "banner dismissed");

// Re-render clean network removes banner automatically.
renderSplitterBanner([]);
console.assert(document.getElementById("splitterBanner") === null, "empty list removes banner");

// detectSplitters is safe on null input.
console.assert(detectSplitters(null).length === 0, "null input returns empty");

console.log("task-44 splitter banner: OK");
```

**Functional test** — load the JSON fixture below via the file picker and verify the
banner appears (saves creating a new fixture file):

```json
{
  "schemaVersion": 1, "sourceApp": "test",
  "structures": [
    {"id": "OUT", "type": "outfall", "x": 0, "y": 0, "rim": 100, "startElev": 97, "crown": 96},
    {"id": "A",   "type": "manhole", "x": 0, "y": -100, "rim": 103, "startElev": 100, "crown": 99},
    {"id": "B",   "type": "manhole", "x": 60, "y": -100, "rim": 104, "startElev": 101, "crown": 100}
  ],
  "pipes": [
    {"id": "P1", "fromId": "A", "toId": "OUT", "shape": "circular", "size": 18, "n": 0.013, "slope": 0.005, "length": 100, "angle": 0, "designQ": 8},
    {"id": "P2", "fromId": "B", "toId": "OUT", "shape": "circular", "size": 15, "n": 0.013, "slope": 0.005, "length":  80, "angle": 45, "designQ": 4},
    {"id": "P3", "fromId": "B", "toId": "A",   "shape": "circular", "size": 12, "n": 0.013, "slope": 0.005, "length":  60, "angle": 30, "designQ": 2}
  ],
  "outfall": {"structureId": "OUT", "tailwaterElev": 97}
}
```

## Done when

- `detectSplitters` and `renderSplitterBanner` defined in the `import` sentinel block.
- Both `importFromJsonFile` and `importFromXlsxFile` call `renderSplitterBanner(detectSplitters(...))`.
- Loading a clean network: no banner appears.
- Loading a network with a splitter: yellow banner appears below the topbar, names the splitter, has a dismiss button.
- Dismissing the banner removes it without other side effects.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-44 splitter detection and warning banner`.
