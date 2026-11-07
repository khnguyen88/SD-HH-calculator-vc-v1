# Task 31: jsdom test harness

## Context

Set up `drainage-calculator/visualizer-tests/` with Node 18 `node --test`, `jsdom`, and the real `xlsx` package. All subsequent test tasks depend on this harness. A loader function reads the dev HTML, boots it into jsdom, and returns a handle exposing `window`, `document`, and the inlined functions.

Implements spec §8 (testing strategy). Mirrors main spec §C.

## Preconditions

- Prior tasks: task-01 (dev HTML exists).
- Node 18+ installed.
- Internet access for `npm install` (one-time).

## Exact changes

**Create** `drainage-calculator/visualizer-tests/package.json`:

```json
{
  "name": "storm-drain-visualizer-tests",
  "version": "1.0.0",
  "private": true,
  "type": "commonjs",
  "scripts": {
    "test": "node --test ."
  },
  "dependencies": {
    "jsdom": "^24.0.0",
    "xlsx": "^0.18.5"
  }
}
```

**Create** `drainage-calculator/visualizer-tests/_harness.js`:

```js
// Shared test harness: boots the dev HTML in jsdom and exposes its globals.
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const DEV_HTML_PATH = path.join(__dirname, "..", "storm-drain-visualizer-dev.html");

function loadVisualizer(extraHeadScripts) {
  const html = fs.readFileSync(DEV_HTML_PATH, "utf8");
  // Replace the SHEETJS sentinel with an inlined bundle when needed; tests pass
  // extraHeadScripts to inject the real `xlsx` module into globalThis.
  const dom = new JSDOM(html, {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    beforeParse(window) {
      if (extraHeadScripts && extraHeadScripts.XLSX) window.XLSX = extraHeadScripts.XLSX;
    }
  });
  return {
    dom,
    window: dom.window,
    document: dom.window.document,
    // Grab any inlined function by name from window scope.
    fn: (name) => dom.window[name]
  };
}

module.exports = { loadVisualizer, DEV_HTML_PATH };
```

**Create** `drainage-calculator/visualizer-tests/sanity.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

test("harness: loads dev HTML and finds the state object", () => {
  const { window } = loadVisualizer();
  assert.ok(window.state, "state missing");
  assert.ok(window.state.ui, "state.ui missing");
  assert.strictEqual(window.state.ui.view, "iso");
});

test("harness: el() function is defined", () => {
  const { fn } = loadVisualizer();
  assert.strictEqual(typeof fn("el"), "function");
});
```

**Create** `drainage-calculator/visualizer-tests/.gitignore`:

```
node_modules/
```

## Installation and run

```powershell
cd drainage-calculator/visualizer-tests
npm install
cd ../..
node --test drainage-calculator/visualizer-tests/
```

Expected output: two passing tests from `sanity.test.js`:

```
# tests 2
# suites 0
# pass 2
# fail 0
```

## Done when

- `drainage-calculator/visualizer-tests/package.json` exists.
- `drainage-calculator/visualizer-tests/_harness.js` exists.
- `drainage-calculator/visualizer-tests/sanity.test.js` exists.
- `node_modules/` present (don't commit); `.gitignore` entry excludes it.
- `node --test drainage-calculator/visualizer-tests/sanity.test.js` prints `pass 2 / fail 0`.
- Commit: `test(visualizer): task-31 jsdom harness + sanity test`.
