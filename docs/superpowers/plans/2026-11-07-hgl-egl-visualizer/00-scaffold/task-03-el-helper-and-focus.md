# Task 03: Add el() DOM helper and withFocusPreserved

## Context

Insert the two foundational DOM helpers between the `// ==== dom-helpers: begin ==== / end ====` sentinels. Every subsequent task uses `el()` to build DOM nodes and `withFocusPreserved` around any input handler that triggers a render.

**Critical:** the `el()` null/undefined guard is not optional. Main spec §A.1 explains why — `setAttribute(name, null)` stringifies to the literal text `"null"`, which for boolean attributes makes the browser treat the condition as always true. This is a bug that shipped in the main app and must not recur here.

Implements spec §0 (same helpers as main app), main spec §A.1 and §A.2.

## Preconditions

- Prior tasks: task-01.
- File `visualizer/storm-drain-visualizer-dev.html` exists with the `// ==== dom-helpers: begin ==== / end ====` sentinels empty.

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Replace the entire block between the two sentinels (inclusive of the sentinel lines) with:

```js
  // ==== dom-helpers: begin ====
  function el(tag, attrs, children) {
    const e = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      const v = attrs[k];
      if (k === "class") e.className = v;
      else if (k === "html") e.innerHTML = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (v === null || v === undefined) { /* skip: do NOT setAttribute(k, null) */ }
      else e.setAttribute(k, v);
    }
    if (children) (Array.isArray(children) ? children : [children]).forEach((c) => {
      if (c == null) return;
      e.appendChild((c instanceof Node) ? c : document.createTextNode(String(c)));
    });
    return e;
  }

  function withFocusPreserved(renderFn) {
    const active = document.activeElement;
    const key = active && active.dataset && active.dataset.focusKey;
    const selStart = active && typeof active.selectionStart === "number" ? active.selectionStart : null;
    const selEnd   = active && typeof active.selectionEnd   === "number" ? active.selectionEnd   : null;
    renderFn();
    if (key) {
      const match = document.querySelector('[data-focus-key="' + CSS.escape(key) + '"]');
      if (match) {
        match.focus();
        if (match.setSelectionRange && selStart !== null) {
          try { match.setSelectionRange(selStart, selEnd); } catch (e) { /* ignore */ }
        }
      }
    }
  }
  // ==== dom-helpers: end ====
```

## Acceptance test

Create a tiny inline smoke test. **In the browser DevTools console** of the dev HTML (opened by double-click), run:

```js
// Null/undefined guard
const d1 = el("div", { hidden: null }, "x");
console.assert(d1.outerHTML === "<div>x</div>", "null-guard failed:", d1.outerHTML);

// Normal attributes
const d2 = el("input", { type: "text", "data-focus-key": "k1" });
console.assert(d2.getAttribute("type") === "text", "attr failed");
console.assert(d2.dataset.focusKey === "k1", "data-attr failed");

// Children as array
const d3 = el("div", null, [el("span", null, "a"), el("span", null, "b")]);
console.assert(d3.children.length === 2, "children failed");

// Event listener via on*
let clicked = 0;
const d4 = el("button", { onclick: () => clicked++ }, "click");
d4.click();
console.assert(clicked === 1, "onclick failed");

// withFocusPreserved roundtrip
document.body.appendChild(d2);
d2.focus();
withFocusPreserved(() => {
  // simulate re-render by removing and recreating with the same focus-key
  d2.remove();
  document.body.appendChild(el("input", { type: "text", "data-focus-key": "k1" }));
});
console.assert(document.activeElement.dataset.focusKey === "k1", "focus not preserved");

console.log("dom-helpers smoke test: OK");
```

Expected console output: `dom-helpers smoke test: OK` (no AssertionError messages).

This smoke test is inline-only; task-32 adds a proper test harness.

## Done when

- The `dom-helpers` sentinel block contains exactly the code above.
- The browser DevTools console smoke test prints `dom-helpers smoke test: OK` with no AssertionError.
- Running `node visualizer/build-visualizer.js` still succeeds.
- Commit: `feat(visualizer): task-03 el() helper and withFocusPreserved`.
