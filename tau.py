import os
import ROOT
from .CorrectionsCore import *

# https://twiki.cern.ch/twiki/bin/viewauth/CMS/TauIDRecommendationForRun2
# https://indico.cern.ch/event/1062355/contributions/4466122/attachments/2287465/3888179/Update2016ULsf.pdf
# https://github.com/cms-tau-pog/TauTriggerSFs/tree/master/data
# https://github.com/cms-tau-pog/TauTriggerSFs/tree/run2_SFs

# Run3: https://twiki.cern.ch/twiki/bin/view/CMS/TauIDRecommendationForRun3

deepTauVersions = {"2p1": "2017", "2p5": "2018"}
period_in_tau_json = {
    "Run2_2016_HIPM": "2016_postVFP",
    "Run2_2016": "2016_preVFP",
    "Run2_2017": "2017",
    "Run2_2018": "2018",
    "Run3_2022": "2022_preEE",
    "Run3_2022EE": "2022_postEE",
    "Run3_2023": "2023_preBPix",
    "Run3_2023BPix": "2023_postBPix",
}

period_in_tau_file_name = {
    "Run2_2016_HIPM": period_names["Run2_2016_HIPM"],
    "Run2_2016": period_names["Run2_2016"],
    "Run2_2017": period_names["Run2_2017"],
    "Run2_2018": period_names["Run2_2018"],
    "Run3_2022": period_in_tau_json["Run3_2022"],
    "Run3_2022EE": period_in_tau_json["Run3_2022EE"],
    "Run3_2023": period_in_tau_json["Run3_2023"],
    "Run3_2023BPix": period_in_tau_json["Run3_2023BPix"],
}

period_in_taupog_folder = {
    "Run2_2016_HIPM": "Run2-2016preVFP-UL-NanoAODv9",
    "Run2_2016": "Run2-2016postVFP-UL-NanoAODv9",
    "Run2_2017": "Run2-2017-UL-NanoAODv9",
    "Run2_2018": "Run2-2018-UL-NanoAODv9",
    "Run3_2022": "Run3-22CDSep23-Summer22-NanoAODv12",
    "Run3_2022EE": "Run3-22EFGSep23-Summer22EE-NanoAODv12",
    "Run3_2023": "Run3-23CSep23-Summer23-NanoAODv12",
    "Run3_2023BPix": "Run3-23DSep23-Summer23BPix-NanoAODv12",
}

jsonfileversion = "2025-10-01"


