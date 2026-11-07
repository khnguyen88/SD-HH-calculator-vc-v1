# Task 06: XLSX importer

## Context

Parse the main app's `.xlsx` export (per main spec §B) into the same in-memory shape task-05 produces. Only four sheets are consumed: `Drainage Area`, `Junction Structure`, `Pipe Sizing`, `Outlet Structures`. Everything else is ignored. Implements spec §2.1 (A).

## Preconditions

- Prior tasks: task-01, task-03, task-04, task-05.
- SheetJS is inlined in the BUILT HTML by task-02. **The dev HTML has no SheetJS until the build runs; test this task against the BUILT file**, not the dev file.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `import` sentinel block, after the task-05 code:

```js
  // --- xlsx importer (task-06) ---
  async function importFromXlsxFile(file) {
    if (typeof XLSX === "undefined") throw new Error("SheetJS not loaded — did you open the BUILT file?");

    const buf = await file.arrayBuffer();
    const wb = XLSX.read(buf, { type: "array" });

    const sh = (name) => {
      const s = wb.Sheets[name];
      if (!s) return [];
      return XLSX.utils.sheet_to_json(s, { defval: null });
    };

    const daRows   = sh("Drainage Area");
    const strRows  = sh("Junction Structure");
    const pipeRows = sh("Pipe Sizing");
    const outRows  = sh("Outlet Structures");

    // Build captured-Q lookup: drainage-area row has structureId + computed Q
    const capturedByStructureId = {};
    for (const r of daRows) {
      const sid = r["Structure ID"] || r.structureId || r["structureId"];
      const q = Number(r["Q (cfs)"] || r.Q || 0);
      if (sid) capturedByStructureId[sid] = (capturedByStructureId[sid] || 0) + (isFinite(q) ? q : 0);
    }

    const structures = strRows.map((r, i) => ({
      id:           String(r["Structure ID"] || r.structureId || ("S-" + (i+1))),
      label:        String(r["Label"] || r.label || r["Structure ID"] || ""),
      type:         String(r["Type"] || r.type || "manhole").toLowerCase(),
      x:            Number(r["X"] || r.x || 0),
      y:            Number(r["Y"] || r.y || 0),
      rim:          r["Rim"] != null ? Number(r["Rim"]) : null,
      startElev:    r["Start Elev"] != null ? Number(r["Start Elev"]) : null,
      crown:        r["Crown"] != null ? Number(r["Crown"]) : null,
      forceElev:    r["Force Elev"] === true || r["Force Elev"] === "TRUE",
      capturedQ:    capturedByStructureId[String(r["Structure ID"])] || 0,
      totalQ:       Number(r["Total Q (cfs)"] || 0),
      Hb:           Number(r["Hb (ft)"] || 0),
      elevation:    Number(r["Upstream EGL (ft)"] || 0)
    }));

    const pipes = pipeRows.map((r, i) => ({
      id:         String(r["Pipe ID"] || r.id || ("P-" + (i+1))),
      fromId:     String(r["From Structure"] || r.fromId),
      toId:       String(r["To Structure"] || r.toId),
      shape:      String(r["Shape"] || "circular").toLowerCase(),
      size:       r["Size"] || 18,
      n:          Number(r["Manning's n"] || r.n || 0.013),
      slope:      Number(r["Slope (ft/ft)"] || r.slope || 0.005),
      length:     Number(r["Length (ft)"] || r.length || 0),
      angle:      Number(r["Angle (deg)"] || r.angle || 0),
      designQ:    Number(r["Design Q (cfs)"] || 0),
      Hf:         Number(r["Hf (ft)"] || 0)
    }));

    // Find outfall: pick the structure with type == "outfall" (first), else lowest elevation.
    let outfallSid = null, outfallTw = null;
    const outfallStructs = structures.filter((s) => s.type === "outfall");
    if (outfallStructs.length > 0) {
      outfallSid = outfallStructs[0].id;
      outfallTw = outfallStructs[0].startElev != null ? outfallStructs[0].startElev : outfallStructs[0].rim;
    } else if (structures.length > 0) {
      const lowest = structures.slice().sort((a, b) => (a.startElev || 1e9) - (b.startElev || 1e9))[0];
      outfallSid = lowest.id;
      outfallTw = lowest.startElev;
    }
    // Override tailwater from Outlet Structures sheet if the outfall is linked there
    for (const r of outRows) {
      const sid = String(r["Structure ID"] || r.structureId || "");
      if (sid === outfallSid && r["TW Elevation"] != null) outfallTw = Number(r["TW Elevation"]);
    }

    state.overrides = { byId: {} };
    state.imported = {
      structures, pipes,
      outfall: { structureId: outfallSid, tailwaterElev: outfallTw != null ? outfallTw : 100 },
      config: { stormLabel: "", units: "us-customary", hglMethod: state.ui.hglMethod },
      kbTable: null
    };
    state.ui.mode = "explore";
  }
```

**Note on column names:** the main app's export uses user-facing column headers (e.g. "Structure ID", "Pipe ID"). The code above checks the header first, then a lowercase fallback. If the main app's export headers differ from what's assumed above, task-35 (the drift-test fixture) will expose the mismatch — fix the column mapping there and re-run.

## Acceptance test

Requires a fixture xlsx (task-35 creates one). For this task, just verify the function is **defined and callable** without arguments throwing a SyntaxError:

```js
// In DevTools console of the BUILT file:
console.assert(typeof importFromXlsxFile === "function", "not defined");
console.assert(typeof XLSX === "object" || typeof XLSX === "function", "XLSX missing");
console.log("task-06 definition check: OK");
```

A runtime test over a real fixture is in task-35.

## Done when

- `importFromXlsxFile` defined in the `import` sentinel block.
- Build succeeds; built file loads with SheetJS inlined.
- Definition check above passes in the browser.
- Commit: `feat(visualizer): task-06 xlsx importer for main-app export`.
