import os
import ROOT
from .CorrectionsCore import *

period_names_Vpt = {
    "Run3_2022": "2022preEE",
    "Run3_2022EE": "2022postEE",
    "Run3_2023": "2023preBPix",
    "Run3_2023BPix": "2023postBPix",
}

scale_defs = {
    "LO": {
        "Central": ["""nom"""],
        "Up": [f"up{n}" for n in range(1, 8)],
        "Down": [f"down{n}" for n in range(1, 8)],
    },
    "NLO": {
        "Central": ["""nom"""],
        "Up": [f"up{n}" for n in range(1, 10)],
        "Down": [f"down{n}" for n in range(1, 10)],
    },
    "NNLO": {
        "Central": ["""nom"""],
        "Up": [f"up{n}" for n in range(1, 9)],
        "Down": [f"down{n}" for n in range(1, 9)],
    },
}
# https://cms-higgs-leprare.docs.cern.ch/htt-common/DY_reweight/
#


class VptCorrProducer:
    EWK_corr_jsonPath_recoil = "Corrections/data/hleprare/DYandRecoilCorrlib/DY_pTll_recoil_corrections_{0}_v5.json.gz"
    EWK_corr_jsonPath_weights = (
        "Corrections/data/hleprare/DYweightCorrlib/DY_pTll_weights_{0}_v5.json.gz"
    )
    EWK_corr_filePath = "Corrections/data/EWK_Corr_Vpt/{0}"
    initialized = False
    SFSources = ["Vpt", "ewcorr"]
    DY_w_SFSources = ["DYWeight"]

    def __init__(self, sampleType, period, order="NLO"):
        rootFile_EWKcorr_name = (
            "ZJetsCorr_collection_wek.root"
            if sampleType == "DY"
            else "WJetsCorr_collection_ewk.root"
        )
        rootFile_EWKcorr = os.path.join(
            os.environ["ANALYSIS_PATH"],
            VptCorrProducer.EWK_corr_filePath.format(rootFile_EWKcorr_name),
        )
        jsonFile_EWKcorr_recoil = os.path.join(
            os.environ["ANALYSIS_PATH"],
            VptCorrProducer.EWK_corr_jsonPath_recoil.format(period_names_Vpt[period]),
        )
        jsonFile_EWKcorr_weight = os.path.join(
            os.environ["ANALYSIS_PATH"],
            VptCorrProducer.EWK_corr_jsonPath_weights.format(period_names_Vpt[period]),
        )
        print(jsonFile_EWKcorr_weight)
        self.order = order
        hist_name = "eej_pTV_kappa_EW" if sampleType == "DY" else "evj_pTV_kappa_EW"
        hist_nominal_weight = "ewcorr"
        self.sampleType = sampleType
        if not VptCorrProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "Vpt.h")
            ROOT.gInterpreter.Declare(f"""#include "{header_path}" """)
            ROOT.gInterpreter.ProcessLine(
                f"""::correction::VptCorrProvider::Initialize("{rootFile_EWKcorr}", "{jsonFile_EWKcorr_weight}","{jsonFile_EWKcorr_recoil}", "{hist_name}", "{hist_nominal_weight}")"""
            )
            VptCorrProducer.initialized = True

    def getDYSF(self, df, isCentral, return_variations):
        sf_sources = VptCorrProducer.DY_w_SFSources
        sf_scales = [up, down] if return_variations else []

        SF_branches = []
        for source in sf_sources:
            for scale in [central] + sf_scales:
                for scale_def in scale_defs[self.order][scale]:
                    if not isCentral and scale != central:
                        continue
                    syst_name = (
                        source + scale_def
                    )  # if source != central else 'Central'
                    branch_SF_name = f"weight_DYw_{syst_name}"
                    branch_name_central = f"weight_DYw_{source}Central"
                    if scale == central:
                        branch_SF_name = branch_name_central
                    # branch_name_central = f"weight_DYw_{source}nom"
                    if self.sampleType == "DY":
                        df = df.Define(
                            f"{branch_SF_name}_double",
                            f"""::correction::VptCorrProvider::getGlobal().getDY_weight(LHE_Vpt, "{self.order}",
                                        ::correction::VptCorrProvider::UncSource::{source}, ::correction::VptCorrProvider::DYUncScale::{scale_def} )""",
                        )
                        # for scale_def in scale_defs[order][scale]:
                        # print(scale_def)
                        # df = df.Define(f"{branch_SF_name}_weightCorrLib_double", f"""weightCorrLib_map_{scale}.at("{scale_def}")""")
                    else:
                        df = df.Define(f"{branch_SF_name}_double", f"""1.f""")

                    # to fix because there are ultiple scales
                    if scale != central:
                        branch_name_final = branch_SF_name + "_rel"
                        # print(branch_name_final)
                        df = df.Define(
                            branch_name_final,
                            f"static_cast<float>({branch_SF_name}_double/{branch_name_central})",
                        )
                    else:
                        branch_name_final = (
                            f"weight_DYw_{source}Central"  # branch_name_central
                        )
                        # print(branch_name_final)
                        df = df.Define(
                            branch_name_final,
                            f"static_cast<float>({branch_SF_name}_double)",
                        )
                    SF_branches.append(branch_name_final)
        return df, SF_branches

    def getSF(self, df, isCentral, return_variations):
        sf_sources = VptCorrProducer.SFSources
        sf_scales = [up, down] if return_variations else []
        SF_branches = []
        for source in sf_sources:
            for scale in [central] + sf_scales:
                if source == central and scale != central:
                    continue
                if not isCentral and scale != central:
                    continue
                syst_name = source + scale  # if source != central else 'Central'
                branch_SF_name = f"weight_EWKCorr_{syst_name}"
                branch_name_central = f"weight_EWKCorr_{source}Central"
                if self.sampleType == "W" or self.sampleType == "DY":
                    df = df.Define(
                        f"{branch_SF_name}_double_sc",
                        f"""::correction::VptCorrProvider::getGlobal().getSF_fromRootFile(
                                        LHE_Vpt, ::correction::VptCorrProvider::UncSource::{source}, ::correction::UncScale::{scale} )""",
                    )
                    df = df.Define(
                        f"{branch_SF_name}_double", f"1+{branch_SF_name}_double_sc"
                    )
                else:
                    df = df.Define(f"{branch_SF_name}_double", f"1.f")
                if scale != central:
                    branch_name_final = branch_SF_name + "_rel"
                    df = df.Define(
                        branch_name_final,
                        f"static_cast<float>({branch_SF_name}_double/{branch_name_central})",
                    )
                else:
                    if source == central:
                        branch_name_final = branch_name_central
                    else:
                        branch_name_final = branch_SF_name
                    df = df.Define(
                        branch_name_final,
                        f"static_cast<float>({branch_SF_name}_double)",
                    )
                SF_branches.append(branch_name_final)
        return df, SF_branches
