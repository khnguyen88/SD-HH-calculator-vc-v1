# Tests for build_golden.py - applies Spec-2 edits to the repaired WIP
# template, producing template_golden.xlsx. Shared fixture `golden_built`
# lives in conftest.py.


def test_skeleton_runs_end_to_end(golden_built):
    # Smoke test: builder completes end-to-end once every edit is
    # implemented. Until Task 1 is done this test fails with
    # NotImplementedError - that's expected.
    assert golden_built is not None
    assert len(golden_built.sheetnames) == 17