class TauCorrProducer:
    jsonPath = (
        "/cvmfs/cms-griddata.cern.ch/cat/metadata/TAU/{}/"
        + jsonfileversion
        + "/tau_DeepTau2018v2p5_{}.json.gz"
    )

    initialized = False

    energyScaleSources_tau = ["TauES_DM0", "TauES_DM1", "TauES_3prong"]
    energyScaleSources_lep = [
        "EleFakingTauES_DM0",
        "EleFakingTauES_DM1",
        "MuFakingTauES",
    ]
    SFSources_tau = [
        "stat1_dm0",
        "stat2_dm0",
        "stat1_dm1",
        "stat2_dm1",
        "stat1_dm10",
        "stat2_dm10",
        "stat1_dm11",
        "stat2_dm11",
        "syst_alleras",
        "syst_year",
        "syst_year_dm0",
        "syst_year_dm1",
        "syst_year_dm10",
        "syst_year_dm11",
        "total",
        "stat_highpT_bin1",
        "stat_highpT_bin2",
        "syst_highpT",
        "syst_highpT_extrap",
        "syst_highpT_bin1",
        "syst_highpT_bin2",
    ]
    SFSources_genuineLep = [
        "genuineElectron_barrel",
        "genuineElectron_endcaps",
        "genuineMuon_etaLt0p4",
        "genuineMuon_eta0p4to0p8",
        "genuineMuon_eta0p8to1p2",
        "genuineMuon_eta1p2to1p7",
        "genuineMuon_etaGt1p7",
    ]

    def __init__(self, period, config):
        self.deepTauVersion = f"""DeepTau{deepTauVersions[config["deepTauVersion"]]}v{config["deepTauVersion"]}"""
        jsonFile = TauCorrProducer.jsonPath.format(
            period_in_taupog_folder[period], period_in_tau_file_name[period]
        )
        if not TauCorrProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "tau.h")
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')
            wp_map_cpp = createWPChannelMap(config["deepTauWPs"])
            tauType_map = createTauSFTypeMap(config["genuineTau_SFtype"])
            ROOT.gInterpreter.ProcessLine(
                f'::correction::TauCorrProvider::Initialize("{jsonFile}", "{self.deepTauVersion}", {wp_map_cpp}, {tauType_map} , "{period_in_tau_json[period]}")'
            )
            TauCorrProducer.initialized = True

    def getES(self, df, source_dict):
        for source in (
            [central]
            + TauCorrProducer.energyScaleSources_tau
            + TauCorrProducer.energyScaleSources_lep
        ):
            updateSourceDict(source_dict, source, "Tau")
            for scale in getScales(source):
                syst_name = getSystName(source, scale)
                df = df.Define(
                    f"Tau_p4_{syst_name}",
                    f"""::correction::TauCorrProvider::getGlobal().getES(
                               Tau_p4_{nano}, Tau_decayMode, Tau_genMatch,
                               ::correction::TauCorrProvider::UncSource::{source}, ::correction::UncScale::{scale})""",
                )
                df = df.Define(
                    f"Tau_p4_{syst_name}_delta", f"Tau_p4_{syst_name} - Tau_p4_{nano}"
                )

        return df, source_dict

    def getSF(self, df, lepton_legs, isCentral, return_variations):
        sf_sources = (
            TauCorrProducer.SFSources_tau + TauCorrProducer.SFSources_genuineLep
        )
        sf_scales = [up, down] if return_variations else []
        SF_branches = []
        for source in [central] + sf_sources:
            for scale in [central] + sf_scales:
                if source == central and scale != central:
                    continue
                if not isCentral and scale != central:
                    continue
                syst_name = source + scale  # if source != central else 'Central'
                for leg_idx, leg_name in enumerate(lepton_legs):
                    branch_Medium_name = (
                        f"weight_{leg_name}_TauID_SF_Medium_{syst_name}"
                    )
                    branch_Medium_central = (
                        f"""weight_{leg_name}_TauID_SF_Medium_{source}Central"""
                    )
                    df = df.Define(
                        f"{branch_Medium_name}_double",
                        f"""HttCandidate.leg_type[{leg_idx}] == Leg::tau ? ::correction::TauCorrProvider::getGlobal().getSF(
                               HttCandidate.leg_p4[{leg_idx}], Tau_decayMode.at(HttCandidate.leg_index[{leg_idx}]),
                               Tau_genMatch.at(HttCandidate.leg_index[{leg_idx}]),"Medium", HttCandidate.channel(),
                               ::correction::TauCorrProvider::UncSource::{source}, ::correction::UncScale::{scale}) : 1.;""",
                    )
                    if scale != central:
                        branch_name_Medium_final = branch_Medium_name + "_rel"
                        df = df.Define(
                            branch_name_Medium_final,
                            f"static_cast<float>({branch_Medium_name}_double/{branch_Medium_central})",
                        )
                    else:
                        if source == central:
                            branch_name_Medium_final = (
                                f"""weight_{leg_name}_TauID_SF_Medium_{central}"""
                            )
                        else:
                            branch_name_Medium_final = branch_Medium_name
                        df = df.Define(
                            branch_name_Medium_final,
                            f"static_cast<float>({branch_Medium_name}_double)",
                        )
                    SF_branches.append(branch_name_Medium_final)
        return df, SF_branches
