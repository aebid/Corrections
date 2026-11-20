"""MET of the shifted trees.

In the tree of a systematic source, the objects the source shifts take their shifted p4 and every
other object keeps its Central correction, so the MET of that tree is the Central MET minus the
shifts of the source's objects relative to Central. Needs the analysis environment (ROOT,
correctionlib, FLAF_PATH).
"""

import os
import subprocess
import sys
import unittest

# Import the package from the directory above, as the analyses do: run from here, the script's own
# directory would make `Corrections` resolve to Corrections.py. The path is restored afterwards so
# that test modules loaded after this one in the same run still import.
repo = os.path.dirname(os.path.abspath(__file__))
_sys_path = list(sys.path)
sys.path = [p for p in sys.path if os.path.abspath(p or ".") != repo]
sys.path.insert(0, os.path.dirname(repo))

import ROOT

from Corrections.CorrectionsCore import central, getScales, getSystName, nano
from Corrections.met import METCorrProducer

sys.path = _sys_path

MET_TYPE = "PuppiMET"
LV = "ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double>>"
N_EVENTS = 20

# object -> (base pt, number of objects); every p4 depends on the event number, so each event
# tests different values.
OBJECTS = {"Electron": (35.0, 2), "Muon": (28.0, 1), "Tau": (45.0, 2), "Jet": (60.0, 3)}
SOURCES = {
    "EleES": ["Electron"],
    "TauES_DM0": ["Tau"],
    "MuScale": ["Muon"],
    "MuRes": ["Muon"],
    "JES_Total": ["Jet", "FatJet"],
    "FatJetOnly": ["FatJet"],
}
CENTRAL_SF = {"Electron": 1.02, "Muon": 0.995, "Tau": 0.97, "Jet": 1.08}
SHIFT_SF = {"Up": 1.03, "Down": 0.98}


def _setup_root():
    for flag in subprocess.run(
        ["correction", "config", "--cflags"], capture_output=True, text=True, check=True
    ).stdout.split():
        if flag.startswith("-I"):
            ROOT.gInterpreter.AddIncludePath(flag[2:])
    # met.h relies on the FLAF types and printing helpers declared before it.
    for header in ["AnalysisTools.h", "TextIO.h"]:
        ROOT.gInterpreter.Declare(
            f'#include "{os.environ["FLAF_PATH"]}/include/{header}"'
        )


HELPERS = """
#include <ROOT/RVec.hxx>
#include <Math/Vector4D.h>
template <typename V> ROOT::VecOps::RVec<double> v_ops_px(const ROOT::VecOps::RVec<V>& v)
{ ROOT::VecOps::RVec<double> r(v.size()); for (size_t i = 0; i < v.size(); ++i) r[i] = v[i].Px(); return r; }
template <typename V> ROOT::VecOps::RVec<double> v_ops_py(const ROOT::VecOps::RVec<V>& v)
{ ROOT::VecOps::RVec<double> r(v.size()); for (size_t i = 0; i < v.size(); ++i) r[i] = v[i].Py(); return r; }
"""


def _rvec_expr(obj, factor_expr):
    base_pt, n = OBJECTS[obj]
    items = ", ".join(
        f"{LV}(({base_pt} + 3.1 * {i} + 0.7 * rdfentry_) * ({factor_expr}),"
        f" {0.3 * i - 0.4}, {1.1 * i - 2.0} + 0.05 * rdfentry_, {0.1 * i})"
        for i in range(n)
    )
    return f"ROOT::VecOps::RVec<{LV}>{{ {items} }}"


def _build_frame():
    df = ROOT.RDataFrame(N_EVENTS)
    df = df.Define(
        f"{MET_TYPE}_p4_{nano}",
        f"{LV}(50 + 2.0 * rdfentry_, 0., 0.3 * rdfentry_ - 3.0, 0.)",
    )
    source_dict = {central: list(OBJECTS) + ["FatJet"]}
    for obj in OBJECTS:
        df = df.Define(f"{obj}_p4_{nano}", _rvec_expr(obj, "1.0"))
        df = df.Define(f"{obj}_p4_{central}", _rvec_expr(obj, f"{CENTRAL_SF[obj]}"))
        df = df.Define(
            f"{obj}_p4_{central}_delta", f"{obj}_p4_{central} - {obj}_p4_{nano}"
        )
    for source, objs in SOURCES.items():
        source_dict[source] = list(objs)
        for obj in objs:
            if obj not in OBJECTS:
                continue
            for scale in getScales(source):
                syst = getSystName(source, scale)
                factor = f"{CENTRAL_SF[obj]} * {SHIFT_SF[scale]}"
                df = df.Define(f"{obj}_p4_{syst}", _rvec_expr(obj, factor))
                df = df.Define(
                    f"{obj}_p4_{syst}_delta", f"{obj}_p4_{syst} - {obj}_p4_{nano}"
                )
    return df, source_dict


