# Mobile Responsive Topbar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a three-section mobile topbar (project title | ☰ hamburger | Import + Export) that appears at ≤760px, replacing the sidebar nav with a dropdown panel.

**Architecture:** Single-file edit to `storm-drain-design-calculator-dev.html` — add CSS classes, insert two HTML elements, add one JS utility function, and update `renderNav()` and `init()`. Desktop layout is untouched. After editing, run `node drainage-calculator/build.js` to regenerate the user-facing file.

**Tech Stack:** Vanilla HTML/CSS/JS, no dependencies.

---

### Task 1: Add CSS — new classes and mobile overrides

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html` (CSS block, lines 7–523)

The CSS block ends at `</style>` around line 523. Find the existing mobile media query:
```css
@media (max-width:760px){
  .app{ grid-template-columns:1fr; }
  .sidebar{ flex-direction:row; overflow-x:auto; }
  .nav{ flex-direction:row; }
}
```

- [ ] **Step 1: Replace the existing mobile media query block**

Find and replace the entire `@media (max-width:760px)` block with:

```css
@media (max-width:760px){
  .sidebar{ display:none; }
  .topbar{ gap:8px; padding:10px 14px; }
  .topbar-center{ display:flex; }
  .mobile-hidden{ display:none !important; }
}
```

- [ ] **Step 2: Add the two new always-present classes immediately before the closing `</style>` tag**

Insert before `</style>`:

```css
.topbar-center{
  display:none;
  align-items:center;
  flex:0 0 auto;
}
.mobile-nav-panel{
  display:none;
  flex-direction:column;
  background:var(--panel);
  border-bottom:1px solid var(--border);
  padding:8px;
  gap:2px;
}
.mobile-nav-panel.open{ display:flex; }
```

- [ ] **Step 3: Verify CSS was inserted correctly**

```bash
grep -n "topbar-center\|mobile-nav-panel\|mobile-hidden" drainage-calculator/storm-drain-design-calculator-dev.html
```
Expected: at least 6 lines — definitions of `.topbar-center`, `.mobile-nav-panel`, `.mobile-nav-panel.open`, `.mobile-hidden`, and the media query overrides.

---

### Task 2: Add HTML — topbar-center and mobile-nav-panel

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html` (HTML body, around lines 546–566)

- [ ] **Step 1: Add `topbar-center` inside `.topbar`, between `.topbar-left` and `.topbar-right`**

Find this line in the HTML:
```html
      <div class="topbar-right">
```

Insert immediately before it:
```html
      <div class="topbar-center">
        <button class="btn btn-sm" id="hamburgerBtn" aria-label="Open navigation menu">&#9776; Menu</button>
      </div>
```

- [ ] **Step 2: Add `mobile-hidden` class to secondary action buttons**

Find and update these four elements in `.topbar-right` (add `mobile-hidden` to their existing `class` attributes):

```html
<!-- Before → After -->
<button class="btn btn-sm" id="saveCompBtn" ...>
→ <button class="btn btn-sm mobile-hidden" id="saveCompBtn" ...>

<button class="btn btn-sm" id="printAllTablesBtn" ...>
→ <button class="btn btn-sm mobile-hidden" id="printAllTablesBtn" ...>

<button class="btn btn-sm" id="printAllDetailBtn" ...>
→ <button class="btn btn-sm mobile-hidden" id="printAllDetailBtn" ...>

<div class="saves-wrap">
→ <div class="saves-wrap mobile-hidden">
```

- [ ] **Step 3: Add `.mobile-nav-panel` div after `.topbar`, before `.content`**

Find:
```html
    <div class="content">
```

Insert immediately before it:
```html
    <div class="mobile-nav-panel" id="mobileNavPanel">
      <nav id="mobileNav"></nav>
    </div>
```

- [ ] **Step 4: Verify HTML changes**

```bash
grep -n "hamburgerBtn\|mobileNavPanel\|mobileNav\|mobile-hidden" drainage-calculator/storm-drain-design-calculator-dev.html
```
Expected: `hamburgerBtn` (1 line), `mobileNavPanel` (1 line), `mobileNav` (2 lines — the div and the nav), `mobile-hidden` (4 lines — saveCompBtn, printAllTablesBtn, printAllDetailBtn, saves-wrap).

