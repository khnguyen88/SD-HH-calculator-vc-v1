# Task 26: Export tweaked JSON

## Context

Build a tweaked-JSON object matching spec §6.3 and download it as a file. Includes the `_overrides` sidecar so re-import is lossless. Implements spec §6.3.

## Preconditions

- Prior tasks: task-01, task-03, task-05, task-23.

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the `edit-mode` sentinel block after task-25:

```js
  // --- Tweaked JSON export (task-26) ---

  function buildTweakedJsonExport() {
    if (!state.imported) throw new Error("no imported data to export");
    const ovs = listOverrides();

    // Merge overrides into element fields for output
    const mergeField = (el) => {
      const ov = state.overrides.byId[el.id];
      if (!ov) return Object.assign({}, el);
      return Object.assign({}, el, ov);
    };
    const structures = state.imported.structures.map(mergeField);
    const pipes = state.imported.pipes.map(mergeField);

    return {
      schemaVersion: 1,
      exportedAt: new Date().toISOString(),
      sourceApp: "storm-drain-hgl-visualizer",
      basedOn: {
        sourceApp: state.imported.config && state.imported.config.sourceApp || "unknown",
        exportedAt: state.imported.config && state.imported.config.exportedAt || null
      },
      config: Object.assign({}, state.imported.config || {}, { hglMethod: state.ui.hglMethod }),
      structures, pipes,
      outfall: Object.assign({}, state.imported.outfall),
      kbTable: state.imported.kbTable || null,
      _overrides: ovs
    };
  }

  function downloadTweakedJson() {
    const obj = buildTweakedJsonExport();
    const text = JSON.stringify(obj, null, 2);
    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const stamp = new Date().toISOString().slice(0, 10);
    a.download = "visualizer-tweaked-" + stamp + ".json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // Wire a toolbar button
  (function () {
    const topbar = document.querySelector(".topbar");
    if (!topbar) return;
    const btn = el("button", {
      type: "button",
      id: "exportTweakedBtn",
      style: "margin-left:4px;",
      onclick: () => {
        try { downloadTweakedJson(); }
        catch (e) { alert("Export failed: " + e.message); }
      }
    }, "export tweaked");
    topbar.appendChild(btn);
  })();
```

## Acceptance test

In DevTools console:

```js
state.imported = {
  structures: [
    { id: "OUT", type: "outfall", x: 0, y: 0, rim: 100, startElev: 95, crown: 94 },
    { id: "A",   type: "bend",    x: 0, y: -100, rim: 103, startElev: 98.4, crown: 97.6 }
  ],
  pipes: [{ id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
           n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 }],
  outfall: { structureId: "OUT", tailwaterElev: 100 },
  config: { sourceApp: "storm-drain-design-calculator", exportedAt: "2026-11-07T10:00:00Z" },
  kbTable: null
};
state.overrides = { byId: {} };
setOverride("P1", "slope", 0.006);

const obj = buildTweakedJsonExport();
console.assert(obj.schemaVersion === 1, "schemaVersion");
console.assert(obj.sourceApp === "storm-drain-hgl-visualizer", "sourceApp");
console.assert(obj.basedOn.sourceApp === "storm-drain-design-calculator", "basedOn");
console.assert(obj.pipes.find((p) => p.id === "P1").slope === 0.006, "merged override");
console.assert(obj._overrides.length === 1 && obj._overrides[0].field === "slope", "_overrides sidecar");
console.assert(obj._overrides[0].originalValue === 0.005, "original preserved in sidecar");
console.assert(obj._overrides[0].newValue === 0.006, "new in sidecar");

// Round-trip through importFromJsonFile (synthesize a File)
const blob = new Blob([JSON.stringify(obj)], { type: "application/json" });
const file = new File([blob], "roundtrip.json", { type: "application/json" });
await importFromJsonFile(file);
console.assert(state.ui.mode === "edit", "edit mode restored");
console.assert(state.overrides.byId.P1.slope === 0.006, "override restored");
console.assert(state.imported.pipes.find((p) => p.id === "P1").slope === 0.005, "imported restored to original");

// Button is present
console.assert(document.getElementById("exportTweakedBtn") !== null, "toolbar button");

console.log("task-26 tweaked export: OK");
```

## Done when

- `buildTweakedJsonExport`, `downloadTweakedJson`, toolbar button all defined.
- Round-trip test passes: export → re-import restores edit mode and overrides, imported values match originals.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-26 export tweaked JSON with roundtrip support`.
