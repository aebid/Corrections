"""MuonScaReCorrProvider nominal correction and uncertainties against the MUO scale-and-resolution recipe.

The two uncertainties are taken around the nominal corrected muon:
- MuScale: the fully corrected pT shifted by the statistical uncertainty of the scale correction;
- MuRes: the applied smearing rescaled from k to k +- k_unc for the same random number, i.e.
  pt_nominal +- (k_unc / k) * (pt_nominal - pt_scaled).
Reference values are computed here with correctionlib. Needs the analysis environment (ROOT,
correctionlib, FLAF_PATH).
"""

import math
import os
import subprocess
import unittest

import correctionlib
import numpy as np
import ROOT

_HERE = os.path.dirname(os.path.abspath(__file__))
_DIR = os.path.join(_HERE, "data/MUO/MuonScaRe/Run3-22EFGSep23-Summer22EE-NanoAODv12")
_JSON = os.path.join(_DIR, "muon_scalesmearing.json.gz")
_JSON_VXBS = os.path.join(_DIR, "muon_scalesmearing_VXBS.json.gz")

# pt, eta, phi, charge, nTrackerLayers; the last muon is below the 20 GeV threshold of the corrections.
# NanoAOD stores pt, eta and phi as float32 and the provider takes them as float, so the reference is
# evaluated at the float32 values; none of them sits on a bin edge of the MUO maps.
_MUONS = [
    tuple(float(np.float32(x)) for x in mu[:3]) + mu[3:]
    for mu in [
        (45.0, 0.43, 0.31, 1, 12),
        (30.0, -1.57, 2.47, -1, 10),
        (80.0, 2.03, -1.19, 1, 14),
        (150.0, -0.71, 1.93, -1, 13),
        (15.0, 0.82, 0.05, -1, 12),
    ]
]
_EVENTS = [(1000 + 37 * i, 11 + i) for i in range(25)]  # (event, lumi)
_REL = 1e-6


