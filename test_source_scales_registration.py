"""The indexed shape-weight scales (PDF members, QCD-scale points) are known at every stage.

A Corrections instance registers only the shape weights of its own stage, so a histogram stage
that does not list `pdf` / `qcd_scale` (or builds no Corrections at all) saw Up/Down for them.
`Corrections.registerConfiguredSourceScales(global_params)` registers every configured one.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Corrections import CorrectionsCore  # noqa: E402
from Corrections.Corrections import Corrections  # noqa: E402

GLOBAL_PARAMS = {
    "corrections": {
        "pu": {"stages": ["AnaTuple", "AnaTupleMerge"]},
        "pdf": {
            "stages": ["AnaTuple", "AnaTupleMerge"],
            "branch": "LHEPdfWeight",
            "n_members": 103,
        },
        "qcd_scale": {
            "stages": ["AnaTuple", "AnaTupleMerge"],
            "branch": "LHEScaleWeight",
        },
        "JEC": {"stages": ["AnaTuple"]},
    }
}


class TestConfiguredSourceScales(unittest.TestCase):
    def setUp(self):
        self._saved = dict(CorrectionsCore._source_scales)
        CorrectionsCore._source_scales.clear()

    def tearDown(self):
        CorrectionsCore._source_scales.clear()
        CorrectionsCore._source_scales.update(self._saved)

    def test_unregistered_indexed_source_falls_back_to_up_down(self):
        self.assertEqual(CorrectionsCore.getScales("pdf"), ["Up", "Down"])

    def test_pdf_members_and_qcd_scale_points_are_registered(self):
        Corrections.registerConfiguredSourceScales(GLOBAL_PARAMS)
        pdf = CorrectionsCore.getScales("pdf")
        self.assertEqual(pdf, [str(k) for k in range(103)])
        qcd = CorrectionsCore.getScales("qcd_scale")
        self.assertEqual(len(qcd), 8)
        self.assertNotIn("_muR1_muF1", qcd)
        self.assertIn("_muR2_muF2", qcd)
        self.assertEqual(CorrectionsCore.getSystName("pdf", "17"), "pdf17")

    def test_n_members_comes_from_the_config(self):
        params = {"corrections": {"pdf": {"n_members": 101}}}
        Corrections.registerConfiguredSourceScales(params)
        self.assertEqual(len(CorrectionsCore.getScales("pdf")), 101)

    def test_up_down_sources_and_other_corrections_are_untouched(self):
        Corrections.registerConfiguredSourceScales(GLOBAL_PARAMS)
        self.assertEqual(CorrectionsCore.getScales("pu"), ["Up", "Down"])
        self.assertEqual(CorrectionsCore.getScales("JEC"), ["Up", "Down"])

    def test_no_corrections_block(self):
        Corrections.registerConfiguredSourceScales({})
        self.assertEqual(CorrectionsCore.getScales("pdf"), ["Up", "Down"])


if __name__ == "__main__":
    unittest.main()