---

### Task 3: Add JS — closeMobileNav, update renderNav, wire init

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html` (JS, around `renderNav` at line ~2373)

- [ ] **Step 1: Add `closeMobileNav()` immediately before `renderNav()`**

Find:
```js
function renderNav(){
```

Insert immediately before it:
```js
function closeMobileNav() {
  document.getElementById("mobileNavPanel").classList.remove("open");
}
```

- [ ] **Step 2: Update `renderNav()` to populate `#mobileNav`**

Find the closing `}` of the existing `renderNav()` function. The function currently ends after:
```js
  document.getElementById("tabLabel").textContent = activeTab ? activeTab.label : "";
}
```

Insert the mobile nav loop **before** that final closing `}`:

```js
  const mobileNav = document.getElementById("mobileNav");
  mobileNav.innerHTML = "";
  tabs.forEach((t, i) => {
    const btn = el("button", {
      class: "nav-btn" + (state.active === t.id ? " active" : ""),
      onclick: () => { state.active = t.id; closeMobileNav(); renderAll(); }
    }, [ el("span", {class:"nav-num"}, String(i+1).padStart(2,"0")), t.label ]);
    mobileNav.appendChild(btn);
  });
```

- [ ] **Step 3: Wire hamburger toggle and outside-click close in `init()`**

Find `function init()` (around line 6516). Inside `init()`, locate where other button event listeners are registered (look for lines like `document.getElementById("exportBtn").addEventListener` or `document.getElementById("importBtn").addEventListener`).

Add immediately after those existing button listeners:

```js
  document.getElementById("hamburgerBtn").addEventListener("click", (e) => {
    e.stopPropagation();
    document.getElementById("mobileNavPanel").classList.toggle("open");
  });
  document.addEventListener("click", () => closeMobileNav());
```

- [ ] **Step 4: Verify JS changes**

```bash
grep -n "closeMobileNav\|mobileNav\|hamburgerBtn" drainage-calculator/storm-drain-design-calculator-dev.html
```
Expected: `closeMobileNav` (3 lines — definition + call in mobile nav onclick + call in document click listener), `mobileNav` (3 lines — innerHTML clear + forEach + appendChild), `hamburgerBtn` (2 lines — HTML and addEventListener).

---

### Task 4: Build, verify, commit, and deploy

**Files:**
- Run: `node drainage-calculator/build.js`
- Rebuild produces: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Run the build**

```bash
node drainage-calculator/build.js
```
Expected output: `Built: NNN KB dev → ~756 KB dist`

- [ ] **Step 2: Open the built file and verify desktop is unchanged**

Open `drainage-calculator/storm-drain-design-calculator.html` in a browser. At normal desktop width:
- Sidebar visible with all tab buttons
- Topbar shows project name left, action buttons right
- No hamburger button visible

- [ ] **Step 3: Verify mobile layout in browser devtools**

In browser devtools, set viewport to 375px width (iPhone):
- Sidebar gone
- Topbar shows: [project name] [☰ Menu button] [↑ Import] [↓ Export to Excel]
- Save, Tables, Detail, Saves buttons are hidden
- Tap ☰ Menu → dropdown panel appears below topbar with all tab buttons numbered
- Tap a tab → panel closes, correct view loads
- Tap anywhere outside panel → panel closes

- [ ] **Step 4: Commit both dev and built files**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: mobile responsive topbar with hamburger nav dropdown"
```

- [ ] **Step 5: Deploy to gh-pages**

```bash
git worktree add .worktrees/gh-pages gh-pages
cp drainage-calculator/storm-drain-design-calculator.html .worktrees/gh-pages/index.html
cd .worktrees/gh-pages
git add index.html
git commit -m "Deploy: mobile responsive topbar with hamburger nav"
git push origin gh-pages
cd ../..
git worktree remove .worktrees/gh-pages
```

- [ ] **Step 6: Push main**

```bash
git push origin main
```
