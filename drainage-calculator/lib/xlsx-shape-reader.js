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
    // Pre-Spec-3 calculator native format (Spec 4).
    if(has("Pipe Sizing") && has("Junction Structure")) return "legacy-native";
    return "unknown";
  }

  function hglMethodFromLabel(_label){
    // Spec 6: HGL method is always HEC-22. Kept as a function for
    // backward-compat with callers that pass the result through.
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

    // ---- Rainfall Settings (Robust-only — custom + fetched NOAA) ----
    // Format: key/value pairs in col A/B. Static keys plus optional
    // Custom NOAA 5/10/15/30/60-min and the Fetched NOAA metadata +
    // 8 storms × 5 durations grid (when a NOAA location was fetched).
    const rainfallSettings = {};
    const rfWs = wb.Sheets["Rainfall Settings"];
    if(rfWs){
      const aoa = XLSX.utils.sheet_to_json(rfWs, {header:1, raw:false, defval:""});
      for(const row of aoa){
        const k = String(row[0]||"").trim();
        if(k) rainfallSettings[k] = row[1];
      }
    }

    return Object.assign(base, {
      tr55Segments, outletStructures, outletDevices, rainfallSettings,
    });
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

  function readLegacyNativeWorkbook(wb){
    // Pre-Spec-3 calculator native xlsx (Spec 4). Separate sheets per
    // entity; no STORM DRAIN COMPS. Output shape matches readRobust so
    // applyRobustReaderResult can consume it directly.
    const pipeRows = readSheetAsObjects(wb, "Pipe Sizing");
    const structRows = readSheetAsObjects(wb, "Junction Structure");
    const daRows = readSheetAsObjects(wb, "Drainage Area");

    const pipes = pipeRows
      .filter(r => r["From Structure"] !== "" && r["From Structure"] != null)
      .map(r => ({
        // Legacy exports carry an explicit ID (e.g., "r12") on col A.
        id: (r["ID"] !== "" && r["ID"] != null) ? String(r["ID"]) : "",
        fromId: String(r["From Structure"] || ""),
        toId: String(r["To Structure"] || ""),
        size: r["Size (in or SPANxRISE)"] || "",
        length: r["Length (ft)"] || "",
        usInvert: (r["US Invert (ft)"] !== "" && r["US Invert (ft)"] != null)
          ? r["US Invert (ft)"] : "",
        dsInvert: (r["DS Invert (ft)"] !== "" && r["DS Invert (ft)"] != null)
          ? r["DS Invert (ft)"] : "",
        angle: r["Angle (deg)"] || 0,
        n: (r["n"] !== "" && r["n"] != null) ? r["n"] : 0.013,
        // Normalize splitRole to a top-level field (visualizer reads it).
        splitRole: String(r["Split Role"] || "").toLowerCase(),
        _splitRole: r["Split Role"] || "",
        _structureType: "",
        _rim: "",
        _inflowAngle1: "",
        _inflowAngle2: "",
        _capturedQOverride: "",
      }));

    const structures = structRows
      .filter(r => r["Structure ID"] !== "" && r["Structure ID"] != null)
      .map(r => ({
        structureId: String(r["Structure ID"] || ""),
        type: String(r["Type"] || "manhole").toLowerCase(),
        rim: (r["Rim-Grate Elev (ft)"] !== "" && r["Rim-Grate Elev (ft)"] != null)
          ? r["Rim-Grate Elev (ft)"] : "",
        // Legacy-only fields the visualizer consumes.
        startElev: (r["Fixed-Start Elev (ft)"] !== "" && r["Fixed-Start Elev (ft)"] != null)
          ? r["Fixed-Start Elev (ft)"] : "",
        forceElev: String(r["Force Fixed"] || "").toUpperCase() === "TRUE",
        totalQ: (r["Total Flow (cfs)"] !== "" && r["Total Flow (cfs)"] != null)
          ? r["Total Flow (cfs)"] : "",
        outPipeId: String(r["Outgoing Pipe ID"] || ""),
        capturedQ: (r["Captured Q (cfs)"] !== "" && r["Captured Q (cfs)"] != null)
          ? r["Captured Q (cfs)"] : "",
        capturedQOverride: "",
      }));

    const drainage = daRows
      .filter(r => r["ID"] !== "" && r["ID"] != null)
      .map(r => ({
        // Legacy carries DA's own ID separately from the linked structure.
        id: String(r["ID"] || ""),
        // "Structure" column links the DA to the capturing structure.
        structureId: String(r["Structure"] || ""),
        area: r["Area A (ac)"] || "",
        C: r["C"] || "",
        tc: r["Tc (min)"] || "",
      }));

    // TR-55 Segments: identical sheet layout to Robust.
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

    // Rainfall Settings is a key/value sheet in legacy as in Robust.
    const rainfallSettings = {};
    const rfWs = wb.Sheets["Rainfall Settings"];
    if(rfWs){
      const aoa = XLSX.utils.sheet_to_json(rfWs, {header:1, raw:false, defval:""});
      for(const row of aoa){
        const k = String(row[0]||"").trim();
        if(k) rainfallSettings[k] = row[1];
      }
    }

    // No Config sheet in legacy — derive hglMethod from Rainfall Settings
    // IF PRESENT. Leave as empty string when absent so consumers can
    // distinguish "no explicit value" from "default value" (prevents a
    // missing Rainfall Settings sheet from silently overriding the
    // consumer's current hglMethod toggle).
    const config = {
      junctionAngleRule:   "smaller-loss",
      hglCrownCeilingRule: "crown-plus-1ft",
      hglMethod: rainfallSettings["HGL Method"]
        ? String(rainfallSettings["HGL Method"]) : "",
      projectName: "",
      templateShape: "legacy-native",
      contractVersion: 1,
    };
    const ovSheet = wb.Sheets["Overview"];
    if(ovSheet){
      const aoa = XLSX.utils.sheet_to_json(ovSheet, {header:1, raw:false, defval:""});
      if(aoa[1] && aoa[1][1]) config.projectName = String(aoa[1][1]);
    }

    const jurisdiction = "MCDOT";
    const pipeStorm = String(rainfallSettings["Pipe & HGL Design Storm"] || "10yr");

    return {
      _shape: "legacy-native",
      pipes, structures, drainage, config,
      tr55Segments, outletStructures, outletDevices, rainfallSettings,
      hydraulics: { jurisdiction, pipeStorm },
    };
  }

  const api = { detectShape, readSimpleWorkbook, readRobustWorkbook,
                readLegacyNativeWorkbook,
                hglMethodFromLabel, readSheetAsObjects };
  if(typeof window !== "undefined") window.__xlsxShapeReader = api;
  if(typeof module !== "undefined" && module.exports) module.exports = api;
})();
