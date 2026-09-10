# LocalStorage Quick-Save / Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Save / Saves ▾ buttons to the header that let users snapshot up to 5 full project states in localStorage and restore or delete them.

**Architecture:** All logic is added inline to the single HTML file. A `getSaves`/`setSaves` pair owns localStorage I/O with error handling. `captureState`/`restoreState` handle deep-clone serialisation of the `state` object. A popover div beneath the `Saves ▾` button is re-rendered on every open/mutate. No auto-save; every action is explicit.

**Tech Stack:** Vanilla JS, inline CSS, localStorage — no new dependencies.

---

## File Structure

**Only one file is modified:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`
  - CSS block (around line 332): add popover + save-row styles
  - HTML topbar-right (line 477–481): add Save button, Saves button, popover div
  - JS (after `function toast` ~line 1922): add storage helpers and comp functions
  - `init()` (~line 5007): wire up button listeners and outside-click close

---

## Task 1: Add CSS for the saves popover

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (CSS block, around line 340)

- [ ] **Step 1: Locate the CSS insertion point**

  Find the line `#toast.err b{ color:var(--fail); }` (around line 342). Insert the new CSS block immediately after it.

- [ ] **Step 2: Add popover and save-row CSS**

  Insert after `#toast.err b{ color:var(--fail); }`:
  ```css
  .saves-wrap{ position:relative; }
  .saves-popover{
    display:none;
    position:absolute;
    top:calc(100% + 6px);
    right:0;
    z-index:200;
    background:var(--panel);
    border:1px solid var(--border);
    border-radius:var(--radius);
    min-width:320px;
    max-width:420px;
    box-shadow:0 4px 16px rgba(0,0,0,0.4);
    padding:10px 0;
  }
  .saves-popover.open{ display:block; }
  .saves-popover-header{
    padding:4px 14px 8px;
    font-size:11px;
    color:var(--muted);
    border-bottom:1px solid var(--border-soft);
    margin-bottom:6px;
  }
  .saves-empty{ padding:8px 14px; color:var(--muted); font-size:12.5px; }
  .save-row{
    display:flex;
    align-items:baseline;
    gap:8px;
    padding:5px 14px;
  }
  .save-row:hover{ background:rgba(255,255,255,0.03); }
  .save-row-name{
    flex:1;
    font-size:12.5px;
    color:var(--text);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    font-family:var(--font-mono);
  }
  ```

- [ ] **Step 3: Open the file in the browser and confirm no visual regressions** (new CSS is not yet visible since no HTML references it)

- [ ] **Step 4: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 1: add CSS for saves popover"
  ```

---

## Task 2: Add HTML buttons and popover div to the topbar

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (HTML, around line 477–481)

- [ ] **Step 1: Locate the topbar-right div**

  Find this block (around line 477):
  ```html
        <button class="btn" id="importBtn" title="Import a previously exported .xlsx file">&#8593; Import from Excel</button>
        <input type="file" id="importFile" accept=".xlsx">
        <button class="btn btn-primary" id="exportBtn" title="Export all tables to a .xlsx file">&#8595; Export to Excel</button>
  ```

- [ ] **Step 2: Insert Save + Saves buttons before the Import button**

  Replace that block with:
  ```html
        <button class="btn btn-sm" id="saveCompBtn" title="Save current project to browser storage">&#8964; Save</button>
        <div class="saves-wrap">
          <button class="btn btn-sm" id="savesMenuBtn">Saves (<span id="savesCount">0</span>) &#9660;</button>
          <div class="saves-popover" id="savesPopover">
            <div class="saves-popover-header">Saved in this browser only &mdash; export to Excel for a permanent record</div>
            <div id="savesList"></div>
          </div>
        </div>
        <button class="btn" id="importBtn" title="Import a previously exported .xlsx file">&#8593; Import from Excel</button>
        <input type="file" id="importFile" accept=".xlsx">
        <button class="btn btn-primary" id="exportBtn" title="Export all tables to a .xlsx file">&#8595; Export to Excel</button>
  ```

- [ ] **Step 3: Open in browser and verify** — two new buttons appear in the header. Clicking them does nothing yet. No regressions.

- [ ] **Step 4: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 2: add Save + Saves buttons and popover shell to topbar HTML"
  ```

---

## Task 3: Add storage helpers (getSaves / setSaves)

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (JS, after `function toast` ~line 1922)

- [ ] **Step 1: Locate insertion point**

  Find `function delBtn(onClick){` (around line 1923). Insert the new functions immediately before it.

- [ ] **Step 2: Add getSaves and setSaves**

  Insert before `function delBtn(onClick){`:
  ```js
  const SAVES_KEY = "sdCalc_saves";
  const SAVES_MAX = 5;

  function getSaves(){
    try {
      const raw = localStorage.getItem(SAVES_KEY);
      if(!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch(e) {
      return [];
    }
  }

  function setSaves(saves){
    try {
      localStorage.setItem(SAVES_KEY, JSON.stringify(saves));
    } catch(e) {
      toast("Browser storage unavailable — save not written.", true);
    }
  }
  ```

