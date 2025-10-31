import os
import ROOT
from .CorrectionsCore import *
from FLAF.Common.Utilities import *
import yaml
import re

# Tau JSON POG integration for tau legs in eTau, muTau, diTau:
# # https://gitlab.cern.ch/cms-nanoAOD/jsonpog-integration/-/tree/master/POG/TAU?ref_type=heads

# singleEle + e/mu legs for xTriggers eTau, muTau:
# https://twiki.cern.ch/twiki/bin/view/CMS/EgHLTScaleFactorMeasurements

# singleMu : files taken from https://gitlab.cern.ch/cms-muonPOG/muonefficiencies/-/tree/master/Run2/UL and saved locally

# singleTau: https://twiki.cern.ch/twiki/bin/viewauth/CMS/TauTrigger#Run_II_Trigger_Scale_Factors
# singleTau: Legacy bc there are no UL as mentioned herehttps://cms-pub-talk.web.cern.ch/t/tau-pog-review/8404/4
# singleTau: 2016 - (HLT_VLooseIsoPFTau120_Trk50_eta2p1_v OR HLT_VLooseIsoPFTau140_Trk50_eta2p1_v) - 0.88 +/- 0.08
# singleTau: 2017 - HLT_MediumChargedIsoPFTau180HighPtRelaxedIso_Trk50_eta2p1_v - 1.08 +/- 0.10
# singleTau: 2018 - (HLT_MediumChargedIsoPFTau180HighPtRelaxedIso_Trk50_eta2p1_v) - 	0.87 +/- 0.11

# singleTau;diTau run3: https://gitlab.cern.ch/cms-tau-pog/jsonpog-integration/-/tree/TauPOG_v2_deepTauV2p5/POG/TAU?ref_type=heads
# crossTrigger run3 : https://gitlab.cern.ch/cms-higgs-leprare/hleprare/-/tree/master/TriggerScaleFactors?ref_type=heads
# singleEle : /cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/EGM/{period}/electronHlt.json.gz
# singleMu : /cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/{period}/muon_Z.json.gz
# missing efficiencies for singleMu --> run2 eff are https://gitlab.cern.ch/cms-muonPOG/muonefficiencies/-/tree/master (but run3 is missing also on this folder)


# SFSources_bbtautau = { 'ditau': [ "ditau_DM0","ditau_DM1", "ditau_3Prong"], 'singleMu':['singleMu'],'singleTau':['singleTau'], 'singleEle':['singleEle'],'etau':['etau_ele',"etau_DM0","etau_DM1", "etau_3Prong",],'mutau':['mutau_mu',"mutau_DM0","mutau_DM1", "mutau_3Prong"]}

taujsonfileversion = "2025-10-01"


