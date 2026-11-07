# Task 15: Iso SVG renderer

## Context

`renderIso(svgEl, state)` populates the `<svg id="viewSvg">` with one group per structure and one line per pipe. Depth-sorted by `(x + y)` ascending. Selected cursor element gets a yellow glow. Implements spec §3.1.

Note: task-22 made `renderIso` override-aware — structure `x`/`y` are resolved via `resolveField` over `s.overrides`.

## Preconditions

- Prior tasks: task-01, task-03, task-05 or 06 or 07 (something that populates `state.imported`), task-14.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `views` sentinel block after task-14:

```js
  // --- Iso SVG render (task-15) ---

  const SVG_NS = "http://www.w3.org/2000/svg";

  function svgEl(tag, attrs, children) {
    const e = document.createElementNS(SVG_NS, tag);
    if (attrs) for (const k in attrs) {
      const v = attrs[k];
      if (v === null || v === undefined) continue;
      e.setAttribute(k, v);
    }
    if (children) (Array.isArray(children) ? children : [children]).forEach((c) => {
      if (c == null) return;
      e.appendChild((c instanceof Node) ? c : document.createTextNode(String(c)));
    });
    return e;
  }

  // Map pipe diameter (in) to stroke width (px), clamped.
  function pipeStrokeWidth(d_in) {
    const d = Number(d_in) || 18;
    return Math.max(2, Math.min(10, d / 12));
  }

  // Symbol glyph per structure type.
  function structureSymbol(type, cx, cy, size, isSelected) {
    const s = size / 2;
    const strokeColor = isSelected ? "#ffd60a" : "#c9d1d9";
    const fillColor = "#161b22";
    const common = { stroke: strokeColor, "stroke-width": isSelected ? 2 : 1, fill: fillColor };
    if (type === "inlet")   return svgEl("polygon", Object.assign({ points: `${cx},${cy-s} ${cx+s},${cy+s} ${cx-s},${cy+s}` }, common));
    if (type === "manhole") return svgEl("rect",    Object.assign({ x: cx-s, y: cy-s, width: 2*s, height: 2*s }, common));
    if (type === "bend")    return svgEl("polyline", Object.assign({}, common, { points: `${cx-s},${cy+s} ${cx},${cy-s} ${cx+s},${cy+s}`, fill: "none" }));
    if (type === "junction")return svgEl("circle",  Object.assign({ cx: cx, cy: cy, r: s }, common));
    if (type === "splitter")return svgEl("rect",    Object.assign({ x: cx-s, y: cy-s, width: 2*s, height: 2*s, "stroke-dasharray": "3 2" }, common));
    if (type === "outfall") return svgEl("g", null, [
      svgEl("circle", Object.assign({ cx: cx, cy: cy, r: s * 1.2 }, common)),
      svgEl("circle", Object.assign({ cx: cx, cy: cy, r: s * 0.65 }, common))
    ]);
    return svgEl("circle", Object.assign({ cx: cx, cy: cy, r: s }, common));
  }

  function renderIso(svg, s) {
    // Clear
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    if (!s.imported) {
      svg.appendChild(svgEl("text", { x: 10, y: 20, fill: "#8b949e" }, "No data imported."));
      return;
    }

    // Build (x,y,z=rim) for each structure, resolving x/y overrides (task-22).
    const pts = s.imported.structures.map((st) => {
      const rx = resolveField(st.id, "x", s.imported, s.overrides);
      const ry = resolveField(st.id, "y", s.imported, s.overrides);
      const x = (typeof rx === "number" && isFinite(rx)) ? rx : 0;
      const y = (typeof ry === "number" && isFinite(ry)) ? ry : 0;
      return { id: st.id, type: st.type, x, y, z: (st.rim || 0) };
    });
    const b = isoBounds(pts, 2.0);
    const pad = 40;
    const vbW = Math.max(100, b.maxX - b.minX + 2 * pad);
    const vbH = Math.max(100, b.maxY - b.minY + 2 * pad);
    svg.setAttribute("viewBox", `${b.minX - pad} ${b.minY - pad} ${vbW} ${vbH}`);

    // Build index of projected positions for edges
    const posById = Object.create(null);
    for (const p of pts) posById[p.id] = projectIso(p.x, p.y, p.z, 2.0);

    // Draw pipes first, then structures on top; depth-sort structures by (x+y)
    const cursorId = s.cursor && s.cursor.id;
    for (const pipe of s.imported.pipes) {
      const a = posById[pipe.fromId], c = posById[pipe.toId];
      if (!a || !c) continue;
      const isSel = cursorId === pipe.id;
      const stroke = isSel ? "#ffd60a" : "#8b949e";
      svg.appendChild(svgEl("line", {
        x1: a.sx, y1: a.sy, x2: c.sx, y2: c.sy,
        stroke: stroke,
        "stroke-width": pipeStrokeWidth(pipe.size),
        "data-kind": "pipe",
        "data-id": pipe.id
      }));
    }
    const sortedStructs = pts.slice().sort((p, q) => (p.x + p.y) - (q.x + q.y));
    for (const p of sortedStructs) {
      const pos = posById[p.id];
      const g = svgEl("g", { "data-kind": "structure", "data-id": p.id });
      const isSel = cursorId === p.id;
      g.appendChild(structureSymbol(p.type, pos.sx, pos.sy, 14, isSel));
      g.appendChild(svgEl("text", {
        x: pos.sx + 10, y: pos.sy - 10,
        fill: "#c9d1d9", "font-size": 10, "font-family": "ui-monospace,monospace"
      }, p.id));
      svg.appendChild(g);
    }
  }
```

## Acceptance test

In DevTools console (requires a populated state):

```js
state.imported = {
  structures: [
    { id: "OUT", type: "outfall", x: 0, y: 0, rim: 100 },
    { id: "A",   type: "manhole", x: 0, y: -100, rim: 103 },
    { id: "B",   type: "bend",    x: 60, y: -100, rim: 104 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18 },
    { id: "P2", fromId: "B", toId: "A",   shape: "circular", size: 15 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };

renderIso(document.getElementById("viewSvg"), state);

const structs = document.querySelectorAll('#viewSvg [data-kind="structure"]');
console.assert(structs.length === 3, "expected 3 structures, got " + structs.length);

const pipes = document.querySelectorAll('#viewSvg [data-kind="pipe"]');
console.assert(pipes.length === 2, "expected 2 pipes, got " + pipes.length);

// Depth order: smaller (x+y) rendered FIRST in SVG document order.
// OUT: (0+0)=0, A: (0+-100)=-100, B: (60+-100)=-40.
// Order should be: A (-100), B (-40), OUT (0).
const ids = Array.from(structs).map((g) => g.getAttribute("data-id"));
console.assert(ids[0] === "A" && ids[1] === "B" && ids[2] === "OUT", "depth sort wrong: " + ids.join(","));

// Selected pipe has yellow stroke
const p1 = document.querySelector('#viewSvg [data-id="P1"]');
console.assert(p1.getAttribute("stroke") === "#ffd60a", "selected pipe should be yellow");

console.log("task-15 iso render: OK");
```

## Done when

- `svgEl`, `pipeStrokeWidth`, `structureSymbol`, `renderIso` defined.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-15 iso SVG renderer`.