def _setup_root():
    flags = subprocess.run(
        ["correction", "config", "--cflags", "--ldflags"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    lib_dir, lib_name = None, None
    for flag in flags:
        if flag.startswith("-I"):
            ROOT.gInterpreter.AddIncludePath(flag[2:])
        elif flag.startswith("-L"):
            lib_dir = flag[2:]
        elif flag.startswith("-l"):
            lib_name = flag[2:]
    ROOT.gSystem.Load(os.path.join(lib_dir, f"lib{lib_name}.so"))
    # The provider relies on the FLAF types and analysis::CrystalBall, declared before it (as
    # MuonEnergyScale_corr.py does).
    for header in ["AnalysisTools.h", "Utilities.h"]:
        ROOT.gInterpreter.Declare(
            f'#include "{os.environ["FLAF_PATH"]}/include/{header}"'
        )
    ROOT.gInterpreter.Declare(
        f'#include "{os.path.join(_HERE, "MuonScaReProvider.h")}"'
    )
    return ROOT.correction.MuonScaReCorrProvider(_JSON, _JSON_VXBS)


class TestMuonScaleResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = _setup_root()
        cls.cs = correctionlib.CorrectionSet.from_file(_JSON)
        cls.Source = ROOT.correction.MuonScaReCorrProvider.UncSource
        cls.Scale = ROOT.correction.UncScale

    # --- references (correctionlib) -------------------------------------------------------------
    def _pt_scaled(self, is_data, pt, eta, phi, charge):
        if pt < 20:
            return pt
        dtmc = "data" if is_data else "mc"
        a = self.cs[f"a_{dtmc}"].evaluate(eta, phi, "nom")
        m = self.cs[f"m_{dtmc}"].evaluate(eta, phi, "nom")
        return 1.0 / (m / pt + charge * a)

    def _scale_unc(self, pt, eta, phi, charge):
        stat_a = self.cs["a_mc"].evaluate(eta, phi, "stat")
        stat_m = self.cs["m_mc"].evaluate(eta, phi, "stat")
        rho = self.cs["m_mc"].evaluate(eta, phi, "rho_stat")
        return (
            pt
            * pt
            * math.sqrt(
                stat_m**2 / pt**2 + stat_a**2 + 2 * charge * rho * stat_m / pt * stat_a
            )
        )

    def _k(self, eta):
        k_data = self.cs["k_data"].evaluate(abs(eta), "nom")
        k_mc = self.cs["k_mc"].evaluate(abs(eta), "nom")
        k = math.sqrt(k_data**2 - k_mc**2) if k_mc < k_data else 0.0
        return k, self.cs["k_mc"].evaluate(abs(eta), "stat")

    # --- provider -------------------------------------------------------------------------------
    def _pt(self, mu, is_data, event, source, scale):
        pt, eta, phi, charge, n_layers = mu
        evt, lumi = event
        return self.provider.getES(
            pt,
            eta,
            phi,
            0.10566,
            charge,
            n_layers,
            is_data,
            evt,
            lumi,
            source,
            scale,
            False,
        ).pt()

    def _nominal(self, mu, is_data, event):
        return self._pt(mu, is_data, event, self.Source.Central, self.Scale.Central)

    # --- tests ----------------------------------------------------------------------------------
    def test_data_nominal_is_the_scale_correction_and_never_varied(self):
        for mu in _MUONS:
            pt, eta, phi, charge, _ = mu
            ref = self._pt_scaled(True, pt, eta, phi, charge)
            for source in (self.Source.Central, self.Source.MuScale, self.Source.MuRes):
                for scale in (self.Scale.Central, self.Scale.Up, self.Scale.Down):
                    self.assertAlmostEqual(
                        self._pt(mu, True, _EVENTS[0], source, scale),
                        ref,
                        delta=_REL * ref,
                    )

    def test_mc_nominal_is_scale_corrected_then_smeared(self):
        smeared = 0
        for mu in _MUONS:
            pt, eta, phi, charge, _ = mu
            scaled = self._pt_scaled(False, pt, eta, phi, charge)
            for event in _EVENTS:
                nominal = self._nominal(mu, False, event)
                if pt < 20:
                    self.assertAlmostEqual(
                        nominal, pt, delta=_REL * pt
                    )  # no correction below 20 GeV
                elif abs(nominal - scaled) > _REL * scaled:
                    smeared += 1
        self.assertGreater(
            smeared, 0.8 * 4 * len(_EVENTS), "the MC smearing is not applied"
        )

    def test_scale_variation_shifts_the_corrected_pt(self):
        for mu in _MUONS:
            pt, eta, phi, charge, _ = mu
            for event in _EVENTS[:5]:
                nominal = self._nominal(mu, False, event)
                unc = self._scale_unc(nominal, eta, phi, charge)
                up = self._pt(mu, False, event, self.Source.MuScale, self.Scale.Up)
                down = self._pt(mu, False, event, self.Source.MuScale, self.Scale.Down)
                self.assertAlmostEqual(up, nominal + unc, delta=_REL * nominal)
                self.assertAlmostEqual(down, nominal - unc, delta=_REL * nominal)
                self.assertGreater(up, nominal)
                self.assertLess(down, nominal)

    def test_resolution_variation_rescales_the_applied_smearing(self):
        checked = 0
        for mu in _MUONS:
            pt, eta, phi, charge, _ = mu
            scaled = self._pt_scaled(False, pt, eta, phi, charge)
            k, k_unc = self._k(eta)
            for event in _EVENTS:
                nominal = self._nominal(mu, False, event)
                up = self._pt(mu, False, event, self.Source.MuRes, self.Scale.Up)
                down = self._pt(mu, False, event, self.Source.MuRes, self.Scale.Down)
                smearing = nominal - scaled
                if k == 0 or abs(smearing) <= _REL * scaled:
                    # no smearing applied (pT < 20 GeV, k = 0, or the random number gave none): nothing to vary
                    self.assertAlmostEqual(up, nominal, delta=_REL * nominal)
                    self.assertAlmostEqual(down, nominal, delta=_REL * nominal)
                    continue
                expected = k_unc / k * smearing
                self.assertAlmostEqual(up - nominal, expected, delta=_REL * nominal)
                self.assertAlmostEqual(down - nominal, -expected, delta=_REL * nominal)
                checked += 1
        self.assertGreater(checked, 0.8 * 4 * len(_EVENTS))

    def test_variations_keep_the_nominal_corrections(self):
        # Regression: the variations used to be computed from the uncorrected pT and without the
        # smearing, so Up and Down were both (nearly) the unsmeared pT and moved yields the same way.
        same_side = 0
        for mu in _MUONS[:4]:
            for event in _EVENTS:
                nominal = self._nominal(mu, False, event)
                for source in (self.Source.MuScale, self.Source.MuRes):
                    up = self._pt(mu, False, event, source, self.Scale.Up) - nominal
                    down = self._pt(mu, False, event, source, self.Scale.Down) - nominal
                    if up * down > 0:
                        same_side += 1
                    self.assertAlmostEqual(up, -down, delta=1e-4 * nominal)
        self.assertEqual(same_side, 0)


if __name__ == "__main__":
    unittest.main()
