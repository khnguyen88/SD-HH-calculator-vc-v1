import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";
import { test } from "node:test";
import assert from "node:assert/strict";

const html = readFileSync(
  new URL("../drainage-calculator/storm-drain-design-calculator.html", import.meta.url),
  "utf8"
);

const dom = new JSDOM(html, {
  runScripts: "dangerously",  // safe: HTML is our own trusted source file
  resources: "usable",
  pretendToBeVisual: true,
});
const { window } = dom;

// Poll until __sdc is populated (DOMContentLoaded fires the init() call)
await new Promise((resolve, reject) => {
  const start = Date.now();
  const interval = setInterval(() => {
    if (window.__sdc) { clearInterval(interval); resolve(); }
    else if (Date.now() - start > 2000) { clearInterval(interval); reject(new Error("__sdc not populated after 2s")); }
  }, 20);
});

const sdc = window.__sdc;

// --- Smoke tests ---
test("__sdc is populated", () => {
  assert.ok(sdc, "__sdc not exposed on window");
});

test("__sdc exposes key functions", () => {
  assert.equal(typeof sdc.computeTotalFlow, "function", "computeTotalFlow missing");
  assert.equal(typeof sdc.buildWorkbook, "function", "buildWorkbook missing");
  assert.equal(typeof sdc.state, "object", "state missing");
});

test("state has expected shape", () => {
  assert.ok(Array.isArray(sdc.state.drainage), "state.drainage not array");
  assert.ok(Array.isArray(sdc.state.pipes), "state.pipes not array");
});
