/*
 * Unit tests for the pure post-import analysis pass (analyzeImported).
 *
 * analyzeImported(imported) is DOM-free: it takes a plain imported object and
 * returns read-only derived facts (walk starts, splitters, missing Design Q,
 * the TR-55 join). These tests call it directly through the jsdom window so a
 * regression in the derivation logic fails independently of the renderers.
 */
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

// Objects returned by the jsdom-realm function carry jsdom prototypes; normalise
// through JSON so deepStrictEqual compares plain data (same trick as roundtrip.test.js).
const plain = (v) => JSON.parse(JSON.stringify(v));

function analyze(imported) {
  const { window } = loadVisualizer();
  return window.analyzeImported(imported);
}

test("analysis: outfalls list in import order, first outfall is default walk start", () => {
  const a = analyze({
    structures: [
      { id: "OUTFALL", type: "outfall" },
      { id: "BYPASS", type: "outfall" },
      { id: "A", type: "manhole" }
    ],
    pipes: []
  });

  assert.deepStrictEqual(plain(a.outfallIds), ["OUTFALL", "BYPASS"]);
  assert.strictEqual(a.defaultWalkStart, "OUTFALL");
});

test("analysis: with no outfall, default start is lowest startElev", () => {
  const a = analyze({
    structures: [
      { id: "A", type: "manhole", startElev: 105, rim: 110 },
      { id: "B", type: "inlet", startElev: 100, rim: 120 },
      { id: "C", type: "bend", startElev: 102, rim: 101 }
    ],
    pipes: []
  });
  assert.strictEqual(a.defaultWalkStart, "B");
});

test("analysis: no outfall and no finite startElev ties break by lowest rim", () => {
  const a = analyze({
    structures: [
      { id: "A", type: "manhole", rim: 110 },
      { id: "B", type: "inlet", rim: 100 }
    ],
    pipes: []
  });
  assert.strictEqual(a.defaultWalkStart, "B");
});

test("analysis: no outfall, no finite startElev or rim falls back to first structure", () => {
  const a = analyze({
    structures: [
      { id: "A", type: "manhole" },
      { id: "B", type: "inlet" }
    ],
    pipes: []
  });
  assert.strictEqual(a.defaultWalkStart, "A");
});

test("analysis: splitter primary pipe prefers splitRole primary", () => {
  const a = analyze({
    structures: [{ id: "S", type: "splitter" }],
    pipes: [
      { id: "Q1", fromId: "S", toId: "OUT", splitRole: "secondary" },
      { id: "Q2", fromId: "S", toId: "B", splitRole: "primary" }
    ]
  });
  assert.deepStrictEqual(plain(a.splitterIds), ["S"]);
  assert.strictEqual(a.primaryPipeByStructureId["S"], "Q2");
});

test("analysis: splitter without roles picks the first outgoing pipe in order", () => {
  const a = analyze({
    structures: [{ id: "S", type: "splitter" }],
    pipes: [
      { id: "X1", fromId: "S", toId: "OUT" },
      { id: "X2", fromId: "S", toId: "B" }
    ]
  });
  assert.strictEqual(a.primaryPipeByStructureId["S"], "X1");
});

test("analysis: missing Design Q flags null/undefined but not numeric zero", () => {
  const a = analyze({
    structures: [{ id: "S", type: "manhole" }],
    pipes: [
      { id: "five", fromId: "S", toId: "OUT", designQ: 5 },
      { id: "zero", fromId: "S", toId: "OUT", designQ: 0 },
      { id: "nil", fromId: "S", toId: "OUT", designQ: null },
      { id: "undef", fromId: "S", toId: "OUT" }
    ]
  });
  assert.deepStrictEqual(plain(a.missingDesignQ), ["nil", "undef"]);
  assert.ok(!a.missingDesignQ.includes("five"), "numeric designQ is present");
  assert.ok(!a.missingDesignQ.includes("zero"), "numeric 0 is present, not missing");
});

test("analysis: TR-55 segments join by DA and sort by order; empty structureId dropped", () => {
  const a = analyze({
    structures: [{ id: "ST-1", type: "inlet" }],
    pipes: [],
    drainageAreas: [
      { id: "DA-1", structureId: "ST-1", tc: 19.4 },
      { id: "DA-2", structureId: "", tc: 10 },
      { id: "DA-3", tc: 5 }
    ],
    tr55Segments: [
      { drainageAreaId: "DA-1", order: 2, type: "shallow" },
      { drainageAreaId: "DA-1", order: 1, type: "sheet" }
    ]
  });

  assert.deepStrictEqual(plain(Object.keys(a.tr55ByStructureId)), ["ST-1"]);
  const blocks = a.tr55ByStructureId["ST-1"];
  assert.strictEqual(blocks.length, 1);
  assert.strictEqual(blocks[0].daId, "DA-1");
  assert.strictEqual(blocks[0].tc, 19.4);
  assert.deepStrictEqual(plain(blocks[0].segments.map((s) => s.order)), [1, 2]);
});

test("analysis: analyzeImported(null) returns null", () => {
  assert.strictEqual(analyze(null), null);
});

test("analysis: walkStarts lists all outfalls before non-outfall structures", () => {
  const a = analyze({
    structures: [
      { id: "OUT", type: "outfall" },
      { id: "A", type: "manhole" },
      { id: "BYP", type: "outfall" },
      { id: "B", type: "bend" }
    ],
    pipes: []
  });

  assert.deepStrictEqual(plain(a.walkStarts), [
    { id: "OUT", label: "OUT", type: "outfall", group: "outfall" },
    { id: "BYP", label: "BYP", type: "outfall", group: "outfall" },
    { id: "A", label: "A", type: "manhole", group: "structure" },
    { id: "B", label: "B", type: "bend", group: "structure" }
  ]);
  const groups = a.walkStarts.map((w) => w.group);
  assert.strictEqual(groups.indexOf("structure") > groups.lastIndexOf("outfall"), true,
    "every outfall-group entry precedes every structure-group entry");
});
