# task-40-02 — OOXML structural test: bookSST + no t="str" without formula

## Context

Spec §B.4 and §C.5 require OOXML structural checks to be an automated, permanent part
of the test suite — not a one-off manual step. The two specific defects to guard:
1. `bookSST:true` must be used → shared strings are written as `t:"s"` not `t:"str"`.
2. No cell anywhere should have `t:"str"` without an accompanying formula `f` property.

The existing test file already imports the `xlsx` npm package for independent read-back.

## Preconditions

- task-40-01 is complete (tests run clean).
- `tests/node_modules/xlsx` is installed (it is — see `tests/package.json`).

## Exact changes

**File:** `tests/run-tests.mjs`

Append at the end:

```js
// ==================== OOXML structural checks — spec §B.4, §C.5 ====================
// Uses the xlsx npm package (not window.XLSX) to read back the exported file,
// providing genuine independence per spec §B.4.
import XLSX_NODE from "xlsx";

test("OOXML: no t='str' cell without a formula (bookSST compliance)", () => {
  const wb = sdc.buildWorkbook();
  // Write with bookSST:true (the app's required setting)
  const buf = window.XLSX.write(wb, { bookType: "xlsx", type: "array", bookSST: true });
  // Read back with the npm xlsx package
  const wbRead = XLSX_NODE.read(buf, { type: "array" });
  const violations = [];
  for (const sheetName of wbRead.SheetNames) {
    const ws = wbRead.Sheets[sheetName];
    for (const addr of Object.keys(ws)) {
      if (addr.startsWith("!")) continue;
      const cell = ws[addr];
      if (cell.t === "str" && !cell.f) {
        violations.push(`${sheetName}!${addr}`);
      }
    }
  }
  assert.deepEqual(violations, [],
    "Cells with t='str' and no formula (spec-invalid): " + violations.slice(0,5).join(", "));
});

test("OOXML: shared-string cells present (bookSST:true worked)", () => {
  const wb = sdc.buildWorkbook();
  const buf = window.XLSX.write(wb, { bookType: "xlsx", type: "array", bookSST: true });
  const wbRead = XLSX_NODE.read(buf, { type: "array" });
  let foundSst = false;
  outer: for (const sheetName of wbRead.SheetNames) {
    const ws = wbRead.Sheets[sheetName];
    for (const addr of Object.keys(ws)) {
      if (addr.startsWith("!")) continue;
      if (ws[addr].t === "s") { foundSst = true; break outer; }
    }
  }
  assert.ok(foundSst, "No shared-string (t='s') cells found — bookSST may not be active");
});
```

**Add import at the top of the file** — the existing file uses ES module syntax (`import`).
Find the existing import block at the top and add:
```js
import XLSX_NODE from "xlsx";
```
after the existing imports.

> If the top-level `import XLSX_NODE` conflicts with how the existing test file imports
> things (it uses `import { ... } from "node:..."` style), just ensure the import is
> placed before the first `test(` call.

## Run step

```
cd tests && node --test run-tests.mjs
```

Expected: all prior tests plus 2 new OOXML tests pass.

## Commit

```
git add tests/run-tests.mjs
git commit -m "test(calculator): OOXML structural checks for bookSST and t=str compliance"
```

## Done when

`cd tests && node --test run-tests.mjs` exits 0 with no failures.
