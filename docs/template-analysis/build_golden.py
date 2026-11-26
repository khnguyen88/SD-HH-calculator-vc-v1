# Apply Spec-2 edits to the Spec-1 repaired WIP template to produce the
# golden rulebook-aligned template.
#
# Usage: python build_golden.py <wip_source.xlsx> <golden_output.xlsx>
#
# Six edits are applied in order (all idempotent):
#   1. add_config_sheet        - new Config tab with 3 toggle named ranges
#   2. rewire_junction_angle_rule - toggle-aware controlling-angle formula
#   3. add_hgl_crown_ceiling_checks - clearance columns on HGL + HGL(25YEAR)
#   4. annotate_hgl_method     - top-of-sheet hglMethod stamp
#   5. add_u7_small_area_tc_lookup - Table 3-3 Tc lookup on C_FACTOR col W
#   6. annotate_equations_sheet - toggle + citation annotations
#
# Spec: docs/superpowers/specs/2026-11-25-golden-template-design.md
import sys

import openpyxl


def add_config_sheet(wb):
    raise NotImplementedError("Task 1")


def rewire_junction_angle_rule(wb):
    raise NotImplementedError("Task 2")


def add_hgl_crown_ceiling_checks(wb):
    raise NotImplementedError("Task 3")


def annotate_hgl_method(wb):
    raise NotImplementedError("Task 4")


def add_u7_small_area_tc_lookup(wb):
    raise NotImplementedError("Task 5")


def annotate_equations_sheet(wb):
    raise NotImplementedError("Task 6")


def main(src, dst):
    wb = openpyxl.load_workbook(src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    annotate_hgl_method(wb)
    add_u7_small_area_tc_lookup(wb)
    annotate_equations_sheet(wb)
    wb.save(dst)
    print(f"wrote {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: build_golden.py <wip_source.xlsx> <golden_output.xlsx>",
              file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