- [ ] **Step 3: Verify in browser console**

  Open DevTools → Console and run:
  ```js
  setSaves([{id:"test", name:"Test", projectName:"Test", savedAt:Date.now(), state:{}}]);
  console.log(getSaves());
  // Expected: array with one object
  setSaves([]);
  console.log(getSaves());
  // Expected: []
  ```

- [ ] **Step 4: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 3: add getSaves/setSaves localStorage helpers"
  ```

---

## Task 4: Add captureState / restoreState helpers

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (JS, after `setSaves`)

- [ ] **Step 1: Add captureState and restoreState**

  Insert immediately after the `setSaves` function (still before `function delBtn`):
  ```js
  function captureState(){
    const snap = JSON.parse(JSON.stringify({
      drainage: state.drainage,
      structures: state.structures,
      pipes: state.pipes,
      kb: state.kb,
      outletStructures: state.outletStructures,
      outletDevices: state.outletDevices,
      activeOutletId: state.activeOutletId,
      outletShowGeometryDetail: state.outletShowGeometryDetail,
      inletSpacing: state.inletSpacing,
      inletSpacingSettings: state.inletSpacingSettings,
      rainfall: state.rainfall,
    }));
    return snap;
  }

  function restoreState(snap, projectName){
    state.drainage = snap.drainage || [];
    state.structures = snap.structures || [];
    state.pipes = snap.pipes || [];
    state.kb = snap.kb || defaultKbRows();
    state.outletStructures = snap.outletStructures || [];
    state.outletDevices = snap.outletDevices || [];
    state.activeOutletId = snap.activeOutletId || "";
    state.outletShowGeometryDetail = snap.outletShowGeometryDetail !== undefined ? snap.outletShowGeometryDetail : true;
    state.inletSpacing = snap.inletSpacing || [];
    state.inletSpacingSettings = snap.inletSpacingSettings || defaultInletSpacingSettings();
    state.rainfall = snap.rainfall || defaultRainfallSettings();
    state.project = projectName;
    document.getElementById("projectName").value = projectName;
    renderAll();
  }
  ```

- [ ] **Step 2: Verify in browser console**

  Run:
  ```js
  const snap = captureState();
  console.log(Object.keys(snap));
  // Expected: ["drainage","structures","pipes","kb","outletStructures","outletDevices","activeOutletId","outletShowGeometryDetail","inletSpacing","inletSpacingSettings","rainfall"]
  ```

- [ ] **Step 3: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 4: add captureState/restoreState helpers"
  ```

---

## Task 5: Implement saveComp, renderSavesPopover, loadComp, deleteComp

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (JS, after `restoreState`)

- [ ] **Step 1: Add the four comp functions**

  Insert immediately after `restoreState` (still before `function delBtn`):
  ```js
  function formatSaveTimestamp(ms){
    const d = new Date(ms);
    const pad = n => String(n).padStart(2,"0");
    return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+pad(d.getHours())+":"+pad(d.getMinutes());
  }

  function saveComp(){
    const saves = getSaves();
    if(saves.length >= SAVES_MAX){
      toast("Save limit reached — delete a save first.", true);
      return;
    }
    const projectName = document.getElementById("projectName").value || "Untitled";
    const now = Date.now();
    const entry = {
      id: "save_"+now+"_"+Math.random().toString(36).slice(2,7),
      name: projectName + " — " + formatSaveTimestamp(now),
      projectName: projectName,
      savedAt: now,
      state: captureState(),
    };
    saves.push(entry);
    setSaves(saves);
    updateSavesUI();
    toast("Saved <b>"+escapeHtml(entry.name)+"</b>.");
  }

  function loadComp(id){
    const saves = getSaves();
    const entry = saves.find(s => s.id === id);
    if(!entry) return;
    restoreState(entry.state, entry.projectName);
    closeSavesPopover();
    toast("Loaded <b>"+escapeHtml(entry.name)+"</b>.");
  }

  function deleteComp(id){
    const saves = getSaves().filter(s => s.id !== id);
    setSaves(saves);
    updateSavesUI();
  }

  function renderSavesPopover(){
    const saves = getSaves();
    const list = document.getElementById("savesList");
    list.innerHTML = "";
    if(saves.length === 0){
      list.appendChild(el("div",{class:"saves-empty"},"No saves yet."));
      return;
    }
    saves.slice().reverse().forEach(entry => {
      const row = el("div",{class:"save-row"});
      row.appendChild(el("span",{class:"save-row-name", title:entry.name}, entry.name));
      const loadBtn = el("button",{class:"btn btn-sm", onclick:()=>loadComp(entry.id)}, "Load");
      const delBtn2 = el("button",{class:"btn btn-sm", style:"color:var(--fail);", title:"Delete this save", onclick:()=>deleteComp(entry.id)}, "✕");
      row.appendChild(loadBtn);
      row.appendChild(delBtn2);
      list.appendChild(row);
    });
  }

  function updateSavesUI(){
    const saves = getSaves();
    document.getElementById("savesCount").textContent = saves.length;
    const saveBtn = document.getElementById("saveCompBtn");
    if(saves.length >= SAVES_MAX){
      saveBtn.disabled = true;
      saveBtn.title = "Save limit reached ("+SAVES_MAX+") — delete a save first";
    } else {
      saveBtn.disabled = false;
      saveBtn.title = "Save current project to browser storage";
    }
    renderSavesPopover();
  }

  function closeSavesPopover(){
    document.getElementById("savesPopover").classList.remove("open");
  }
  ```

