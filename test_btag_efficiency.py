"""The b-tag efficiency maps of bTagCorrProvider (loadEfficiency) are freed with the provider.

The constructor reads one map per flavour and working point and divides it by the flavour's
denominator, read the same way; a denominator that nobody deleted stayed allocated until the
process ended. The live histograms are counted with ROOT's object table, which counts only the
objects made after it is switched on, so the provider is built in a child process that switches
it on first. The efficiency file is the 2018_UL one of this repository. Needs the analysis
environment (ROOT, correctionlib, FLAF_PATH) and /cvmfs.
"""

import json
import os
import subprocess
import sys
import unittest

repo = os.path.dirname(os.path.abspath(__file__))

# The package is imported from the directory above, as the analyses do; ANALYSIS_PATH points
# there too, so that the efficiency file is the one of this repository.
CHILD = """
import gc, json, os, sys
sys.path = [p for p in sys.path if os.path.abspath(p or ".") != sys.argv[1]]
sys.path.insert(0, os.path.dirname(sys.argv[1]))
os.environ["ANALYSIS_PATH"] = os.path.dirname(sys.argv[1])
import ROOT
ROOT.TObject.SetObjectStat(True)
from FLAF.Common.Utilities import WorkingPointsbTag, generate_enum_class
from Corrections.CorrectionsCore import declareHeader
from Corrections.btag import bTagCorrProducer

def live():
    gc.collect()
    ROOT.gObjectTable.UpdateInstCount()
    return ROOT.TH2D.Class().GetInstanceCount()

for header in ["AnalysisTools.h", "RootExt.h"]:
    declareHeader(os.path.join(os.environ["FLAF_PATH"], "include", header))
ROOT.gInterpreter.Declare(generate_enum_class(WorkingPointsbTag))
# RDataFrame loaded first, as in test_jer_gen_match.py: without it cling cannot construct the
# provider from the declared headers.
ROOT.RDataFrame(1)
counts = {"start": live()}
producer = bTagCorrProducer(
    campaign="2018_UL", jetCollection="Jet", loadEfficiency=True, tagger="deepJet"
)
counts["constructed"] = live()
del producer
counts["deleted"] = live()
print(json.dumps(counts))
"""


class TestBTagEfficiency(unittest.TestCase):
    def test_efficiency_maps_are_freed(self):
        result = subprocess.run(
            [sys.executable, "-c", CHILD, repo], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        counts = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(counts["start"], 0)
        # Three flavours times three working points.
        self.assertEqual(counts["constructed"], 9, "a denominator was left allocated")
        self.assertEqual(counts["deleted"], 0, "a histogram outlived the provider")


if __name__ == "__main__":
    unittest.main()
