# Task 16: Profile (elevation) SVG renderer

## Context

`renderProfile(svgEl, state, ledgerRows)` draws the 2D elevation profile along the currently-walked path: two polylines for crown/invert, two polylines for HGL (solid)/EGL (dashed), and vertical bars for structures. Implements spec §3.2.

## Preconditions

- Prior tasks: task-01, task-03, task-08, task-09, task-12, task-13, task-15 (shares `svgEl` helper).

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the `views` sentinel block after task-15:

```js
  // --- Profile render (task-16) ---

  // Given a ledger walk (rows from buildLedger + annotateLedgerHgl), produce an array
  // of {station, kind, id, invert, crown, egl, hgl, rim?} points marching up the path.
  function profileStations(rows, imported, overrides) {
    const stations = [];
    let station = 0;
    const elev = (str, field, fallback) => {
      const v = str ? str[field] : null;
      return (typeof v === "number" && isFinite(v)) ? v : fallback;
    };
    for (const row of rows) {
      if (row.kind === "start") {
        const str = imported.structures.find((s) => s.id === row.id);
        stations.push({
          station: 0, kind: "structure", id: row.id,
          invert: elev(str, "startElev", row.after - 3),
          crown: elev(str, "crown", row.after),
          rim: elev(str, "rim", row.after + 3),
          egl: row.after, hgl: row.hgl != null ? row.hgl : row.after
        });
      } else if (row.kind === "hf") {
        const pipe = imported.pipes.find((p) => p.id === row.id);
        const rawLength = (overrides && overrides.byId[row.id] && overrides.byId[row.id].length != null)
          ? overrides.byId[row.id].length
          : (pipe ? pipe.length : 0);
        const length = Number(rawLength);
        // March station forward by this pipe's length (horizontally — profile ignores plan curvature)
        if (isFinite(length) && length > 0) station += length;
        // Crown and invert at the upstream end of this pipe come from the From structure.
        const fromStr = pipe ? imported.structures.find((s) => s.id === pipe.fromId) : null;
        stations.push({
          station, kind: "pipe", id: row.id,
          invert: elev(fromStr, "startElev", row.after - 3),
          crown: elev(fromStr, "crown", row.after),
          rim: null,
          egl: row.after, hgl: row.hgl != null ? row.hgl : row.after
        });
      } else if (row.kind === "hb") {
        const str = imported.structures.find((s) => s.id === row.id);
        stations.push({
          station, kind: "structure", id: row.id,
          invert: elev(str, "startElev", row.after - 3),
          crown: elev(str, "crown", row.after),
          rim: elev(str, "rim", row.after + 3),
          egl: row.after, hgl: row.hgl != null ? row.hgl : row.after
        });
      }
      // skip 'end' rows — they share position with the last structure
    }
    return stations;
  }

  function renderProfile(svg, s, annotatedRows) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    if (!s.imported || !annotatedRows || annotatedRows.length === 0) {
      svg.appendChild(svgEl("text", { x: 10, y: 20, fill: "#8b949e" }, "No path to profile."));
      return;
    }
    const stations = profileStations(annotatedRows, s.imported, s.overrides);
    if (stations.length === 0) return;

    const xs = stations.map((p) => p.station);
    const ys = stations.flatMap((p) => [p.invert, p.crown, p.egl, p.hgl, p.rim].filter((v) => typeof v === "number" && isFinite(v)));
    if (ys.length === 0) ys.push(0);
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = Math.min(...ys), yMax = Math.max(...ys);
    const pad = 20;
    const W = 800, H = 300;
    const sx = (x) => pad + (x - xMin) / Math.max(1e-9, xMax - xMin) * (W - 2 * pad);
    const sy = (y) => H - pad - (y - yMin) / Math.max(1e-9, yMax - yMin) * (H - 2 * pad);
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);

    const poly = (color, dashed, picker) => {
      const pts = stations.map((p) => `${sx(p.station)},${sy(picker(p))}`).join(" ");
      return svgEl("polyline", Object.assign(
        { points: pts, fill: "none", stroke: color, "stroke-width": 2 },
        dashed ? { "stroke-dasharray": "6 3" } : {}
      ));
    };

    svg.appendChild(poly("#8b949e", false, (p) => p.crown));
    svg.appendChild(poly("#8b949e", false, (p) => p.invert));
    svg.appendChild(poly("#ffd60a", false, (p) => p.hgl));
    svg.appendChild(poly("#58a6ff", true,  (p) => p.egl));

    // Structure vertical bars
    const cursorId = s.cursor && s.cursor.id;
    for (const p of stations) {
      if (p.kind !== "structure") continue;
      const isSel = cursorId === p.id;
      const top = (p.rim != null) ? p.rim : p.crown + 3;
      svg.appendChild(svgEl("line", {
        x1: sx(p.station), y1: sy(p.invert),
        x2: sx(p.station), y2: sy(top),
        stroke: isSel ? "#ffd60a" : "#30363d",
        "stroke-width": isSel ? 3 : 2,
        "data-kind": "structure", "data-id": p.id
      }));
      svg.appendChild(svgEl("text", {
        x: sx(p.station) + 4, y: sy(top) - 4,
        fill: "#c9d1d9", "font-size": 10, "font-family": "ui-monospace,monospace"
      }, p.id));
    }

    // Cursor band for pipe selection
    if (s.cursor && s.cursor.kind === "pipe") {
      const idx = stations.findIndex((p) => p.id === s.cursor.id);
      if (idx > 0) {
        const left = stations[idx - 1].station, right = stations[idx].station;
        const width = sx(right) - sx(left);
        if (width >= 0.5) {
          svg.appendChild(svgEl("rect", {
            x: sx(left), y: 0,
            width: width, height: H,
            fill: "#ffd60a", "fill-opacity": 0.08,
            "pointer-events": "none",
            "data-kind": "pipe", "data-id": s.cursor.id
          }));
        }
      }
    }
  }
```

## Acceptance test

In DevTools console (requires compute tasks 08-13 done):

```js
state.imported = {
  structures: [
    { id: "OUT", type: "outfall", x: 0, y: 0, rim: 103, startElev: 97, crown: 99 },
    { id: "A",   type: "bend",    x: 0, y: -100, rim: 105, startElev: 98, crown: 100 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.01, length: 100, angle: 0, designQ: 5 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };
state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };

const rows = buildLedger(["OUT", "P1", "A"], state, null, "hec22");
const annotated = annotateLedgerHgl(rows, state, "hec22");
renderProfile(document.getElementById("viewSvg"), state, annotated);

const polys = document.querySelectorAll('#viewSvg polyline');
console.assert(polys.length === 4, "expected 4 polylines (crown, invert, hgl, egl), got " + polys.length);

const bars = document.querySelectorAll('#viewSvg [data-kind="structure"]');
console.assert(bars.length === 2, "expected 2 structure bars, got " + bars.length);

// Cursor band for selected pipe
const bands = document.querySelectorAll('#viewSvg rect[data-kind="pipe"]');
console.assert(bands.length === 1, "expected 1 cursor band");

console.log("task-16 profile: OK");
```

## Done when

- `profileStations`, `renderProfile` defined in the `views` sentinel block.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-16 profile SVG renderer`.
