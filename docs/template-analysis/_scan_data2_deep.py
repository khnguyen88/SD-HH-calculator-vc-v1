"""Deep DATA2 verification:
  (1) Every VLOOKUP that reads DATA2 — what col_index is used?
      (If every usage is col_index 2 or 3, we can safely shrink the range
      from $A$2:$D$101 to $A$2:$C$101.)
  (2) Does DATA2!E2:H? duplicate DATA!A68:D159 exactly, or differ?
      (Compare row counts, angle stepping, cell values.)
  (3) Does DATA2!J2:L101 duplicate DATA2!A2:C101 in reverse?
      (Confirm J=B, K=C, L=A to exact values.)
  (4) Sheet-by-sheet search for ANY textual mention of 'DATA2' in a formula,
      including partial-string matches (sanity check for hidden refs).

Run: python docs/template-analysis/_scan_data2_deep.py
"""
import re
from collections import Counter
from pathlib import Path

import openpyxl

HERE = Path(__file__).parent
TARGETS = [HERE.parent / "template_wip_new.xlsx",
           HERE.parent / "template_golden.xlsx"]

VLOOKUP_DATA2 = re.compile(
    r"VLOOKUP\s*\(\s*([^,]+)\s*,\s*'?DATA2'?!\$?[A-Z]+\$?\d*:\$?[A-Z]+\$?\d*\s*,\s*(\d+)",
    re.IGNORECASE,
)
ANY_DATA2 = re.compile(r"(?:'?)DATA2(?:'?)!", re.IGNORECASE)


def scan(xlsx_path):
    print(f"\n=== {xlsx_path.name} ===")
    wb = openpyxl.load_workbook(xlsx_path, data_only=False)

    # (1) Every VLOOKUP into DATA2 — gather col_index counts.
    col_index_counts = Counter()
    all_data2_refs = []  # (sheet, cell, formula) for any DATA2 reference
    for sheet_name in wb.sheetnames:
        if sheet_name == "DATA2":
            continue
        s = wb[sheet_name]
        for row in s.iter_rows():
            for cell in row:
                v = cell.value
                if not isinstance(v, str) or not v.startswith("="):
                    continue
                if not ANY_DATA2.search(v):
                    continue
                all_data2_refs.append((sheet_name, cell.coordinate, v))
                for m in VLOOKUP_DATA2.finditer(v):
                    _, idx = m.groups()
                    col_index_counts[int(idx)] += 1

    print(f"  (1) VLOOKUP col_index usage into DATA2:")
    for idx, cnt in sorted(col_index_counts.items()):
        print(f"    col_index={idx}: {cnt} formulas")
    print(f"  Total DATA2-referencing formulas (any form): {len(all_data2_refs)}")

    # Show a few distinct formula patterns as a sanity spot-check.
    patterns = Counter()
    for _, _, f in all_data2_refs:
        normalized = re.sub(r"[A-Z]+\d+", "{CELL}", f)
        patterns[normalized] += 1
    print(f"  Distinct formula patterns reading DATA2 (top 5):")
    for pat, cnt in patterns.most_common(5):
        print(f"    [{cnt}x] {pat[:120]}")

    # (2) DATA2 vs DATA Kb-table comparison.
    ws_data2 = wb["DATA2"]
    ws_data = wb["DATA"]
    print(f"  (2) DATA2 E-H (Kb duplicate) vs DATA A68:D159 (live Kb):")
    # Find last row of DATA2 E-H block.
    last_e_row = 1
    for r in range(2, 200):
        if ws_data2[f"E{r}"].value in (None, "") and \
           ws_data2[f"F{r}"].value in (None, "") and \
           ws_data2[f"G{r}"].value in (None, ""):
            break
        last_e_row = r
    print(f"    DATA2 E-H occupied rows: 2..{last_e_row} "
          f"({last_e_row - 1} data rows)")
    print(f"    DATA   A68:D159 rows: 68..159 (92 data rows)")
    print(f"    DATA2!E stepping (first 6 rows):")
    for r in range(2, 8):
        print(f"      row {r}: E={ws_data2[f'E{r}'].value}, "
              f"F={ws_data2[f'F{r}'].value}, "
              f"G={ws_data2[f'G{r}'].value}, "
              f"H={ws_data2[f'H{r}'].value}")
    print(f"    DATA!A68:D73 stepping (first 6 rows):")
    for r in range(68, 74):
        print(f"      row {r}: A={ws_data[f'A{r}'].value}, "
              f"B={ws_data[f'B{r}'].value}, "
              f"C={ws_data[f'C{r}'].value}, "
              f"D={ws_data[f'D{r}'].value}")

    # Check angle stepping.
    e_angles = []
    for r in range(2, last_e_row + 1):
        v = ws_data2[f"E{r}"].value
        if isinstance(v, (int, float)):
            e_angles.append(v)
    data_angles = []
    for r in range(68, 160):
        v = ws_data[f"A{r}"].value
        if isinstance(v, (int, float)):
            data_angles.append(v)
    print(f"    DATA2 E angle range: [{min(e_angles) if e_angles else 'n/a'}, "
          f"{max(e_angles) if e_angles else 'n/a'}] "
          f"({len(e_angles)} rows)")
    if len(e_angles) >= 2:
        print(f"    DATA2 E stepping: {e_angles[1] - e_angles[0]}")
    print(f"    DATA  A angle range: [{min(data_angles)}, "
          f"{max(data_angles)}] ({len(data_angles)} rows)")
    if len(data_angles) >= 2:
        print(f"    DATA  A stepping: {data_angles[1] - data_angles[0]}")

    # (3) J-L reverse-duplicate check.
    print(f"  (3) J-L vs A-C reversed:")
    mismatches = 0
    for r in range(2, 102):
        a = ws_data2[f"A{r}"].value
        b = ws_data2[f"B{r}"].value
        c = ws_data2[f"C{r}"].value
        j = ws_data2[f"J{r}"].value
        k = ws_data2[f"K{r}"].value
        l = ws_data2[f"L{r}"].value
        # Expected: J == B, K == C, L == A.
        if (j != b) or (k != c) or (l != a):
            mismatches += 1
            if mismatches <= 3:
                print(f"    row {r} mismatch: A={a},B={b},C={c} "
                      f"vs J={j},K={k},L={l}")
    print(f"    Total mismatches: {mismatches} / 100 rows")

    # (4) Any formula on DATA2 itself that references another sheet?
    print(f"  (4) DATA2 self-formulas (should be zero):")
    self_formulas = 0
    for row in ws_data2.iter_rows():
        for cell in row:
            v = cell.value
            if isinstance(v, str) and v.startswith("="):
                self_formulas += 1
                if self_formulas <= 3:
                    print(f"    {cell.coordinate}: {v[:80]}")
    print(f"    Total DATA2 formulas: {self_formulas}")


for p in TARGETS:
    if p.exists():
        scan(p)
