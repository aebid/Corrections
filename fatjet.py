import os
import ROOT
from .CorrectionsCore import *


class FatJetCorrProducer:
    initialized = False

    period = None

    base_file_path = os.path.join(
        os.environ["ANALYSIS_PATH"], "Corrections/data/AK8Jet/bbWW"
    )
    fatjet_corr_dict = {
        "particleNetWithMass_HbbvsQCD": {
            "file_name": {
                "2022_Summer22": os.path.join(
                    base_file_path,
                    "ak8_sf_corrections_bbww_combined_2022_preEE.json.gz",
                ),
                "2022_Summer22EE": os.path.join(
                    base_file_path,
                    "ak8_sf_corrections_bbww_combined_2022_postEE.json.gz",
                ),
                "2023_Summer23": os.path.join(
                    base_file_path,
                    "ak8_sf_corrections_bbww_combined_2023_preBPix.json.gz",
                ),
                "2023_Summer23BPix": os.path.join(
                    base_file_path,
                    "ak8_sf_corrections_bbww_combined_2023_postBPix.json.gz",
                ),
            },
            "keys_bb": {
                "2022_Summer22": "HHbbww_2022_preEE_SF_bb",
                "2022_Summer22EE": "HHbbww_2022_postEE_SF_bb",
                "2023_Summer23": "HHbbww_2023_preBPix_SF_bb",
                "2023_Summer23BPix": "HHbbww_2023_postBPix_SF_bb",
            },
            "keys_cc": {
                "2022_Summer22": "HHbbww_2022_preEE_SF_cc",
                "2022_Summer22EE": "HHbbww_2022_postEE_SF_cc",
                "2023_Summer23": "HHbbww_2023_preBPix_SF_cc",
                "2023_Summer23BPix": "HHbbww_2023_postBPix_SF_cc",
            },
        }
    }

    fatjet_Sources = ["Hbb", "Hcc", "tau21"]

    def __init__(self, period, ana, tagger, fatjetName, isData=False):
        # ana input for future, if other analyses will use separate corrections
        self.isData = isData
        self.fatjetName = fatjetName

        this_dict = self.fatjet_corr_dict[tagger]
        file_nameID = this_dict["file_name"][period]
        bb_key = this_dict["keys_bb"][period]
        cc_key = this_dict["keys_cc"][period]

        if not FatJetCorrProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "fatjet.h")
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')
            ROOT.gInterpreter.ProcessLine(
                f'::correction::FatJetCorrProvider::Initialize("{file_nameID}","{bb_key}","{cc_key}")'
            )
            FatJetCorrProducer.initialized = True

        self.period = period
        self.columns = {}

    def getSF(self, df, isCentral, return_variations):
        sf_sources = [central]
        if isCentral and return_variations:
            sf_sources += FatJetCorrProducer.fatjet_Sources
        SF_branches = []
        syst_name_central = getSystName(central, central)
        branch_central = f"""{self.fatjetName}_weight_FatJetSF_{syst_name_central}"""
        for source in sf_sources:
            for scale in getScales(source):
                syst_name = getSystName(source, scale)
                branch_name = f"{self.fatjetName}_weight_FatJetSF_{syst_name}"

                df = df.Define(
                    f"{branch_name}",
                    f"""::correction::FatJetCorrProvider::getGlobal().get_SF({self.fatjetName}_isValid,
                            {self.fatjetName}_pt, {self.fatjetName}_hadronFlavour,
                            ::correction::FatJetCorrProvider::UncSource::{source},
                            ::correction::UncScale::{scale})""",
                )

                if scale != central:
                    branch_name_final = branch_name + "_rel"
                    df = df.Define(
                        branch_name_final,
                        f"({branch_name}/{branch_central})",
                    )
                else:
                    branch_name_final = branch_name

                SF_branches.append(branch_name_final)
        return df, SF_branches