class TrigCorrProducer:
    eTRG_jsonPath = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/EGM/{}/electronHlt.json.gz"
    MuTRG_jsonPath = os.path.join(
        os.environ["ANALYSIS_PATH"], "Corrections/data/TRG/{}/MuHlt_abseta_pt_wEff.json"
    )
    TauTRG_jsonPath = (
        "/cvmfs/cms-griddata.cern.ch/cat/metadata/TAU/{}/"
        + taujsonfileversion
        + "/tau_DeepTau2018v2p5_{}.json.gz"
    )
    muTauTRG_jsonPath = os.path.join(
        os.environ["ANALYSIS_PATH"],
        "Corrections/data/TRG/{}/CrossMuTauHlt_MuLeg_v1.json",
    )
    eTauTRG_jsonPath = os.path.join(
        os.environ["ANALYSIS_PATH"],
        "Corrections/data/TRG/{}/CrossEleTauHlt_EleLeg_v1.json",
    )
    TaujetTRG_jsonPath = os.path.join(
        os.environ["ANALYSIS_PATH"],
        "Corrections/data/TRG/{}/DiTauJetHlt_JetLeg_v1.json",
    )

    initialized = False
    SFSources = {
        "singleIsoMu": ["IsoMu24"],
        "singleEleWpTight": ["singleEle"],
        "singleMu": ["IsoMu24"],
        "singleEle": ["singleEle"],
        "ditau": ["ditau_DM0", "ditau_DM1", "ditau_3Prong"],
    }

    year = ""

    def __init__(self, period, config, trigger_dict):
        # json_correction_path = eval(trigger_dict['ditaujet']['legs'][1]["jsonTRGcorrection_path"])
        tau_filename_dict = {
            "2022_Summer22": "2022_preEE",
            "2022_Summer22EE": "2022_postEE",
            "2023_Summer23": "2023_preBPix",
            "2023_Summer23BPix": "2023_postBPix",
        }
        period_in_taupog_folder = {
            "Run2_2016_HIPM": "Run2-2016preVFP-UL-NanoAODv9",
            "Run2_2016": "Run2-2016postVFP-UL-NanoAODv9",
            "Run2_2017": "Run2-2017-UL-NanoAODv9",
            "Run2_2018": "Run2-2018-UL-NanoAODv9",
            "2022_Summer22": "Run3-22CDSep23-Summer22-NanoAODv12",
            "2022_Summer22EE": "Run3-22EFGSep23-Summer22EE-NanoAODv12",
            "2023_Summer23": "Run3-23CSep23-Summer23-NanoAODv12",
            "2023_Summer23BPix": "Run3-23DSep23-Summer23BPix-NanoAODv12",
        }

        self.period = period
        self.config = config
        self.trigger_dict = trigger_dict

        jsonFile_e = os.path.join(
            os.environ["ANALYSIS_PATH"], TrigCorrProducer.eTRG_jsonPath.format(period)
        )
        jsonFile_Tau = os.path.join(
            os.environ["ANALYSIS_PATH"],
            TrigCorrProducer.TauTRG_jsonPath.format(
                period_in_taupog_folder[period], tau_filename_dict[period]
            ),
        )
        jsonFile_Mu = os.path.join(
            os.environ["ANALYSIS_PATH"],
            TrigCorrProducer.MuTRG_jsonPath.format(tau_filename_dict[period]),
        )
        jsonFile_TauJet = os.path.join(
            os.environ["ANALYSIS_PATH"],
            TrigCorrProducer.TaujetTRG_jsonPath.format(tau_filename_dict[period]),
        )
        jsonFile_muTau = os.path.join(
            os.environ["ANALYSIS_PATH"],
            TrigCorrProducer.muTauTRG_jsonPath.format(tau_filename_dict[period]),
        )
        jsonFile_eTau = os.path.join(
            os.environ["ANALYSIS_PATH"],
            TrigCorrProducer.eTauTRG_jsonPath.format(tau_filename_dict[period]),
        )

        if not TrigCorrProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "triggersRun3.h")
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')
            TrigCorrProducer.year = period.split("_")[0]
            self.year = period.split("_")[0]
            if period.endswith("Summer22"):
                TrigCorrProducer.year = period.split("_")[0] + "Re-recoBCD"
            if period.endswith("Summer22EE"):
                TrigCorrProducer.year = period.split("_")[0] + "Re-recoE+PromptFG"
            if period.endswith("Summer23"):
                TrigCorrProducer.year = period.split("_")[0] + "PromptC"
            if period.endswith("Summer23BPix"):
                TrigCorrProducer.year = period.split("_")[0] + "PromptD"

            # ROOT.gInterpreter.ProcessLine(f"""::correction::TrigCorrProvider::Initialize("{jsonFile_Mu}","{jsonFile_e}", "{jsonFile_Tau}", "{self.muon_trg_dict[period]}","{self.ele_trg_dict['McEff'][period]}", "{self.tau_trg_dict[period]}", "{period}")""")
            mu_trg_key_mc, mu_trg_key_data = None, None
            ele_trg_key_mc, ele_trg_key_data = None, None

            # bbWW uses singleIsoMu and singleEleWpTight names
            if "singleIsoMu" in self.trigger_dict.keys():
                mu_trg_key_mc = self.trigger_dict["singleIsoMu"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period].format("MC")
                mu_trg_key_data = self.trigger_dict["singleIsoMu"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period].format("DATA")
            if "singleEleWpTight" in self.trigger_dict.keys():
                ele_trg_key_mc = self.trigger_dict["singleEleWpTight"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period].format("Mc")
                ele_trg_key_data = self.trigger_dict["singleEleWpTight"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period].format("Data")

            # Now bbtautau keys
            mutau_trg_key_mc, mutau_trg_key_data = None, None
            tau_trg_key = None
            jet_trg_key = None
            if "singleMu" in self.trigger_dict.keys():
                mu_trg_key_mc = self.trigger_dict["singleMu"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period].format("MC")
                mu_trg_key_data = self.trigger_dict["singleMu"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period].format("DATA")
            if "singleEle" in self.trigger_dict.keys():
                ele_trg_key_mc = self.trigger_dict["singleEle"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period].format("Mc")
                ele_trg_key_data = self.trigger_dict["singleEle"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period].format("Data")
            if "mutau" in self.trigger_dict.keys():
                mutau_trg_key_mc = self.trigger_dict["mutau"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period].format("MC")
                mutau_trg_key_data = self.trigger_dict["mutau"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period].format("DATA")
            if "ditau" in self.trigger_dict.keys():
                tau_trg_key = self.trigger_dict["ditau"]["legs"][0][
                    "jsonTRGcorrection_key"
                ][period]
            if "ditaujet" in self.trigger_dict.keys():
                jet_trg_key = self.trigger_dict["ditaujet"]["legs"][1][
                    "jsonTRGcorrection_key"
                ][period]

            ROOT.gInterpreter.ProcessLine(
                f"""::correction::TrigCorrProvider::Initialize("{jsonFile_Mu}","{jsonFile_e}", "{jsonFile_Tau}", "{jsonFile_TauJet}", "{jsonFile_eTau}", "{jsonFile_muTau}", "{mu_trg_key_mc}", "{mu_trg_key_data}", "{mutau_trg_key_mc}", "{mutau_trg_key_data}","{ele_trg_key_mc}","{ele_trg_key_data}", "{tau_trg_key}", "{jet_trg_key}", "{period}")"""
            )
            print("TrigCorrProducer initialized")
            TrigCorrProducer.initialized = True

    def getSF(self, df, trigger_names, lepton_legs, return_variations, isCentral):
        SF_branches = []
        legs_to_be = {
            "singleIsoMu": ["mu", "mu"],
            "singleEleWpTight": ["e", "e"],
            "ditau": ["tau", "tau"],
            "singleMu": ["mu", "mu"],
            "singleEle": ["e", "e"],
        }
        for trg_name in [
            "singleEleWpTight",
            "singleIsoMu",
            "singleEle",
            "singleMu",
            "ditau",
        ]:
            if trg_name not in trigger_names:
                continue
            sf_sources = (
                TrigCorrProducer.SFSources[trg_name] if return_variations else []
            )
            for leg_idx, leg_name in enumerate(lepton_legs):
                applyTrgBranch_name = f"{trg_name}_{leg_name}_ApplyTrgSF"
                leg_to_be = legs_to_be[trg_name][leg_idx]
                df = df.Define(
                    applyTrgBranch_name,
                    f"""{leg_name}_legType == Leg::{leg_to_be} && {leg_name}_index >= 0 && HLT_{trg_name} && {leg_name}_HasMatching_{trg_name}""",
                )
                for source in [central] + sf_sources:
                    for scale in getScales(source):
                        if source == central and scale != central:
                            continue
                        if not isCentral and scale != central:
                            continue
                        syst_name = getSystName(source, scale)
                        suffix = f"{trg_name}_{syst_name}"
                        branch_name = f"weight_{leg_name}_TrgSF_{suffix}"
                        branch_central = f"weight_{leg_name}_TrgSF_{trg_name}_{getSystName(central,central)}"
                        # the trigCorr dictionary below is due to different analysis having different trigger names for muon and electron.
                        trigCorr_dict = {
                            "singleIsoMu": "singleIsoMu",
                            "singleEleWpTight": "singleEleWpTight",
                            "ditau": "ditau",
                            "singleMu": "singleIsoMu",
                            "singleEle": "singleEleWpTight",
                        }
                        # for tau trigger sf, selecting SF for the time being as a corrtype, rather than eff_data/eff_mc
                        if trg_name == "ditau":
                            df = df.Define(
                                f"{branch_name}_double",
                                f"""{applyTrgBranch_name} ? ::correction::TrigCorrProvider::getGlobal().getSF_{trigCorr_dict[trg_name]}(
                                        {leg_name}_p4,"{TrigCorrProducer.year}",Tau_decayMode.at(HttCandidate.leg_index[{leg_idx}]), "{trigCorr_dict[trg_name]}", "Medium", "sf", ::correction::TrigCorrProvider::UncSource::{source}, ::correction::UncScale::{scale} ) : 1.f""",
                            )
                        else:
                            df = df.Define(
                                f"{branch_name}_double",
                                f"""{applyTrgBranch_name} ? ::correction::TrigCorrProvider::getGlobal().getSF_{trigCorr_dict[trg_name]}(
                                        {leg_name}_p4,"{TrigCorrProducer.year}", ::correction::TrigCorrProvider::UncSource::{source}, ::correction::UncScale::{scale} ) : 1.f""",
                            )
                        if scale != central:
                            df = df.Define(
                                f"{branch_name}_rel",
                                f"static_cast<float>({branch_name}_double/{branch_central})",
                            )
                            branch_name += "_rel"
                        else:
                            df = df.Define(
                                f"{branch_name}",
                                f"static_cast<float>({branch_name}_double)",
                            )
                        SF_branches.append(f"{branch_name}")
        return df, SF_branches

    def getEff(self, df, trigger_names, offline_legs, trigger_dict):
        ch_trg = self.config.get("triggers", [])
        tauwps = self.config.get("deepTauWPs", [])
        VSjetWP = {}
        for ch in ch_trg:
            for trg in ch_trg[ch]:
                if ch in tauwps.keys():
                    VSjetWP[trg] = tauwps[ch]["VSjet"]
                else:
                    VSjetWP[trg] = "placeholder"
        SF_branches = []
        for trg_name in trigger_names:
            trigger_legs = trigger_dict[trg_name]["legs"]
            for trg_leg_idx, trg_leg in enumerate(trigger_legs):
                electron_input = trigger_dict[trg_name]["legs"][trg_leg_idx][
                    "jsonTRGcorrection_elepath"
                ]
                legtype_query = re.search(
                    r"{obj}_legType == Leg::\w+", trg_leg["offline_obj"]["cut"]
                )
                # Extract the leg type (e.g., 'mu') from the string "{obj}_legType == Leg::mu"
                legtype_value = None
                match = (
                    re.search(r"Leg::(\w+)", legtype_query.group(0))
                    if legtype_query
                    else None
                )
                legtype_value = match.group(1) if match else None
                # legtype_query = legtype_query.group(0) if legtype_query else ""
                # legtype_query = re.sub(r"(Leg::\w+)", r"static_cast<int>(\1)", legtype_query)
                for leg_idx, leg_name in enumerate(offline_legs):
                    applyTrgBranch_name = (
                        f"{trg_name}_{leg_name}_triggerleg{trg_leg_idx+1}_ApplyTrgSF"
                    )
                    # query = legtype_query.format(obj=leg_name)
                    query = trg_leg["offline_obj"]["cut"].format(obj=leg_name)
                    query += f""" && {leg_name}_index >= 0 && HLT_{trg_name} && {leg_name}_HasMatching_{trg_name}"""
                    df = df.Define(applyTrgBranch_name, f"""{query}""")
                    for scale in getScales(None):
                        for mc_or_data in ["data", "mc"]:
                            eff = f"eff_{mc_or_data}_{leg_name}_{trg_name}_triggerleg_{legtype_value}_{scale}"
                            func_name = "getEff_" + trg_name
                            # if len(trigger_legs)>1: func_name += f"_leg{trg_leg_idx+1}"
                            if len(trigger_legs) > 1 and legtype_value != None:
                                func_name += f"_leg_{legtype_value}"
                            args = f""" {leg_name}_p4, {leg_name}_decayMode, "{TrigCorrProducer.year}", "{trg_name}", "{electron_input}", "{VSjetWP[trg_name]}", ::correction::TrigCorrProvider::UncSource::{central}, ::correction::UncScale::{scale}, "{mc_or_data}" """
                            df = df.Define(
                                eff,
                                f"""{applyTrgBranch_name} ? ::correction::TrigCorrProvider::getGlobal().{func_name}({args})  : 1.f """,
                            )
                            SF_branches.append(eff)
        return df, SF_branches
