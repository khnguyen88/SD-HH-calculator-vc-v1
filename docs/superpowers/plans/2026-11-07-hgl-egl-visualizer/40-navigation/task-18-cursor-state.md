# Task 18: Cursor state helpers

## Context

Implement `initialCursor`, `advanceCursor`, `retreatCursor`, and `upstreamOptions` — pure helpers that compute cursor transitions without touching the DOM. Implements spec §5.1 walk model.

## Preconditions

- Prior tasks: task-01, task-03, task-12.

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Insert inside the `navigation` sentinel block, immediately after the `begin` line:

```js
  // --- Cursor helpers (task-18) ---

  // Return the list of candidate next-upstream elements from a given cursor position.
  //   - At a structure: list the pipes with toId == structure.id.
  //   - At a pipe: list the pipe's fromId structure (always just one).
  function upstreamOptions(cursor, imported) {
    if (!cursor || !imported) return [];
    if (cursor.kind === "structure") {
      return imported.pipes
        .filter((p) => p.toId === cursor.id)
        .map((p) => ({ kind: "pipe", id: p.id, label: p.id + " (from " + p.fromId + ")", pipe: p }));
    }
    if (cursor.kind === "pipe") {
      const pipe = imported.pipes.find((p) => p.id === cursor.id);
      if (!pipe) return [];
      const s = imported.structures.find((st) => st.id === pipe.fromId);
      return s ? [{ kind: "structure", id: s.id, label: s.id, structure: s }] : [];
    }
    return [];
  }

  function initialCursor(imported) {
    if (!imported || !imported.outfall) return { kind: null, id: null, pathStack: [] };
    const sid = imported.outfall.structureId;
    return { kind: "structure", id: sid, pathStack: [sid] };
  }

  // Produce a NEW cursor advanced to the chosen next element.
  //   next: one of the options returned by upstreamOptions (or null to stay).
  function advanceCursor(cursor, next) {
    if (!next) return cursor;
    return {
      kind: next.kind,
      id: next.id,
      pathStack: cursor.pathStack.concat([next.id])
    };
  }

  // Produce a NEW cursor with the last entry popped.
  function retreatCursor(cursor) {
    if (!cursor || !cursor.pathStack || cursor.pathStack.length <= 1) return cursor;
    const newStack = cursor.pathStack.slice(0, -1);
    const topId = newStack[newStack.length - 1];
    // Determine kind from the id: if it's in structures → "structure", else "pipe".
    // We don't have imported here; caller passes it. For simplicity, caller resolves.
    return { kind: cursor.kind, id: topId, pathStack: newStack };
  }

  // Helper: re-kind after retreat (caller passes imported so we can tell structure vs pipe).
  function resolveCursorKind(cursor, imported) {
    if (!cursor || !cursor.id || !imported) return cursor;
    const isPipe = imported.pipes.some((p) => p.id === cursor.id);
    const kind = isPipe ? "pipe" : "structure";
    return { kind, id: cursor.id, pathStack: cursor.pathStack };
  }
```

## Acceptance test

In DevTools console:

```js
const imported = {
  structures: [
    { id: "OUT", type: "outfall" },
    { id: "A",   type: "bend" },
    { id: "B",   type: "manhole" }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT" },
    { id: "P2", fromId: "B", toId: "A" }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};

let c = initialCursor(imported);
console.assert(c.kind === "structure" && c.id === "OUT" && c.pathStack.length === 1, "initial cursor");

let opts = upstreamOptions(c, imported);
console.assert(opts.length === 1 && opts[0].kind === "pipe" && opts[0].id === "P1", "upstream from OUT");

c = advanceCursor(c, opts[0]);
console.assert(c.kind === "pipe" && c.id === "P1" && c.pathStack.length === 2, "advance to pipe");

opts = upstreamOptions(c, imported);
console.assert(opts.length === 1 && opts[0].kind === "structure" && opts[0].id === "A", "upstream from P1");

c = advanceCursor(c, opts[0]);
console.assert(c.id === "A" && c.pathStack.length === 3, "advance to A");

// Retreat
c = retreatCursor(c);
c = resolveCursorKind(c, imported);
console.assert(c.id === "P1" && c.kind === "pipe", "retreat to P1");

// Retreat past start stays at outfall (length-1 stack)
c = { kind: "structure", id: "OUT", pathStack: ["OUT"] };
const c2 = retreatCursor(c);
console.assert(c2.id === "OUT" && c2.pathStack.length === 1, "retreat at start is no-op");

console.log("task-18 cursor helpers: OK");
```

## Done when

- `upstreamOptions`, `initialCursor`, `advanceCursor`, `retreatCursor`, `resolveCursorKind` defined.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-18 cursor state helpers`.
