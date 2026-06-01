import os
import ROOT
from .CorrectionsCore import *


class DYbbtautauCorrProducer:
    # JsonPath = "/afs/cern.ch/work/m/mrieger/public/hbt/external_files/custom_dy_files/hbt_corrections.json.gz"
    JsonPath = "Corrections/data/DY_corr_hbt/hbt_corrections_v2.json.gz"
    initialized = False

    era_map = {
        "Run3_2022": "2022preEE",
        "Run3_2022EE": "2022postEE",
        "Run3_2023": "2023preBPix",
        "Run3_2023BPix": "2023postBPix",
        "Run3_2024": "2024",
    }

    default_variations = [
        # "stat_up",
        # "stat_down",
        # "syst_up",
        # "syst_down",
        "stat_btag0_up",
        "stat_btag0_down",
        "stat_btag1_up",
        "stat_btag1_down",
        "stat_btag2_up",
        "stat_btag2_down",
        "syst_gauss_up",
        "syst_gauss_down",
        "syst_linear_up",
        "syst_linear_down",
    ]

    def __init__(
        self,
        sampleType,
        era,
        *,
        njets_branch="nJet",
        ntags_branch="nBJets",
        pt_ll_gen="pt_ll_gen",
        valid="valid",
        variations=None,
    ):
        self.era = era
        self.valid = valid
        if sampleType == "DY":
            self.isDY = True
        else:
            self.isDY = False

        if self.era not in self.era_map:
            raise RuntimeError(
                f"DYbbtautauCorrProducer: unsupported era '{self.era}'. "
                f"Supported eras: {list(self.era_map.keys())}"
            )

        analysis_path = os.environ.get("ANALYSIS_PATH")
        if analysis_path is None:
            raise RuntimeError(
                "DYbbtautauCorrProducer: ANALYSIS_PATH is not set. "
                "Cannot resolve DY correction JSON path."
            )

        if os.path.isabs(self.JsonPath):
            self.json_path = self.JsonPath
        else:
            self.json_path = os.path.join(analysis_path, self.JsonPath)

        if not os.path.exists(self.json_path):
            raise FileNotFoundError(
                f"DYbbtautauCorrProducer: DY correction JSON not found: {self.json_path}"
            )

        self.njets_branch = njets_branch
        self.ntags_branch = ntags_branch
        self.pt_ll_gen = pt_ll_gen
        self.variations = list(
            self.default_variations if variations is None else variations
        )

        if not DYbbtautauCorrProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "DY_hhbbtautau.h")
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')
            ROOT.gInterpreter.ProcessLine(
                f'::correction::DYbbtautauCorrProvider::Initialize("{self.json_path}")'
            )
            DYbbtautauCorrProducer.initialized = True

    def _valid_expr(self):
        if isinstance(self.valid, bool):
            return "true" if self.valid else "false"
        return f"static_cast<bool>({self.valid})"

    def getWeight(
        self,
        df,
        return_variations=True,
        return_list_of_branches=False,
        enabled=True,
    ):
        if not enabled:
            if return_list_of_branches:
                return df, []
            return df

        systs = ["nominal"]
        if return_variations:
            systs += self.variations

        branches = []
        valid_expr = self._valid_expr()

        for syst in systs:
            branch_name = (
                "weight_dy_central" if syst == "nominal" else f"weight_dy_{syst}"
            )
            if self.isDY:
                df = df.Define(
                    branch_name,
                    f"""static_cast<float>(
                        ::correction::DYbbtautauCorrProvider::getGlobal().getWeight(
                            \"{self.era_map[self.era]}\",
                            static_cast<int>({self.njets_branch}),
                            static_cast<int>({self.ntags_branch}),
                            static_cast<float>({self.pt_ll_gen}),
                            \"{syst}\",
                            {valid_expr}
                        )
                    )""",
                )
            else:
                df = df.Define(branch_name, f"""1.f""")

            branches.append(branch_name)

        if return_list_of_branches:
            return df, branches
        return df
