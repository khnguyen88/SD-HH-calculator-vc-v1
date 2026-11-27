"""Build a minimal Robust-shape xlsx fixture for detectShape tests."""
from pathlib import Path
import openpyxl

OUT = Path(__file__).parent / "robust_minimal.xlsx"


def main():
    wb = openpyxl.Workbook()
    wb.active.title = "STORM DRAIN COMPS"
    wb.create_sheet("Outlet Structures")
    wb.save(OUT)


if __name__ == "__main__":
    main()
