import os
import sys
import ROOT
from .CorrectionsCore import *

# lumi POG: https://twiki.cern.ch/twiki/bin/view/CMS/TWikiLUM
# PU scenarios https://twiki.cern.ch/twiki/bin/view/CMS/PileupScenariosRun2
# https://bamboo-hep.readthedocs.io/en/latest/recipes.html#pileup-reweighting
# https://twiki.cern.ch/twiki/bin/viewauth/CMS/PileupJSONFileforData
# https://twiki.cern.ch/twiki/bin/viewauth/CMS/PileupJSONFileforData#Centrally_produced_correctionlib
# https://bamboo-hep.readthedocs.io/en/latest/recipes.html#pileup-reweighting


class puWeightProducer:
    JsonPath = "/cvmfs/cms-griddata.cern.ch/cat/metadata/LUM/{folder}/latest/puWeights{suffix}.json.gz"
    initialized = False

    uncSource = ["pu"]
    golden_json_dict = {
        "2025_Winter25": "",
        "2025_Summer24": "",
        "2024_Summer24": "Collisions24_BCDEFGHI_goldenJSON",
        "2023_Summer23BPix": "Collisions2023_369803_370790_eraD_GoldenJson",
        "2023_Summer23": "Collisions2023_366403_369802_eraBC_GoldenJson",
        "2022_Summer22EE": "Collisions2022_359022_362760_eraEFG_GoldenJson",
        "2022_Summer22": "Collisions2022_355100_357900_eraBCD_GoldenJson",
        "2018_UL": "Collisions18_UltraLegacy_goldenJSON",
        "2017_UL": "Collisions17_UltraLegacy_goldenJSON",
        "2016preVFP_UL": "Collisions16_UltraLegacy_goldenJSON",
        "2016postVFP_UL": "Collisions16_UltraLegacy_goldenJSON",
    }

    def __init__(self, period):
        suffix = "_BCDEFGHI" if period == "2024_Summer24" else ""  # tmp patch
        jsonFile = puWeightProducer.JsonPath.format(
            folder=pog_folder_names["LUM"][period], suffix=suffix
        )
        if not puWeightProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "pu.h")
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')
            ROOT.gInterpreter.ProcessLine(
                f'::correction::puCorrProvider::Initialize("{jsonFile}", "{self.golden_json_dict[period]}")'
            )
            puWeightProducer.initialized = True

    def getWeight(
        self,
        df,
        shape_weights_dict=None,
        return_variations=True,
        return_list_of_branches=False,
        enabled=True,
    ):
        sf_sources = puWeightProducer.uncSource if return_variations else []
        branches = []
        for source in [central] + sf_sources:
            for scale in getScales(source):
                branch_name = f"weight_pu_{scale}"
                if enabled:
                    df = df.Define(
                        branch_name,
                        f"""::correction::puCorrProvider::getGlobal().getWeight(
                                    ::correction::UncScale::{scale}, Pileup_nTrueInt)""",
                    )
                    branches.append(branch_name)

                key = (source, scale)
                if shape_weights_dict:
                    if key not in shape_weights_dict:
                        shape_weights_dict[key] = []
                    shape_weights_dict[key].append(branch_name)

        if return_list_of_branches:
            return df, branches
        return df
