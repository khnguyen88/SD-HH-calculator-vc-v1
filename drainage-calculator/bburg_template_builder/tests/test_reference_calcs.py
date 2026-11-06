import pytest
from bburg_template_builder.reference_calcs import (
    interpolate_pl, manning_sf_full, velocity_head, hgl_walk_step
)
from bburg_template_builder.seed_data import NOAA14_SEED


class TestInterpolatePL:
    def test_endpoint_5_min_montgomery_10yr(self):
        depths = {d: NOAA14_SEED["Montgomery"]["10yr"][d] for d in (5, 10, 15, 30, 60)}
        # At Tc=5 min, i = 60 * 6.64 / 5 = 79.68 in/hr
        assert interpolate_pl(5.0, depths) == pytest.approx(79.68, rel=1e-3)

    def test_endpoint_60_min_montgomery_10yr(self):
        depths = {d: NOAA14_SEED["Montgomery"]["10yr"][d] for d in (5, 10, 15, 30, 60)}
        # At Tc=60 min, i = 60 * 2.11 / 60 = 2.11 in/hr
        assert interpolate_pl(60.0, depths) == pytest.approx(2.11, rel=1e-3)

    def test_mid_10_min_montgomery_10yr(self):
        depths = {d: NOAA14_SEED["Montgomery"]["10yr"][d] for d in (5, 10, 15, 30, 60)}
        # At Tc=10 min exactly, intensity = 60*5.31/10 = 31.86 in/hr (uses 5-10 bracket, t=10)
        assert interpolate_pl(10.0, depths) == pytest.approx(31.86, rel=1e-3)

    def test_mid_7_min_montgomery_10yr(self):
        # Power-law between 5min (6.64 in) and 10min (5.31 in):
        # b = ln(5.31/6.64)/ln(10/5) = -0.322471
        # a = 6.64 / 5^b = 6.64 * 5^0.322471 = 11.157474
        # At Tc=7: depth = 11.157474 * 7^(-0.322471) = 5.957252 in
        # i = 60 * 5.957252 / 7 = 51.0622 in/hr
        depths = {d: NOAA14_SEED["Montgomery"]["10yr"][d] for d in (5, 10, 15, 30, 60)}
        assert interpolate_pl(7.0, depths) == pytest.approx(51.0622, rel=1e-3)


class TestManningSfFull:
    def test_24in_rcp_9p5_cfs(self):
        # D=24in -> d_ft=2, A=pi*1 = 3.1416, R=0.5
        # conveyance = 1.486 * 3.1416 * 0.5^(2/3) = 1.486 * 3.1416 * 0.6300 = 2.942
        # Sf = (9.5*0.013/2.942)^2 = (0.04197)^2 = 0.00176
        assert manning_sf_full(9.5, 0.013, 24) == pytest.approx(0.00176, rel=1e-2)

    def test_zero_q_gives_zero_sf(self):
        assert manning_sf_full(0.0, 0.013, 24) == 0.0


class TestVelocityHead:
    def test_known_value(self):
        # V=3 fps -> Vh = 9/64.4 = 0.1398
        assert velocity_head(3.0) == pytest.approx(0.1398, rel=1e-3)


class TestHglWalkStep:
    def test_hec22_pressurized(self):
        # HGL_dn_raw=97, Crown_dn=96, Crown_up=96.5, Hf=0.142
        # HGL_dn = max(97, 96) = 97; HGL_up = 97 + 0.142 = 97.142 (no u/s floor)
        hgl_dn, hgl_up = hgl_walk_step(97.0, 96.0, 96.5, 0.142, "hec22")
        assert hgl_dn == pytest.approx(97.0, abs=1e-4)
        assert hgl_up == pytest.approx(97.142, abs=1e-4)

    def test_hec22_gravity_ds_crown_floor(self):
        # HGL_dn_raw=93 (below crown 96), Hf=0.05
        # HGL_dn = max(93, 96) = 96; HGL_up = 96 + 0.05 = 96.05 (no u/s floor)
        hgl_dn, hgl_up = hgl_walk_step(93.0, 96.0, 97.0, 0.05, "hec22")
        assert hgl_dn == pytest.approx(96.0, abs=1e-4)
        assert hgl_up == pytest.approx(96.05, abs=1e-4)

    def test_legacy_gravity_both_ends_crown_floor(self):
        # Same inputs as above, but Legacy pins HGL_up at Crown_up=97.0 (since 96.05 < 97.0)
        hgl_dn, hgl_up = hgl_walk_step(93.0, 96.0, 97.0, 0.05, "legacy")
        assert hgl_dn == pytest.approx(96.0, abs=1e-4)
        assert hgl_up == pytest.approx(97.0, abs=1e-4)

    def test_methods_agree_when_pressurized(self):
        a = hgl_walk_step(100.0, 96.0, 96.5, 0.2, "hec22")
        b = hgl_walk_step(100.0, 96.0, 96.5, 0.2, "legacy")
        assert a == b
