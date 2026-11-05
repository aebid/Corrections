"""The BTV json files are read from a dated version, never from "latest".

BTV replaces "latest" in place (e.g. 2026-11-05: the 2023BPix light-jet shape SFs below 30 GeV),
which changes the SFs of a running production silently. As for JERC, each entry of
pog_folder_names["BTV"] is "<campaign folder>/<YYYY-MM-DD>".

Reads the sources only; the existence check runs where /cvmfs is mounted.
"""

import ast
import os
import re
import unittest

repo = os.path.dirname(os.path.abspath(__file__))
BTV_ROOT = "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV"


def module_dict(name):
    """The literal dict assigned to `name` in CorrectionsCore.py."""
    with open(os.path.join(repo, "CorrectionsCore.py")) as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise KeyError(name)


class TestBtvJsonPinned(unittest.TestCase):
    def setUp(self):
        self.btv = module_dict("pog_folder_names")["BTV"]
        self.campaigns = module_dict("campaign_names")

    def test_every_btv_folder_is_dated(self):
        for campaign, folder in self.btv.items():
            if not folder:  # campaigns without a BTV set
                continue
            with self.subTest(campaign=campaign):
                self.assertRegex(folder, r"^[^/]+/\d{4}-\d{2}-\d{2}$")

    def test_btag_py_does_not_read_latest(self):
        with open(os.path.join(repo, "btag.py")) as f:
            code = [l for l in f if not l.strip().startswith("#")]
        self.assertFalse([l for l in code if re.search(r"/latest/", l)])

    @unittest.skipUnless(os.path.isdir(BTV_ROOT), "needs /cvmfs/cms-griddata.cern.ch")
    def test_pinned_files_exist_for_every_era(self):
        for era, campaign in self.campaigns.items():
            with self.subTest(era=era):
                path = os.path.join(BTV_ROOT, self.btv[campaign], "btagging.json.gz")
                self.assertTrue(os.path.isfile(path), path)


if __name__ == "__main__":
    unittest.main()
