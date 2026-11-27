/* xlsx-shape-reader.js — shared Simple/Robust xlsx reader.
   Inlined into both calculator and visualizer by build.js.
   Exposes window.__xlsxShapeReader with:
     detectShape, readSimpleWorkbook, readRobustWorkbook, hglMethodFromLabel */
(function(){
  "use strict";

  function detectShape(wb){
    const names = wb.SheetNames || Object.keys(wb.Sheets || {});
    const has = (n) => names.indexOf(n) !== -1;
    if(has("STORM DRAIN COMPS")){
      if(has("Outlet Structures")) return "robust";
      return "simple";
    }
    return "unknown";
  }

  function hglMethodFromLabel(label){
    const s = String(label||"").toLowerCase();
    if(s.indexOf("hec-22")!==-1 || s.indexOf("hec22")!==-1) return "hec22";
    if(s.indexOf("legacy")!==-1 || s.indexOf("both-end")!==-1
       || s.indexOf("both end")!==-1 || s.indexOf("conservative")!==-1){
      return "legacy-both-crown";
    }
    return "hec22";
  }

  function readSimpleWorkbook(wb){
    const sdc = wb.Sheets["STORM DRAIN COMPS"];
    if(!sdc) throw new Error("Missing STORM DRAIN COMPS sheet");

    const cell = (addr) => {
      const c = sdc[addr];
      if(!c) return "";
      return (c.v !== undefined && c.v !== null) ? c.v : "";
    };

    const pipes = [];
    for(let r = 10; r <= 98; r++){
      const fromId = cell("A"+r);
      if(fromId === "" || fromId == null) continue;
      pipes.push({
        fromId: String(fromId),
        toId: String(cell("B"+r)||""),
        size: cell("N"+r),
        length: cell("O"+r),
        usInvert: cell("P"+r),
        dsInvert: cell("Q"+r),
        angle: cell("R"+r),
        n: cell("S"+r),
        _structureType: cell("AA"+r),
        _rim: cell("AB"+r),
        _inflowAngle1: cell("AG"+r),
        _inflowAngle2: cell("AH"+r),
        _capturedQOverride: cell("AK"+r),
      });
    }

    const jurisdiction = cell("T3") || "MCDOT";
    const pipeStorm    = cell("H3") || "10yr";

    // Pass 1: every unique fromId and toId becomes a structure.
    const seen = Object.create(null);
    for(const p of pipes){
      for(const sid of [p.fromId, p.toId]){
        if(sid && !seen[sid]){
          seen[sid] = {
            structureId: sid, type: "manhole", rim: "", capturedQOverride: "",
          };
        }
      }
    }
    // Pass 2: enrich from the pipe row where A == structureId.
    const byFrom = Object.create(null);
    for(const p of pipes) byFrom[p.fromId] = p;
    for(const sid of Object.keys(seen)){
      const src = byFrom[sid];
      if(src){
        if(src._structureType) seen[sid].type = String(src._structureType).toLowerCase();
        if(src._rim !== "" && src._rim != null) seen[sid].rim = src._rim;
        if(src._capturedQOverride !== "" && src._capturedQOverride != null){
          seen[sid].capturedQOverride = src._capturedQOverride;
        }
      }
    }
    // Pass 3: outfall = structure that only appears as a toId.
    const allFrom = new Set(pipes.map(p => p.fromId));
    for(const sid of Object.keys(seen)){
      if(!allFrom.has(sid) && seen[sid].type === "manhole"){
        seen[sid].type = "outfall";
      }
    }
    const structures = Object.values(seen);

    // ---- C_FACTOR drainage rows ----
    const drainage = [];
    const cf = wb.Sheets["C_FACTOR"];
    if(cf){
      const cellCf = (addr) => {
        const c = cf[addr];
        if(!c) return "";
        return (c.v !== undefined && c.v !== null) ? c.v : "";
      };
      for(let r = 6; r <= 88; r++){
        const sid = cellCf("B"+r);
        if(sid === "" || sid == null) continue;
        drainage.push({
          structureId: String(sid),
          area: cellCf("C"+r),
          C:    cellCf("M"+r),
          tc:   cellCf("V"+r),
        });
      }
    }

    // ---- Config toggles (golden only; defaults otherwise) ----
    const config = {
      junctionAngleRule:   "smaller-loss",
      hglCrownCeilingRule: "crown-plus-1ft",
      hglMethod:           "HEC-22 EGL (d/s crown floor)",
      projectName:         "",
      templateShape:       "simple",
      contractVersion:     1,
    };
    const cfg = wb.Sheets["Config"];
    if(cfg){
      const cellCfg = (addr) => {
        const c = cfg[addr];
        if(!c) return "";
        return (c.v !== undefined && c.v !== null) ? c.v : "";
      };
      if(cellCfg("B1")) config.projectName         = String(cellCfg("B1"));
      if(cellCfg("B3")) config.junctionAngleRule   = String(cellCfg("B3"));
      if(cellCfg("B4")) config.hglCrownCeilingRule = String(cellCfg("B4"));
      if(cellCfg("B5")) config.hglMethod           = String(cellCfg("B5"));
      if(cellCfg("B6")) config.templateShape       = String(cellCfg("B6"));
      if(cellCfg("B7")) config.contractVersion     = Number(cellCfg("B7"));
    }

    return {
      _shape: "simple",
      pipes, structures, drainage, config,
      hydraulics: { jurisdiction, pipeStorm },
    };
  }

  function readRobustWorkbook(wb){
    // Robust files are Simple files + extras. Reuse the Simple reader
    // for overlap, then overlay the Robust-only sheets.
    const base = readSimpleWorkbook(wb);
    base._shape = "robust";

    const tr55 = wb.Sheets["TR-55 Segments"];
    const tr55Segments = [];
    if(tr55){
      const sheetAoa = XLSX.utils.sheet_to_json(tr55, {header:1, raw:true, defval:""});
      const headers = (sheetAoa[0]||[]).map(h => String(h).trim());
      const idx = (name) => headers.indexOf(name);
      for(let i = 1; i < sheetAoa.length; i++){
        const row = sheetAoa[i];
        if(!row.some(v => v !== "" && v != null)) continue;
        tr55Segments.push({
          drainageAreaId: row[idx("Drainage Area")] || "",
          order: row[idx("Order")] || i,
          type: String(row[idx("Type")]||"").toLowerCase(),
          n: row[idx("n")] || "",
          L: row[idx("L (ft)")] || "",
          s: row[idx("s (ft/ft)")] || "",
          P2: row[idx("P2 (in)")] || "",
          surface: row[idx("Surface")] || "",
          area: row[idx("Area a (sf)")] || "",
          wp: row[idx("Wetted Perimeter Pw (ft)")] || "",
        });
      }
    }

    const outletStructures = readSheetAsObjects(wb, "Outlet Structures");
    const outletDevices    = readSheetAsObjects(wb, "Outlet Devices");

    return Object.assign(base, { tr55Segments, outletStructures, outletDevices });
  }

  function readSheetAsObjects(wb, sheetName){
    const ws = wb.Sheets[sheetName];
    if(!ws) return [];
    const aoa = XLSX.utils.sheet_to_json(ws, {header:1, raw:true, defval:""});
    if(aoa.length < 1) return [];
    const headers = aoa[0].map(h => String(h).trim());
    return aoa.slice(1)
      .filter(r => r.some(v => v !== "" && v != null))
      .map(r => {
        const obj = {};
        headers.forEach((h, i) => { obj[h] = r[i]; });
        return obj;
      });
  }

  const api = { detectShape, readSimpleWorkbook, readRobustWorkbook,
                hglMethodFromLabel, readSheetAsObjects };
  if(typeof window !== "undefined") window.__xlsxShapeReader = api;
  if(typeof module !== "undefined" && module.exports) module.exports = api;
})();