- [ ] **Step 2: Verify escapeHtml exists**

  Search the file for `function escapeHtml` — it must exist (used in toast calls throughout the file). If it does not exist, add it before `saveComp`:
  ```js
  function escapeHtml(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
  ```

- [ ] **Step 3: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 5: add saveComp, loadComp, deleteComp, renderSavesPopover, updateSavesUI"
  ```

---

## Task 6: Wire up buttons in init() and add outside-click close

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (`init()` ~line 5007, and `document.addEventListener("DOMContentLoaded"...)`)

- [ ] **Step 1: Locate the init() wiring block**

  Find this block in `init()` (around line 5014):
  ```js
    document.getElementById("exportBtn").addEventListener("click", exportExcel);
    const fileInput = document.getElementById("importFile");
    document.getElementById("importBtn").addEventListener("click", ()=> fileInput.click());
  ```

- [ ] **Step 2: Add saves button wiring before the existing exportBtn line**

  Insert before `document.getElementById("exportBtn").addEventListener(...)`:
  ```js
    updateSavesUI();

    document.getElementById("saveCompBtn").addEventListener("click", saveComp);

    document.getElementById("savesMenuBtn").addEventListener("click", (e)=>{
      e.stopPropagation();
      const pop = document.getElementById("savesPopover");
      const isOpen = pop.classList.contains("open");
      if(!isOpen) renderSavesPopover();
      pop.classList.toggle("open", !isOpen);
    });

    document.addEventListener("click", (e)=>{
      const pop = document.getElementById("savesPopover");
      if(pop.classList.contains("open") && !pop.contains(e.target) && e.target.id !== "savesMenuBtn"){
        closeSavesPopover();
      }
    });
  ```

- [ ] **Step 3: Open in browser and run the full manual test**

  **Test A — Save:**
  1. Edit the project name to "Test Project A". Click **Save**.
  2. Toast "Saved Test Project A — ..." appears.
  3. Click **Saves (1) ▾** — popover opens. One row shows "Test Project A — <timestamp>".

  **Test B — Popover close:**
  4. Click outside the popover — it closes.
  5. Click **Saves (1) ▾** again — it re-opens. Click the button again — it closes.

  **Test C — Load:**
  6. Edit the project name to "Different Name". Add a new pipe row.
  7. Click **Saves (1) ▾** → **Load** on the saved entry.
  8. Project name reverts to "Test Project A". The extra pipe row is gone.

  **Test D — Delete:**
  9. Click **Saves (1) ▾** → **✕** on the saved entry.
  10. Popover now shows "No saves yet." Count badge shows 0.

  **Test E — Save limit:**
  11. Save 5 times (edit project name between each so names differ).
  12. After the 5th save, the **Save** button is disabled. Tooltip says "Save limit reached (5) — delete a save first".
  13. Delete one save — **Save** button re-enables.

  **Test F — Storage unavailable (manual simulation):**
  14. In DevTools console, run `localStorage.setItem = ()=>{throw new Error("QuotaExceeded")}` then click Save.
  15. Toast shows error "Browser storage unavailable — save not written."
  16. Reload page to restore normal behaviour.

- [ ] **Step 4: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 6: wire saves buttons in init(), add outside-click close"
  ```

---

## Task 7: Update CLAUDE.md and spec to reflect localStorage allowance

**Files:**
- Modify: `drainage-calculator/storm-drain-calculator-spec.md` (Section 0, ~line 14)
- Modify: `CLAUDE.md` (Rules section)

- [ ] **Step 1: Update the spec's non-negotiable constraints**

  Find this line in `storm-drain-calculator-spec.md`:
  ```
  - **No localStorage/sessionStorage.** Persistence is via explicit Export/Import to `.xlsx` only.
  ```
  Replace with:
  ```
  - **No auto-save via localStorage/sessionStorage.** Persistence for the permanent record is via explicit Export/Import to `.xlsx` only. A browser-local quick-save feature (up to 5 named snapshots, user-triggered) is the one permitted use of localStorage — see `docs/superpowers/specs/2026-09-10-localstorage-save-delete-design.md`.
  ```

- [ ] **Step 2: Update CLAUDE.md**

  Find in `CLAUDE.md`:
  ```
  - Persistence is explicit Excel export/import only — no localStorage.
  ```
  Replace with:
  ```
  - Persistence for the permanent record is explicit Excel export/import only. Browser localStorage is permitted only for the quick-save feature (≤5 user-triggered snapshots).
  ```

- [ ] **Step 3: Commit**
  ```
  git add drainage-calculator/storm-drain-calculator-spec.md CLAUDE.md
  git commit -m "Task 7: update spec and CLAUDE.md to allow localStorage quick-save"
  ```