class TestMetShiftPropagation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_root()
        ROOT.gInterpreter.Declare(HELPERS)
        df, source_dict = _build_frame()
        cls.df, cls.source_dict = METCorrProducer().getMET(df, source_dict, MET_TYPE)
        cls.columns = {str(c) for c in cls.df.GetColumnNames()}

    def _check(self, syst, objs):
        # Reference: Central MET minus the shift of each of the source's objects relative to
        # Central, in px and py.
        terms = " + ".join(
            f"ROOT::VecOps::Sum(v_ops_px({o}_p4_{syst}) - v_ops_px({o}_p4_{central}))"
            for o in objs
        )
        terms_y = terms.replace("v_ops_px", "v_ops_py")
        df = self.df.Define(
            "dx",
            f"{MET_TYPE}_p4_{syst}.Px() - ({MET_TYPE}_p4_{central}.Px() - ({terms}))",
        ).Define(
            "dy",
            f"{MET_TYPE}_p4_{syst}.Py() - ({MET_TYPE}_p4_{central}.Py() - ({terms_y}))",
        )
        worst = max(
            max(abs(x) for x in df.Take["double"]("dx").GetValue()),
            max(abs(y) for y in df.Take["double"]("dy").GetValue()),
        )
        self.assertLess(
            worst, 1e-9, f"{syst}: MET differs from the reference by {worst}"
        )

    def test_central_carries_every_central_correction(self):
        self._check_central(self.df, list(OBJECTS))

    def _check_central(self, df, objs):
        terms = " + ".join(
            f"ROOT::VecOps::Sum(v_ops_px({o}_p4_{central}) - v_ops_px({o}_p4_{nano}))"
            for o in objs
        )
        terms_y = terms.replace("v_ops_px", "v_ops_py")
        df = df.Define(
            "dx",
            f"{MET_TYPE}_p4_{central}.Px() - ({MET_TYPE}_p4_{nano}.Px() - ({terms}))",
        ).Define(
            "dy",
            f"{MET_TYPE}_p4_{central}.Py() - ({MET_TYPE}_p4_{nano}.Py() - ({terms_y}))",
        )
        worst = max(
            max(abs(x) for x in df.Take["double"]("dx").GetValue()),
            max(abs(y) for y in df.Take["double"]("dy").GetValue()),
        )
        self.assertLess(worst, 1e-9)

    def test_shifted_met_is_central_met_plus_the_source_shift(self):
        for source, objs in SOURCES.items():
            met_objs = [o for o in objs if o in OBJECTS]
            if not met_objs:
                continue
            for scale in getScales(source):
                self._check(getSystName(source, scale), met_objs)

    def test_source_without_met_objects_defines_no_met(self):
        for scale in getScales("FatJetOnly"):
            syst = getSystName("FatJetOnly", scale)
            self.assertNotIn(f"{MET_TYPE}_p4_{syst}", self.columns)
        self.assertNotIn("MET", self.source_dict["FatJetOnly"])
        self.assertIn("MET", self.source_dict["EleES"])

    def test_data_has_central_only(self):
        df = ROOT.RDataFrame(1).Define(
            f"{MET_TYPE}_p4_{nano}", f"{LV}(40., 0., 1., 0.)"
        )
        df = df.Define(f"Jet_p4_{nano}", _rvec_expr("Jet", "1.0"))
        df = df.Define(f"Jet_p4_{central}", _rvec_expr("Jet", "1.1"))
        df = df.Define(f"Jet_p4_{central}_delta", f"Jet_p4_{central} - Jet_p4_{nano}")
        df, source_dict = METCorrProducer().getMET(df, {central: ["Jet"]}, MET_TYPE)
        self.assertEqual(source_dict, {central: ["Jet", "MET"]})
        self._check_central(df, ["Jet"])


if __name__ == "__main__":
    unittest.main()
