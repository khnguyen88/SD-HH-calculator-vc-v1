# Task 07: Auto-layout when coordinates are missing

## Context

If an imported file has no `x`/`y` coordinates on structures (older main-app exports or hand-authored JSON), run a layered-graph auto-layout so the iso view still renders. Implements spec §2.3.

## Preconditions

- Prior tasks: task-01, task-03, task-05.

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the `import` sentinel block, after the task-06 code:

```js
  // --- auto-layout (task-07) ---
  function autoLayoutStructures(structures, pipes, outfallSid) {
    // BFS hop-distance from the outfall backward along pipes (follow pipes upstream:
    // for each structure S, find pipes where toId == S's id; those pipes' fromId
    // structures are at hopDistance = S's hopDistance + 1).
    const hop = {};
    hop[outfallSid] = 0;
    const queue = [outfallSid];
    while (queue.length) {
      const cur = queue.shift();
      for (const p of pipes) {
        if (p.toId === cur && !(p.fromId in hop)) {
          hop[p.fromId] = hop[cur] + 1;
          queue.push(p.fromId);
        }
      }
    }

    // Any structure not reached (orphan) gets a large hop, placed below the main tree.
    const maxHop = Math.max(0, ...Object.values(hop));
    for (const s of structures) if (!(s.id in hop)) hop[s.id] = maxHop + 2;

    // Group by hop level, assign x-indices in insertion order
    const levels = {};
    for (const s of structures) {
      const h = hop[s.id];
      (levels[h] = levels[h] || []).push(s);
    }

    for (const h in levels) {
      const row = levels[h];
      const count = row.length;
      row.forEach((s, i) => {
        s.x = (i - (count - 1) / 2) * 80;
        s.y = -h * 100;
      });
    }
  }

  // Called by the bootstrap after any successful import.
  function autoLayoutIfNeeded() {
    if (!state.imported) return;
    const needs = state.imported.structures.some((s) =>
      !(typeof s.x === "number" && typeof s.y === "number" && (s.x !== 0 || s.y !== 0))
    );
    // A structure having (0,0) exactly is treated as "unset" only if ALL structures do.
    const allZero = state.imported.structures.every((s) => (s.x === 0 || s.x == null) && (s.y === 0 || s.y == null));
    if (needs && allZero) {
      autoLayoutStructures(state.imported.structures, state.imported.pipes, state.imported.outfall.structureId);
    }
  }
```

**Modify** the bootstrap file-input handler. Locate the inside of the try block:

```js
      const name = f.name.toLowerCase();
      if (name.endsWith(".json")) await importFromJsonFile(f);
      else if (name.endsWith(".xlsx")) await importFromXlsxFile(f);
      else throw new Error("Unsupported file type: " + f.name);
      renderAll();
```

Insert `autoLayoutIfNeeded();` before `renderAll();`:

```js
      const name = f.name.toLowerCase();
      if (name.endsWith(".json")) await importFromJsonFile(f);
      else if (name.endsWith(".xlsx")) await importFromXlsxFile(f);
      else throw new Error("Unsupported file type: " + f.name);
      autoLayoutIfNeeded();
      renderAll();
```

## Acceptance test

In DevTools console of the dev HTML:

```js
// Build a 4-structure chain with all x/y zero; outfall is OUT.
state.imported = {
  structures: [
    { id: "OUT", type: "outfall", x: 0, y: 0 },
    { id: "A",   type: "manhole", x: 0, y: 0 },
    { id: "B",   type: "manhole", x: 0, y: 0 },
    { id: "C",   type: "manhole", x: 0, y: 0 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT" },
    { id: "P2", fromId: "B", toId: "A" },
    { id: "P3", fromId: "C", toId: "B" }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};

autoLayoutIfNeeded();

const byId = (id) => state.imported.structures.find((s) => s.id === id);
console.assert(byId("OUT").y === 0, "OUT.y should be 0");
console.assert(byId("A").y === -100, "A.y should be -100");
console.assert(byId("B").y === -200, "B.y should be -200");
console.assert(byId("C").y === -300, "C.y should be -300");
console.log("task-07 autolayout chain: OK");

// Branching: two structures at the same hop
state.imported.structures = [
  { id: "OUT", type: "outfall", x: 0, y: 0 },
  { id: "A",   type: "manhole", x: 0, y: 0 },
  { id: "B",   type: "manhole", x: 0, y: 0 }
];
state.imported.pipes = [
  { id: "P1", fromId: "A", toId: "OUT" },
  { id: "P2", fromId: "B", toId: "OUT" }
];
autoLayoutIfNeeded();
const a = state.imported.structures.find((s) => s.id === "A");
const b = state.imported.structures.find((s) => s.id === "B");
console.assert(a.y === -100 && b.y === -100, "A/B should share hop level");
console.assert(Math.abs(a.x - b.x) === 80, "A/B should be spaced 80 apart, got " + Math.abs(a.x - b.x));
console.log("task-07 autolayout branching: OK");
```

## Done when

- `autoLayoutStructures` and `autoLayoutIfNeeded` defined in the `import` sentinel block.
- Bootstrap handler calls `autoLayoutIfNeeded()` after import.
- Both smoke tests above pass.
- Commit: `feat(visualizer): task-07 layered-graph auto-layout`.
