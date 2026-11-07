# Task 05: JSON importer

## Context

Read a user-selected `.json` file, validate it via task-04, and populate `state.imported`. Also detect the `_overrides` sidecar from a previously-exported tweaked JSON and restore edit mode. Implements spec §2.1 and §6.3 (re-import is lossless).

## Preconditions

- Prior tasks: task-01, task-03, task-04.
- `validateImportedJson` is defined in the `import` sentinel block.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `import` sentinel block, after the task-04 code:

```js
  // --- json importer (task-05) ---
  async function importFromJsonFile(file) {
    const text = await file.text();
    let obj;
    try { obj = JSON.parse(text); }
    catch (e) { throw new Error("JSON parse error: " + e.message); }

    const result = validateImportedJson(obj);
    if (!result.valid) throw new Error("JSON validation failed: " + result.errors.join("; "));

    // Separate the tweaked-export sidecar (if present) before copying `imported`.
    const overrides = Array.isArray(obj._overrides) ? obj._overrides : [];
    const imported = {
      structures: obj.structures.map((s) => Object.assign({}, s)),
      pipes: obj.pipes.map((p) => Object.assign({}, p)),
      outfall: Object.assign({}, obj.outfall),
      config: Object.assign({}, obj.config || {}),
      kbTable: Array.isArray(obj.kbTable) ? obj.kbTable.slice() : null
    };

    // If this is a tweaked export, imported fields currently hold the TWEAKED values.
    // Walk `_overrides` and restore the originalValue onto imported so `state.imported`
    // is a clean baseline; the newValue goes into state.overrides.
    state.overrides = { byId: {} };
    for (const ov of overrides) {
      // Find and mutate the imported element
      const el = imported.structures.find((s) => s.id === ov.elementId)
              || imported.pipes.find((p) => p.id === ov.elementId);
      if (el) el[ov.field] = ov.originalValue;
      // Record in state.overrides
      state.overrides.byId[ov.elementId] = state.overrides.byId[ov.elementId] || {};
      state.overrides.byId[ov.elementId][ov.field] = ov.newValue;
    }

    state.imported = imported;
    state.ui.mode = overrides.length > 0 ? "edit" : "explore";

    // Apply hglMethod from config if provided
    if (imported.config && (imported.config.hglMethod === "hec22" || imported.config.hglMethod === "legacy-both-crown")) {
      state.ui.hglMethod = imported.config.hglMethod;
    }
  }
```

**Modify** the bootstrap file-input handler at the bottom of the file:

Locate:
```js
  document.getElementById("fileInput").addEventListener("change", (ev) => {
    const f = ev.target.files[0]; if (!f) return;
    document.getElementById("fileName").textContent = f.name;
    // (task-05/06 wire the actual import here)
  });
```

Replace with:
```js
  document.getElementById("fileInput").addEventListener("change", async (ev) => {
    const f = ev.target.files[0]; if (!f) return;
    document.getElementById("fileName").textContent = f.name;
    try {
      const name = f.name.toLowerCase();
      if (name.endsWith(".json")) await importFromJsonFile(f);
      else if (name.endsWith(".xlsx")) await importFromXlsxFile(f);  // added by task-06
      else throw new Error("Unsupported file type: " + f.name);
      renderAll();
    } catch (err) {
      alert("Import failed: " + err.message);
      state.imported = null;
    }
  });
```

Note: `importFromXlsxFile` is defined by task-06; if task-06 hasn't landed yet, this line throws `ReferenceError` — fine, the `.json` path still works. Fix order: do task-05 → task-06 and the handler works for both.

## Acceptance test

In the dev HTML's DevTools console:

```js
// Build a valid JSON Blob and run importFromJsonFile against it.
const payload = { schemaVersion: 1, sourceApp: "test",
  structures: [
    { id: "OUT", type: "outfall", x: 0, y: 0, rim: 100, startElev: 95, crown: 94 },
    { id: "S1",  type: "manhole", x: 0, y: -100, rim: 103, startElev: 98.4, crown: 97.6 }
  ],
  pipes: [
    { id: "P1", fromId: "S1", toId: "OUT",
      shape: "circular", size: 18, n: 0.013, slope: 0.005, length: 120, angle: 0 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 } };

const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
const file = new File([blob], "test.json", { type: "application/json" });
await importFromJsonFile(file);
console.assert(state.imported !== null, "imported not set");
console.assert(state.imported.structures.length === 2, "wrong structure count");
console.assert(state.imported.pipes[0].slope === 0.005, "slope not set");
console.assert(state.ui.mode === "explore", "mode should be explore");

// Now test tweaked re-import
const tweaked = Object.assign({}, payload, {
  pipes: [Object.assign({}, payload.pipes[0], { slope: 0.006 })],
  _overrides: [{ elementId: "P1", field: "slope", originalValue: 0.005, newValue: 0.006 }]
});
const file2 = new File([new Blob([JSON.stringify(tweaked)])], "tweaked.json");
await importFromJsonFile(file2);
console.assert(state.ui.mode === "edit", "mode should be edit after _overrides");
console.assert(state.imported.pipes[0].slope === 0.005, "original slope should restore to imported");
console.assert(state.overrides.byId["P1"].slope === 0.006, "override not recorded");

console.log("task-05 importer smoke test: OK");
```

## Done when

- `importFromJsonFile` defined; bootstrap handler calls it for `.json` files.
- Smoke test above prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-05 JSON importer with tweaked-sidecar restore`.
