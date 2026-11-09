/*
 * Drift guard: the embedded "calculator-demo" sample must stay a faithful
 * mirror of the main calculator's seedExample() demo. This test boots the
 * calculator dev HTML headless (same instrumentation technique as
 * fixtures/generate-fixture.js), runs seedExample(), maps the resulting
 * state into the visualizer JSON shape, and compares against the embedded
 * sample. If the calculator demo changes, this fails and the sample must
 * be updated to match.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");
const XLSX = require("xlsx");
const { loadVisualizer } = require("./_harness");

const CALC_DEV = path.join(__dirname, "..", "..", "drainage-calculator",
  "storm-drain-design-calculator-dev.html");

function loadCalculatorDemo() {
  const html = fs.readFileSync(CALC_DEV, "utf8");
  const marker = '"use strict";';
  const idx = html.indexOf(marker);
  if (idx < 0) throw new Error('no "use strict" marker in calculator dev html');
  const injection = marker +
    "\nglobalThis.__getApp = () => ({ state, seedExample, computeStructureCalc });";
  const dom = new JSDOM(html.slice(0, idx) + injection + html.slice(idx + marker.length), {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    beforeParse(window) {
      window.XLSX = XLSX;
      window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
    }
  });
  const app = dom.window.__getApp();
  app.seedExample();
  return { dom, state: app.state, app };
}

// Round every finite number to 5 decimals so float noise (e.g. secondary
// split flow 0.09382999999999964) compares equal to the embedded 0.09383.
function canon(v) {
  if (Array.isArray(v)) return v.map(canon);
  if (v && typeof v === "object") {
    const out = {};
    for (const k of Object.keys(v)) out[k] = canon(v[k]);
    return out;
  }
  if (typeof v === "number" && isFinite(v)) return Number(v.toFixed(5));
  return v;
}

// Inverts: calculator state stores them as numbers or blank strings; the
// visualizer sample schema wants finite numbers or null.
const invNum = (v) => {
  const n = (v === "" || v == null) ? null : Number(v);
  return (n != null && isFinite(n)) ? n : null;
};

// Both sides come from different jsdom realms (calculator + visualizer), so
// deepStrictEqual would reject matching values on prototype identity alone.
// A JSON round-trip rebuilds both in the Node realm first.
function nodeRealm(v) {
  return JSON.parse(JSON.stringify(v));
}

test("calculator-demo sample matches seedExample() (drift guard)", () => {
  const viz = loadVisualizer();
  const sample = viz.window.SAMPLES["calculator-demo"].data;
  const calc = loadCalculatorDemo();
  const s = calc.state;

  // Structures in state push order. rim is "" for outfalls -> null.
  // crown = calc.crown of the structure's outgoing pipe (null for outfalls).
  const mappedStructures = s.structures.map((st) => {
    const c = calc.app.computeStructureCalc(st.id);
    return {
      id: st.structureId,
      type: st.type,
      rim: (st.rim === "" || st.rim == null) ? null : st.rim,
      startElev: st.forceElev ? st.startElev : null,
      crown: (c && c.crown != null) ? Number(c.crown) : null
    };
  });

  // Pipes in push order. designQ comes from the FROM structure's computed
  // flow: splitInfo.primaryQ / secondaryQ for split pipes, else outPipeFlow.
  const mappedPipes = s.pipes.map((p, i) => {
    const fromSt = s.structures.find((x) => x.id === p.fromStructureId);
    const toSt = s.structures.find((x) => x.id === p.toStructureId);
    const c = calc.app.computeStructureCalc(p.fromStructureId);
    let designQ = null;
    if (c) {
      if (p.splitRole === "secondary") designQ = c.splitInfo ? c.splitInfo.secondaryQ : null;
      else if (p.splitRole === "primary") designQ = c.splitInfo ? c.splitInfo.primaryQ : c.outPipeFlow;
      else designQ = c.outPipeFlow;
    }
    return {
      id: "P" + (i + 1),
      fromId: fromSt.structureId,
      toId: toSt.structureId,
      shape: p.shape,
      size: Number(p.size),
      n: p.n,
      slope: p.slope,
      length: p.length,
      angle: p.angle,
      splitRole: p.splitRole || "",
      designQ,
      usInvert: invNum(p.upstreamInvert),
      dsInvert: invNum(p.downstreamInvert)
    };
  });

  // Drainage rows: the DA's own label lives in row.structureId (e.g. "DA-1");
  // the receiving structure is found via structure.drainageAreaId === row.id.
  const mappedDrainage = s.drainage.map((d) => {
    const st = s.structures.find((x) => x.drainageAreaId === d.id);
    return {
      id: d.structureId,
      structureId: st ? st.structureId : "",
      areaAc: d.area,
      C: d.C,
      tc: d.tc
    };
  });

  const mappedTr55 = [];
  for (const d of s.drainage) {
    const segs = (d.tr55 && d.tr55.segments) || [];
    segs.forEach((seg, i) => {
      mappedTr55.push({
        drainageAreaId: d.structureId,
        order: i + 1,
        type: seg.type,
        n: seg.n != null ? seg.n : null,
        L: seg.L,
        s: seg.s,
        P2: seg.P2 != null ? seg.P2 : null,
        surface: seg.surface || "",
        area: seg.area != null ? seg.area : null,
        wp: seg.wp != null ? seg.wp : null
      });
    });
  }

  assert.deepStrictEqual(nodeRealm(canon(mappedStructures)), nodeRealm(canon(sample.structures)),
    "structures drifted from seedExample() — update SAMPLES[\"calculator-demo\"]");
  assert.deepStrictEqual(nodeRealm(canon(mappedPipes)), nodeRealm(canon(sample.pipes)),
    "pipes drifted from seedExample() — update SAMPLES[\"calculator-demo\"]");
  assert.deepStrictEqual(nodeRealm(canon(mappedDrainage)), nodeRealm(canon(sample.drainageAreas)),
    "drainageAreas drifted from seedExample() — update SAMPLES[\"calculator-demo\"]");
  assert.deepStrictEqual(nodeRealm(canon(mappedTr55)), nodeRealm(canon(sample.tr55Segments)),
    "tr55Segments drifted from seedExample() — update SAMPLES[\"calculator-demo\"]");

  calc.dom.window.close();
  viz.dom.window.close();
});
