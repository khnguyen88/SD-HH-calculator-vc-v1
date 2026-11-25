"""Pass A: dump structured JSON describing every sheet in a template xlsx.

Usage: python extract.py <input.xlsx> <output.json>

Produces, for each sheet: name, dimensions, Table definitions, formula count,
#REF! error count, list of cross-sheet references (sheet names referenced in
any formula on this sheet), and the raw formula text for later review.
Workbook-level: list of defined names that resolve to #REF! or external links.
"""
import json
import re
import sys
from pathlib import Path

import openpyxl

SHEET_REF_RE = re.compile(r"'([^']+)'!|([A-Za-z_][A-Za-z0-9_ ]*)!")


def scan_sheet(ws, all_sheet_names):
    formulas = []
    ref_errors = 0
    cross_sheet = set()
    for row in ws.iter_rows():
        for cell in row:
            v = cell.value
            text = None
            if isinstance(v, str) and v.startswith("="):
                text = v
            elif hasattr(v, "text") and isinstance(getattr(v, "text", None), str):
                text = v.text  # ArrayFormula
            if text is None:
                continue
            formulas.append({"cell": cell.coordinate, "formula": text})
            if "#REF!" in text:
                ref_errors += 1
            for m in SHEET_REF_RE.finditer(text):
                name = (m.group(1) or m.group(2) or "").strip()
                if name and name in all_sheet_names and name != ws.title:
                    cross_sheet.add(name)
    tables = []
    if getattr(ws, "tables", None):
        for tname, tref in ws.tables.items():
            tables.append({"name": tname, "ref": tref})
    return {
        "name": ws.title,
        "max_row": ws.max_row,
        "max_col": ws.max_column,
        "formula_count": len(formulas),
        "ref_error_count": ref_errors,
        "tables": tables,
        "cross_sheet_refs": sorted(cross_sheet),
        "formulas": formulas,
    }


def scan_defined_names(wb):
    broken = []
    duplicates = {}
    for name in wb.defined_names:
        d = wb.defined_names[name]
        val = getattr(d, "value", None) or str(d)
        if "#REF!" in val:
            broken.append({"name": name, "value": val})
        duplicates.setdefault(val, []).append(name)
    dup_report = [
        {"range": rng, "names": names}
        for rng, names in duplicates.items()
        if len(names) > 1
    ]
    return broken, dup_report


def main(src, dst):
    wb = openpyxl.load_workbook(src, data_only=False)
    names = wb.sheetnames
    sheets = [scan_sheet(wb[n], set(names)) for n in names]
    broken, dups = scan_defined_names(wb)
    out = {
        "source": str(src),
        "sheet_count": len(names),
        "sheets": sheets,
        "broken_defined_names": broken,
        "duplicate_defined_names": dups,
    }
    Path(dst).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {dst}: {len(sheets)} sheets, "
          f"{sum(s['ref_error_count'] for s in sheets)} #REF! formulas, "
          f"{len(broken)} broken names, {len(dups)} duplicate-name ranges")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: extract.py <in.xlsx> <out.json>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
