/*
 * Splitter ledger test: a flow splitter has two outgoing pipes. The Hb row
 * must use the structure's DECLARED outgoing pipe (outPipeId) and declared
 * total flow, not "the first pipe whose fromId matches" — otherwise the
 * secondary branch can be mistaken for the primary and the wrong Aout/Qtotal
 * feed the structure-loss equation.
 */
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

test("splitter ledger: hb row uses declared out-pipe and total flow", () => {
  const { window } = loadVisualizer();

  const imported = {
    structures: [
      { id: "OUT", type: "outfall" },
      { id: "S", type: "splitter", totalQ: 10, outPipeId: "PA" }
    ],
    // Deliberately list the SECONDARY pipe first so a naive fromId lookup
    // would pick PB (18-in, Q=4) instead of the declared PA (24-in, Q=6).
    pipes: [
      {
        id: "PB", fromId: "S", toId: "OUT", shape: "circular", size: 18,
        n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 4
      },
      {
        id: "PA", fromId: "S", toId: "OUT", shape: "circular", size: 24,
        n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 6
      }
    ],
    outfall: { structureId: "OUT", tailwaterElev: 100 },
    config: {},
    kbTable: null
  };
  const stateObj = { imported, overrides: { byId: {} } };

  const rows = window.buildLedger(["OUT", "PA", "S"], stateObj, window.KB_SEED, "hec22");
  const hb = rows.find((r) => r.kind === "hb");
  assert.ok(hb, "hb row produced for the splitter");
  assert.strictEqual(hb.id, "S");

  assert.strictEqual(hb.detail.Qtotal, 10, "declared structure totalQ used");
  const paArea = window.pipeArea("circular", 24);
  const pbArea = window.pipeArea("circular", 18);
  assert.notStrictEqual(paArea, pbArea);
  assert.strictEqual(hb.detail.Aout, paArea, "Aout from declared PA (24-in), not PB");
});
