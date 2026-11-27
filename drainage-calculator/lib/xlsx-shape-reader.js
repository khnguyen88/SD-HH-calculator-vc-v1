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
    throw new Error("readSimpleWorkbook not yet implemented (Task 4-6)");
  }

  function readRobustWorkbook(wb){
    throw new Error("readRobustWorkbook not yet implemented (Task 21)");
  }

  const api = { detectShape, readSimpleWorkbook, readRobustWorkbook,
                hglMethodFromLabel };
  if(typeof window !== "undefined") window.__xlsxShapeReader = api;
  if(typeof module !== "undefined" && module.exports) module.exports = api;
})();
