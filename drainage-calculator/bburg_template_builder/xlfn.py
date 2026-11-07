"""Stamp post-2007 Excel functions with their required OOXML `_xlfn.` prefixes.

openpyxl writes formula text verbatim. Excel 365 reads a bare `XLOOKUP(...)` as an
unknown name and renders #NAME? until the workbook is re-saved by Excel. Dynamic-array
functions (FILTER) live in the `_xlws` namespace and take two prefixes.
"""
import re

from openpyxl import Workbook

# (regex, replacement). The lookbehind keeps already-prefixed names untouched: a
# prefixed name is always preceded by a dot, and an identifier character excludes
# user-defined names such as MyXLOOKUP.
_PREFIXES = (
    (re.compile(r"(?<![\w.])FILTER\("), "_xlfn._xlws.FILTER("),
    (re.compile(r"(?<![\w.])XLOOKUP\("), "_xlfn.XLOOKUP("),
    (re.compile(r"(?<![\w.])XMATCH\("), "_xlfn.XMATCH("),
    (re.compile(r"(?<![\w.])MAXIFS\("), "_xlfn.MAXIFS("),
    (re.compile(r"(?<![\w.])MINIFS\("), "_xlfn.MINIFS("),
    (re.compile(r"(?<![\w.])IFS\("), "_xlfn.IFS("),
    (re.compile(r"(?<![\w.])SWITCH\("), "_xlfn.SWITCH("),
)


def prefix_future_functions(wb: Workbook) -> None:
    """Rewrite every cell formula in `wb` in place."""
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                value = cell.value
                if not (isinstance(value, str) and value.startswith("=")):
                    continue
                updated = value
                for pattern, replacement in _PREFIXES:
                    updated = pattern.sub(replacement, updated)
                if updated != value:
                    cell.value = updated
