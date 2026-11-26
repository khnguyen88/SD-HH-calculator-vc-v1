"""One-off: empirically verify DATA2 structure + external references.

Reports:
  (1) DATA2 occupied column letters, header values, row span.
  (2) Count of cross-sheet references into each DATA2 column.
  (3) Sample references (first 5 per column) for spot-check.

Run: python docs/template-analysis/_scan_data2.py
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl

HERE = Path(__file__).parent
TARGETS = [HERE.parent / "template_wip_new.xlsx",
           HERE.parent / "template_golden.xlsx"]

# DATA2 absolute or relative references, column-aware.
# Matches: DATA2!A2, DATA2!$A$2:$D$101, 'DATA2'!A2, DATA2!A:A, etc.
REF_RE = re.compile(
    r"(?:'?DATA2'?!)\$?([A-Z]+)\$?(\d*)(?::\$?([A-Z]+)\$?(\d*))?",
    re.IGNORECASE,
)


def col_letter_to_idx(letter):
    n = 0
    for ch in letter.upper():
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def cols_in_range(c1, c2):
    i1, i2 = col_letter_to_idx(c1), col_letter_to_idx(c2)
    lo, hi = min(i1, i2), max(i1, i2)
    out = []
    for i in range(lo, hi + 1):
        # back to letter
        s = ""
        v = i
        while v > 0:
            v, r = divmod(v - 1, 26)
            s = chr(ord("A") + r) + s
        out.append(s)
    return out


def scan(xlsx_path):
    print(f"\n=== {xlsx_path.name} ===")
    wb = openpyxl.load_workbook(xlsx_path, data_only=False)
    if "DATA2" not in wb.sheetnames:
        print("  (no DATA2 sheet)")
        return
    ws = wb["DATA2"]

    # (1) Occupied column span + header row + row span.
    max_col = 0
    max_row = 0
    for row in ws.iter_rows():
        for cell in row:
            if cell.value not in (None, ""):
                if cell.column > max_col:
                    max_col = cell.column
                if cell.row > max_row:
                    max_row = cell.row
    print(f"  Dimensions: {ws.dimensions} (openpyxl-reported), "
          f"last populated cell col={max_col} row={max_row}")

    # Header values row 1, each column A..max_col.
    print(f"  Row 1 headers:")
    for col in range(1, max_col + 1):
        c = ws.cell(row=1, column=col)
        letter = c.coordinate.rstrip("1")
        print(f"    {letter}1 = {c.value!r}")

    # Sample row 2 (first data row) + row 101 (last expected) per column.
    print(f"  Row 2 sample:")
    for col in range(1, max_col + 1):
        c = ws.cell(row=2, column=col)
        letter = c.coordinate.rstrip("2")
        print(f"    {letter}2 = {c.value!r}")
    print(f"  Row {max_row} sample:")
    for col in range(1, max_col + 1):
        c = ws.cell(row=max_row, column=col)
        letter = c.coordinate.rstrip(str(max_row))
        print(f"    {letter}{max_row} = {c.value!r}")

    # (2) Scan ALL sheets (not DATA2 itself) for formula references into DATA2.
    hits_per_col = defaultdict(int)
    samples_per_col = defaultdict(list)

    for sheet_name in wb.sheetnames:
        if sheet_name == "DATA2":
            continue
        s = wb[sheet_name]
        for row in s.iter_rows():
            for cell in row:
                v = cell.value
                if not isinstance(v, str) or not v.startswith("="):
                    continue
                for m in REF_RE.finditer(v):
                    c1, _, c2, _ = m.groups()
                    if c2:
                        cols = cols_in_range(c1, c2)
                    else:
                        cols = [c1.upper()]
                    for col in cols:
                        hits_per_col[col] += 1
                        if len(samples_per_col[col]) < 3:
                            samples_per_col[col].append(
                                f"{sheet_name}!{cell.coordinate} -> {v[:80]}"
                            )

    print(f"  Cross-sheet reference counts into DATA2 columns:")
    all_cols = sorted(set(list(hits_per_col.keys()) +
                          [openpyxl.utils.get_column_letter(i)
                           for i in range(1, max_col + 1)]))
    for col in all_cols:
        count = hits_per_col.get(col, 0)
        print(f"    DATA2!{col}: {count} references")
        for samp in samples_per_col.get(col, []):
            print(f"      - {samp}")


def main():
    for p in TARGETS:
        if p.exists():
            scan(p)
        else:
            print(f"(skipped, missing: {p})")


if __name__ == "__main__":
    main()
