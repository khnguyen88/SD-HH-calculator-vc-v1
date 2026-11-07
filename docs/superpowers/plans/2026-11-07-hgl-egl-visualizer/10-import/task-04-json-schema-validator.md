# Task 04: JSON schema validator

## Context

Validate that an imported JSON object matches schemaVersion 1. Reject malformed inputs with a specific error message **before** any state mutation. Implements spec §2.1 (JSON sidecar schema).

## Preconditions

- Prior tasks: task-01, task-03.
- Sentinel block `// ==== import: begin ==== / end ====` exists and is empty.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Insert inside the `import` sentinel block, immediately after the `begin` line:

```js
  // --- schema validator (task-04) ---
  function validateImportedJson(obj) {
    const errors = [];
    const push = (p) => errors.push(p);

    if (!obj || typeof obj !== "object") { push("not an object"); return { valid: false, errors }; }
    if (obj.schemaVersion !== 1) push("schemaVersion must be 1 (got " + obj.schemaVersion + ")");
    if (typeof obj.sourceApp !== "string") push("sourceApp must be a string");

    if (!Array.isArray(obj.structures)) push("structures must be an array");
    else obj.structures.forEach((s, i) => {
      if (!s || typeof s !== "object") { push("structures[" + i + "] not an object"); return; }
      if (typeof s.id !== "string" || !s.id) push("structures[" + i + "].id missing");
      if (typeof s.type !== "string") push("structures[" + i + "].type missing");
      ["rim", "startElev", "crown"].forEach((f) => {
        if (s[f] != null && typeof s[f] !== "number") push("structures[" + i + "]." + f + " must be a number");
      });
    });

    if (!Array.isArray(obj.pipes)) push("pipes must be an array");
    else obj.pipes.forEach((p, i) => {
      if (!p || typeof p !== "object") { push("pipes[" + i + "] not an object"); return; }
      if (typeof p.id !== "string" || !p.id) push("pipes[" + i + "].id missing");
      if (typeof p.fromId !== "string") push("pipes[" + i + "].fromId missing");
      if (typeof p.toId !== "string") push("pipes[" + i + "].toId missing");
      ["slope", "length"].forEach((f) => {
        if (typeof p[f] !== "number" || p[f] < 0) push("pipes[" + i + "]." + f + " must be non-negative number");
      });
      if (typeof p.n !== "number" || p.n <= 0) push("pipes[" + i + "].n must be positive number");
    });

    if (!obj.outfall || typeof obj.outfall !== "object") push("outfall missing");
    else {
      if (typeof obj.outfall.structureId !== "string") push("outfall.structureId missing");
      if (typeof obj.outfall.tailwaterElev !== "number") push("outfall.tailwaterElev must be a number");
    }

    return { valid: errors.length === 0, errors };
  }
```

## Acceptance test

**In the browser DevTools console** of the dev HTML, run:

```js
// Valid minimal object
const ok = { schemaVersion: 1, sourceApp: "x",
  structures: [{ id: "S1", type: "outfall", rim: 100, startElev: 95, crown: 94 }],
  pipes: [{ id: "P1", fromId: "S2", toId: "S1", n: 0.013, slope: 0.005, length: 100 }],
  outfall: { structureId: "S1", tailwaterElev: 100 } };
let r = validateImportedJson(ok);
console.assert(r.valid === true, "valid rejected:", r.errors);

// Missing schemaVersion
r = validateImportedJson({ ...ok, schemaVersion: 2 });
console.assert(r.valid === false && r.errors.some((e) => e.includes("schemaVersion")), "schemaVersion check failed");

// Negative length
r = validateImportedJson({ ...ok, pipes: [{ ...ok.pipes[0], length: -5 }] });
console.assert(r.valid === false && r.errors.some((e) => e.includes("length")), "negative length check failed");

// Zero n
r = validateImportedJson({ ...ok, pipes: [{ ...ok.pipes[0], n: 0 }] });
console.assert(r.valid === false && r.errors.some((e) => e.includes(".n ")), "zero n check failed");

// Null input
r = validateImportedJson(null);
console.assert(r.valid === false, "null not rejected");

console.log("task-04 validator smoke test: OK");
```

Expected: `task-04 validator smoke test: OK`, zero AssertionErrors.

A node-based test is added by task-31 (`validator.test.js`).

## Done when

- `validateImportedJson(obj)` is defined inside the `import` sentinel block.
- Console smoke test passes.
- Build still succeeds.
- Commit: `feat(visualizer): task-04 JSON schema validator`.
