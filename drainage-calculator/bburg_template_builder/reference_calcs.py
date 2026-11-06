"""Python reference implementations of hydraulic calcs used by the template.

Purpose: these functions compute the same quantities that the Excel formulas on
IDF_Lookup, Pipe Capacity, and HGL sheets compute. Tests verify this Python
reference against hand-calculated values; the Excel formulas are designed to
produce identical results when Excel evaluates them.

If Excel vs reference values diverge on any sheet, one of them has a bug.
"""
from __future__ import annotations
import math
from typing import Literal


GRAVITY_FT_S2 = 32.2


def interpolate_pl(
    tc_min: float,
    depths_by_duration_min: dict[int, float],
) -> float:
    """Power-law interpolate a rainfall intensity (in/hr) from NOAA14 depths.

    Mirrors the HTML calculator's interpolatePL() function (dev HTML line 1178+).
    Given point depths at durations {5, 10, 15, 30, 60} min, fit i = 60*a*t^(b-1)
    between the two bracketing durations, where t is in minutes.
    """
    durations = sorted(depths_by_duration_min.keys())
    if tc_min <= durations[0]:
        d = depths_by_duration_min[durations[0]]
        return 60.0 * d / durations[0]
    if tc_min >= durations[-1]:
        d = depths_by_duration_min[durations[-1]]
        return 60.0 * d / durations[-1]
    # Find bracketing durations
    t_lo, t_hi = durations[0], durations[1]
    for i in range(len(durations) - 1):
        if durations[i] <= tc_min <= durations[i + 1]:
            t_lo, t_hi = durations[i], durations[i + 1]
            break
    d_lo = depths_by_duration_min[t_lo]
    d_hi = depths_by_duration_min[t_hi]
    # Power-law fit: d = a * t^b, so b = ln(d_hi/d_lo) / ln(t_hi/t_lo), a = d_lo / t_lo^b
    b = math.log(d_hi / d_lo) / math.log(t_hi / t_lo)
    a = d_lo / (t_lo ** b)
    depth_at_tc = a * (tc_min ** b)
    return 60.0 * depth_at_tc / tc_min


def manning_sf_full(q_cfs: float, n: float, diameter_in: float) -> float:
    """Full-flow Manning's friction slope for a circular pipe (ft/ft).

    Sf = (Q * n / (1.486 * A_full * R_full^(2/3)))^2
    with A_full = pi/4 * (D/12)^2 and R_full = D/48.
    """
    d_ft = diameter_in / 12.0
    area_full = math.pi * d_ft ** 2 / 4.0
    r_full = d_ft / 4.0
    conveyance = 1.486 * area_full * (r_full ** (2.0 / 3.0))
    return (q_cfs * n / conveyance) ** 2


def velocity_head(v_fps: float) -> float:
    """V^2 / (2g)."""
    return v_fps ** 2 / (2.0 * GRAVITY_FT_S2)


HglMethod = Literal["hec22", "legacy"]


def hgl_walk_step(
    hgl_dn_raw: float,
    crown_dn: float,
    crown_up: float,
    hf: float,
    method: HglMethod,
) -> tuple[float, float]:
    """Compute (HGL_dn_final, HGL_up_final) for a single pipe step.

    HEC-22: HGL_dn = max(HGL_dn_raw, Crown_dn); HGL_up = HGL_dn + Hf (no u/s floor).
    Legacy: HGL_dn = max(HGL_dn_raw, Crown_dn); HGL_up = max(HGL_dn + Hf, Crown_up).
    """
    hgl_dn = max(hgl_dn_raw, crown_dn)
    hgl_up_raw = hgl_dn + hf
    if method == "legacy":
        hgl_up = max(hgl_up_raw, crown_up)
    else:
        hgl_up = hgl_up_raw
    return hgl_dn, hgl_up
