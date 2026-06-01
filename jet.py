import os
import urllib.request
import ROOT
from .CorrectionsCore import *

# https://docs.google.com/spreadsheets/d/1JZfk78_9SD225bcUuTWVo4i02vwI5FfeVKH-dwzUdhM/edit#gid=1345121349

# MET corrections
# https://twiki.cern.ch/twiki/bin/viewauth/CMS/MissingETRun2Corrections
# https://lathomas.web.cern.ch/lathomas/METStuff/XYCorrections/XYMETCorrection_withUL17andUL18andUL16.h
# https://indico.cern.ch/event/1033432/contributions/4339934/attachments/2235168/3788215/metxycorrections_UL2016.pdf
# JEC uncertainty sources took from recommendation here:
# https://twiki.cern.ch/twiki/bin/view/CMS/JECDataMC
# https://github.com/cms-jet/JECDatabase/tree/master
# https://twiki.cern.ch/twiki/bin/view/CMS/JECUncertaintySources
# JER uncertainty source took from:
# https://twiki.cern.ch/twiki/bin/view/CMS/JetResolution
# https://github.com/cms-jet/JRDatabase
# smearing procedure
# https://twiki.cern.ch/twiki/bin/viewauth/CMS/JetResolution#Smearing_procedures

# according to recommendation, SummerUL19 should be used but also SummerUL20 are available for JER.
"""BBEC1_2016postVFP

IMPORTANT
From: https://twiki.cern.ch/twiki/bin/view/CMS/PdmVRun2LegacyAnalysis

Note: The RunIISummer19UL16(APV) samples have a bug in the beamspot position affecting only (most of the) 2016 samples HN, HN, talk. The RunIISummer19UL16 samples will be invalidated at the end of August. Please migrate to Summer20UL now. All Summer19UL samples are based on an older version of pythia. The difference of Summer19UL and Summer20UL due to the difference in the pythia version was studied and found negligible 1 2 3. Invalidation and deletion of all RunIISummer19 samples, for all years, is scheduled for the end of September 2021

"""


def getJMEFile(jme_repo, jme_file):
    repo_dict = {
        "JRDatabase": {
            "url": "https://raw.githubusercontent.com/cms-jet/JRDatabase/refs/heads/master/textFiles/",
            "path": "data/JRDatabase/textFiles/",
        },
        "JECDatabase": {
            "url": "https://raw.githubusercontent.com/cms-jet/JECDatabase/refs/heads/master/textFiles/",
            "path": "data/JECDatabase/textFiles/",
        },
    }

    if jme_repo not in repo_dict:
        raise RuntimeError(
            f"JME repository {jme_repo} not found in available repositories: {repo_dict.keys()}"
        )
    repo_entry = repo_dict[jme_repo]
    this_file_dir = os.path.dirname(os.path.abspath(__file__))
    jme_file_dir = os.path.join(this_file_dir, repo_entry["path"])
    jme_file_path = os.path.join(jme_file_dir, jme_file)
    if not os.path.exists(jme_file_path):
        if not os.path.exists(jme_file_dir):
            os.makedirs(jme_file_dir)
        url = repo_entry["url"] + jme_file
        print(f"Downloading {jme_file} from {url}")
        urllib.request.urlretrieve(url, jme_file_path)
    return jme_file_path


directories_JER = {
    "2018_UL": "Summer19UL18_JRV2",
    "2017_UL": "Summer19UL17_JRV2",
    "2016preVFP_UL": "Summer20UL16APV_JRV3",
    "2016postVFP_UL": "Summer20UL16_JRV3",
}
directories_JEC = {
    "2018_UL": "Summer19UL18_V5_MC",
    "2017_UL": "Summer19UL17_V5_MC",
    "2016preVFP_UL": "Summer19UL16APV_V7_MC",
    "2016postVFP_UL": "Summer19UL16_V7_MC",
}

regrouped_files_names = {
    "2018_UL": "RegroupedV2_Summer19UL18_V5_MC_UncertaintySources_AK4PFchs.txt",
    "2017_UL": "RegroupedV2_Summer19UL17_V5_MC_UncertaintySources_AK4PFchs.txt",
    "2016preVFP_UL": "RegroupedV2_Summer19UL16APV_V7_MC_UncertaintySources_AK4PFchs.txt",
    "2016postVFP_UL": "RegroupedV2_Summer19UL16_V7_MC_UncertaintySources_AK4PFchs.txt",
}


class JetCorrProducer:
    jsonPath_btag = "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/{}/btagging.json.gz"

    initialized = False

    jet_algorithm = "AK4PFPuppi"
    fatjet_algorithm = "AK8PFPuppi"

    uncSources_regrouped = [
        "FlavorQCD",
        "RelativeBal",
        "HF",
        "BBEC1",
        "EC2",
        "Absolute",
        "BBEC1_",
        "Absolute_",
        "EC2_",
        "HF_",
        "RelativeSample_",
    ]

    uncSources_minimal = ["Total"]

    jet_jsonPath = (
        "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/{}/latest/jet_jerc.json.gz"
    )
    fatjet_jsonPath = (
        "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/{}/latest/fatJet_jerc.json.gz"
    )
    jersmear_jsonPath = "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/JER-Smearing/latest/jer_smear.json.gz"

    # maps period to JER tag (only for MC!)
    jer_tag_map = {
        "2022_Summer22": "Summer22_22Sep2023_JRV1_MC",
        "2022_Prompt": "JR_Winter22Run3_V1_MC",
        "2022_Summer22EE": "Summer22EE_22Sep2023_JRV1_MC",
        "2023_Summer23BPix": "Summer23BPixPrompt23_RunD_JRV1_MC",
        "2023_Summer23": "Summer23Prompt23_RunCv1234_JRV1_MC",
        "2024_Summer24": "Summer23BPixPrompt23_RunD_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2024 data. The JER MC_ScaleFactor and MC_PtResolution for the Summer24 samples will be announced soon. from https://cms-jerc.web.cern.ch/Recommendations/#2024_1
        "2025_Summer24": "Summer23BPixPrompt23_RunD_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2025 data. The JER MC_ScaleFactor and MC_PtResolution for the Winter25 samples will be announced soon.  https://cms-jerc.web.cern.ch/Recommendations/#2025_1 # tmp patch because 2025_Summer24 does not exist
        "2025_Winter25": "Summer23BPixPrompt23_RunD_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2025 data. The JER MC_ScaleFactor and MC_PtResolution for the Winter25 samples will be announced soon. https://cms-jerc.web.cern.ch/Recommendations/#2025_1
    }

    # maps period to JEC tag
    jec_tag_map_mc = {
        "2022_Prompt": ["Winter22Run3_V3_MC"],
        "2022_Summer22": [
            "Summer22_22Sep2023_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2022-preee
        "2022_Summer22EE": [
            "Summer22EE_22Sep2023_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2022-postee
        "2023_Summer23BPix": [
            "Summer23BPixPrompt23_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2023-postbpix
        "2023_Summer23": [
            "Summer23Prompt23_V3_MC",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2023-prebpix
        "2024_Summer24": [
            "Summer24Prompt24_V2_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024
        "2025_Summer24": [
            "Winter25Prompt25_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2025 # tmp patch because 2025_Summer24 does not exist
        "2025_Winter25": [
            "Winter25Prompt25_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2025
    }

    # maps period to base tag
    # for DATA: jec_tag = {base_tag}_Run{letters}_V{version}_DATA
    jec_tag_map_data = {
        "2022_Prompt": ["Winter22Run3_Run{}_V3_DATA"],
        "2022_Summer22": [
            # "Summer22_22Sep2023_Run{}_V3_DATA",
            "Summer22_22Sep2023_V3_DATA"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2022-preee
        "2022_Summer22EE": [
            "Summer22EE_22Sep2023_Run{}_V3_DATA",
            "Summer22EE_22Sep2023_V3_DATA",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2022-postee
        "2023_Summer23BPix": [
            "Summer23BPixPrompt23_Run{}_V3_DATA",
            "Summer23BPixPrompt23_V3_DATA",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2023-postbpix
        "2023_Summer23": [
            "Summer23Prompt23_Run{}_V3_DATA",
            "Summer23Prompt23_V3_DATA",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2023
        "2024_Summer24": [
            "Summer24Prompt24_V2_DATA"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024
        "2025_Summer24": [
            "Winter25Prompt25_Run{}_V3_DATA",
            "Winter25Prompt25_V3_DATA",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2025 # tmp patch because 2025_Summer24 does not exist
        "2025_Winter25": [
            "Winter25Prompt25_Run{}_V3_DATA",
            "Winter25Prompt25_V3_DATA",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2025
    }

    # maps period to JER tag (only for MC!)
    fatjer_tag_map = {
        "2022_Summer22": "Summer22_22Sep2023_JRV1_MC",
        "2022_Prompt": "JR_Winter22Run3_V1_MC",
        "2022_Summer22EE": "Summer22EE_22Sep2023_JRV1_MC",
        "2023_Summer23BPix": "Summer23BPixPrompt23_RunD_JRV1_MC",
        "2023_Summer23": "Summer23Prompt23_RunCv1234_JRV1_MC",
        "2024_Summer24": "Summer23BPixPrompt23_RunD_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2024 data. The JER MC_ScaleFactor and MC_PtResolution for the Summer24 samples will be announced soon. from https://cms-jerc.web.cern.ch/Recommendations/#2024_1
        "2025_Summer24": "Summer23BPixPrompt23_RunD_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2025 data. The JER MC_ScaleFactor and MC_PtResolution for the Winter25 samples will be announced soon.  https://cms-jerc.web.cern.ch/Recommendations/#2025_1 # tmp patch because 2025_Summer24 does not exist
        "2025_Winter25": "Summer23BPixPrompt23_RunD_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2025 data. The JER MC_ScaleFactor and MC_PtResolution for the Winter25 samples will be announced soon. https://cms-jerc.web.cern.ch/Recommendations/#2025_1
    }

    # maps period to JEC tag
    fatjec_tag_map_mc = {
        "2022_Summer22": ["Summer22_22Sep2023_V3_MC"],
        "2022_Prompt": ["Winter22Run3_V3_MC"],
        "2022_Summer22EE": ["Summer22EE_22Sep2023_V3_MC"],
        "2023_Summer23BPix": ["Summer23BPixPrompt23_V3_MC"],
        "2023_Summer23": [
            "Summer23Prompt23_V3_MC",
        ],  # Summer23Prompt23_V3_MC should be there (https://cms-jerc.web.cern.ch/Recommendations/#2023) but it does not find any key, so keep v2 for the moment... https://cms-jerc.web.cern.ch/Recommendations/#2023
        "2024_Summer24": [
            "Summer24Prompt24_V2_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024
        "2025_Summer24": [
            "Winter25Prompt25_V2_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024 # tmp patch because 2025_Summer24 does not exist
        "2025_Winter25": [
            "Winter25Prompt25_V2_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024
    }

    fatjec_tag_map_data = {
        "2022_Summer22": [
            "Summer22_22Sep2023_V3_DATA"
        ],  # "Summer22_22Sep2023_Run{}_V3_DATA",
        "2023_Summer23BPix": [
            "Summer23BPixPrompt23_Run{}_V3_DATA",
            "Summer23BPixPrompt23_V3_DATA",
        ],
        "2022_Prompt": ["Winter22Run3_Run{}_V3_DATA"],
        "2023_Summer23": [
            "Summer23Prompt23_Run{}_V3_DATA",
            "Summer23Prompt23_V3_DATA",
        ],  # Summer23Prompt23_V3_DATA should be there (https://cms-jerc.web.cern.ch/Recommendations/#2023) but it does not find any key, so keep v2 for the moment... https://cms-jerc.web.cern.ch/Recommendations/#2023
        "2022_Summer22EE": [
            "Summer22EE_22Sep2023_Run{}_V3_DATA",
            "Summer22EE_22Sep2023_V3_DATA",
        ],
        "2024_Summer24": [
            "Summer24Prompt24_V2_DATA"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024
        "2025_Summer24": [
            "Winter25Prompt25_Run{}_V3_DATA",
            "Winter25Prompt25_V3_DATA",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2025
        "2025_Winter25": [
            "Winter25Prompt25_Run{}_V3_DATA",
            "Winter25Prompt25_V3_DATA",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2025
    }

    run_versions = {
        "2022_Summer22": [],
        "2023_Summer23BPix": [],
        "2022_Prompt": [],
        "2023_Summer23": ["v123", "v4"],
        "2022_Summer22EE": [],
        "2024_Winter24": [],
        "2024_Summer24": [],  # ["nib1", "nib2", "nib3"], # https://cms-jerc.web.cern.ch/Recommendations/#2024 --> should have this naming convention, but apparently this does not work
        "2025_Summer24": [],
        "2025_Winter25": [],
    }

    run_letters = {
        "2022_Summer22": ["CD"],
        "2023_Summer23BPix": ["D"],
        "2022_Prompt": ["C", "D"],
        "2023_Summer23": ["C"],
        "2022_Summer22EE": ["E", "F", "G"],
        "2024_Winter24": ["BCD", "E", "F", "G", "H"],
        "2024_Summer24": ["CDEReprocessing", "FGHIPrompt"],
        "2025_Winter25": ["C", "D", "E", "F"],
        "2025_Summer24": ["C", "D", "E", "F"],
    }

    # Sources = []
    period = None

    def __init__(
        self, period, isData, sample_name, use_corrlib=True, use_regrouped=False
    ):
        self.isData = isData
        self.sample_name = sample_name
        self.use_regrouped = use_regrouped
        self.use_corrlib = use_corrlib
        self.uncSources_toUse = []
        if self.use_regrouped:
            self.uncSources_toUse = JetCorrProducer.uncSources_regrouped
        else:
            self.uncSources_toUse = JetCorrProducer.uncSources_minimal
        self.year = int(period[:4])
        self.period = period
        if not self.use_corrlib:
            print("Initializing old JetCorrProducer")
            JEC_dir = directories_JEC[period]
            JER_dir = directories_JER[period]
            type_suffix = "DATA" if isData else "MC"
            JER_SF_txt = (
                f"{JER_dir}_{type_suffix}/{JER_dir}_{type_suffix}_SF_AK4PFchs.txt"
            )
            JER_PtRes_txt = f"{JER_dir}_{type_suffix}/{JER_dir}_{type_suffix}_PtResolution_AK4PFchs.txt"
            JEC_Regrouped_txt = f"{JEC_dir}/{regrouped_files_names[period]}"
            ptResolution = getJMEFile("JRDatabase", JER_PtRes_txt)
            ptResolutionSF = getJMEFile("JRDatabase", JER_SF_txt)
            JEC_Regrouped = getJMEFile("JECDatabase", JEC_Regrouped_txt)
            if not JetCorrProducer.initialized:
                ROOT.gSystem.Load("libJetMETCorrectionsModules.so")
                ROOT.gSystem.Load("libCondFormatsJetMETObjects.so")
                ROOT.gSystem.Load("libCommonToolsUtils.so")
                headers_dir = os.path.dirname(os.path.abspath(__file__))
                header_path = os.path.join(headers_dir, "jet.h")
                JME_calc_base = os.path.join(headers_dir, "JMECalculatorBase.cc")
                JME_calc_path = os.path.join(
                    headers_dir, "JMESystematicsCalculators.cc"
                )
                ROOT.gInterpreter.Declare(f'#include "{JME_calc_base}"')
                ROOT.gInterpreter.Declare(f'#include "{JME_calc_path}"')
                ROOT.gInterpreter.Declare(f'#include "{header_path}"')

                ROOT.gInterpreter.ProcessLine(
                    f"""::correction::JetCorrProvider::Initialize("{ptResolution}", "{ptResolutionSF}","{JEC_Regrouped}", "{periods[period]}")"""
                )
                JetCorrProducer.period = period
                JetCorrProducer.initialized = True
        else:
            print("Initializing new JetCorrProducer")

            jet_path = JetCorrProducer.jet_jsonPath.format(
                pog_folder_names["JERC"][period]
            )
            jet_jsonFile = os.path.join(os.environ["ANALYSIS_PATH"], jet_path)
            jersmear_path = JetCorrProducer.jersmear_jsonPath
            jetsmear_jsonFile = os.path.join(os.environ["ANALYSIS_PATH"], jersmear_path)
            year = period.split("_")[0]
            jec_tag_map = (
                JetCorrProducer.jec_tag_map_data
                if self.isData
                else JetCorrProducer.jec_tag_map_mc
            )

            jec_tag_array = jec_tag_map[period]
            jec_tag = jec_tag_array[0]
            other_jec_tag = (
                jec_tag_array[1] if len(jec_tag_array) > 1 else jec_tag_array[0]
            )
            # print(f"jec_tag is {jec_tag}")
            fatjet_path = JetCorrProducer.fatjet_jsonPath.format(
                pog_folder_names["JERC"][period]
            )
            fatjet_jsonFile = os.path.join(os.environ["ANALYSIS_PATH"], fatjet_path)
            fatjec_tag_map = (
                JetCorrProducer.fatjec_tag_map_data
                if self.isData
                else JetCorrProducer.fatjec_tag_map_mc
            )

            fatjec_tag_array = fatjec_tag_map[period]
            fatjec_tag = fatjec_tag_array[0]
            other_fatjec_tag = (
                fatjec_tag_array[1]
                if len(fatjec_tag_array) > 1
                else fatjec_tag_array[0]
            )

            if self.isData:
                letter_list = JetCorrProducer.run_letters[period]
                version_list = JetCorrProducer.run_versions[period]
                sample_letter = ""
                sample_version = ""
                if sample_name[-1].isalpha():
                    sample_letter = sample_name[-1]
                elif sample_name[-1].isnumeric():
                    tokens = sample_name.split("_")
                    sample_version = tokens[-1]
                    sample_letter = tokens[-2][-1]
                if period == "2025_Summer24":
                    sample_version = ""

                # print(
                #     f"sample version = {sample_version}, sample letter = {sample_letter}"
                # )

                # in some cases, sample letter can be compound:
                # e.g. for 2022_Summer22 run letter is CD
                # if there is no exact match, take compound letter
                if sample_letter not in letter_list:
                    matches = [let for let in letter_list if sample_letter in let]
                    if len(matches) != 1:
                        raise RuntimeError(
                            f"ambiguous deduction of sample letter for {sample_name}: got letter options {matches}"
                        )
                    sample_letter = matches[0]

                # same for run version:
                # e.g. for 2023_Summer23 run version is v123 or v4
                # if there is no exact match, take compound version
                # sample_version = v* => need to check that * is in exactly one version in available version list
                if version_list and sample_version not in version_list:
                    matches = [v for v in version_list if sample_version[1:] in v]
                    if len(matches) != 1:
                        raise RuntimeError(
                            f"ambiguous deduction of sample version for {sample_name}: got version options {matches}"
                        )
                    sample_version = matches[0]

                letters = sample_letter + sample_version
                if not sample_letter and not sample_version:
                    raise RuntimeError(
                        f"sample name {sample_name} doesn't follow expected pattern base_letter_version"
                    )
                jec_tag = jec_tag.format(letters)
                other_jec_tag = other_jec_tag.format(letters)
                # print(f"jec_tag is {jec_tag}")

                fatjec_tag = fatjec_tag.format(letters)
                other_fatjec_tag = other_fatjec_tag.format(letters)
                # print(f"fatjec_tag is {fatjec_tag}")

            jer_tag = JetCorrProducer.jer_tag_map[period]
            algo = JetCorrProducer.jet_algorithm

            fatjer_tag = JetCorrProducer.jer_tag_map[period]
            fatalgo = JetCorrProducer.fatjet_algorithm

            if not JetCorrProducer.initialized:
                headers_dir = os.path.dirname(os.path.abspath(__file__))
                header_path = os.path.join(headers_dir, "jet.h")
                ROOT.gInterpreter.Declare(f'#include "{header_path}"')
                is_data = "true" if self.isData else "false"
                regrouped = "true" if self.use_regrouped else "false"
                apply_compound = "true"
                ROOT.gInterpreter.ProcessLine(
                    f"""::correction::JetCorrectionProvider::Initialize("{jet_jsonFile}",
                                                                                                  "{jetsmear_jsonFile}",
                                                                                                  "{jec_tag}",
                                                                                                  "{other_jec_tag}",
                                                                                                  "{jer_tag}",
                                                                                                  "{algo}",
                                                                                                  "{fatjet_jsonFile}",
                                                                                                  "{fatjec_tag}",
                                                                                                  "{other_fatjec_tag}",
                                                                                                  "{fatjer_tag}",
                                                                                                  "{fatalgo}",
                                                                                                  "{year}",
                                                                                                   {is_data},
                                                                                                   {regrouped},
                                                                                                   {apply_compound})"""
                )
                JetCorrProducer.initialized = True

    def getP4Variations(
        self, df, source_dict, apply_JER, apply_JES, apply_forward_jet_horns_fix_=False
    ):
        class_name = ""
        apply_forward_jet_horns_fix = (
            "true" if apply_forward_jet_horns_fix_ else "false"
        )
        if self.use_corrlib:
            apply_jer = "true" if apply_JER and not self.isData else "false"
            reapply_jec = "true"  # by the time being
            require_run_number = "false"
            if self.isData:
                require_run_number = "true"
            if self.period == "2023_Summer23BPix":
                require_run_number = "true"
            wantPhi = (
                "true"
                if (self.period == "2023_Summer23BPix" and self.isData)
                or (self.period == "2024_Summer24" or self.period == "2025_Summer24")
                else "false"
            )
            if not self.isData:
                df = df.Define(
                    "Jet_p4_shifted_map",
                    f"""::correction::JetCorrectionProvider::getGlobal().getShiftedP4(Jet_pt, Jet_eta, Jet_phi, Jet_mass,
                                                                                                                       Jet_rawFactor, Jet_area, Rho_fixedGridRhoFastjetAll, event, {apply_jer},
                                                                                                                       {reapply_jec},{require_run_number},run,{wantPhi},{apply_forward_jet_horns_fix},
                                                                                                                       GenJet_pt, Jet_genJetIdx)""",
                )

                df = df.Define(
                    "FatJet_p4_shifted_map",
                    f"""::correction::JetCorrectionProvider::getGlobal().getShiftedP4(FatJet_pt, FatJet_eta, FatJet_phi, FatJet_mass,
                                                                                                                       FatJet_rawFactor, FatJet_area, Rho_fixedGridRhoFastjetAll, event, {apply_jer},
                                                                                                                       {reapply_jec},{require_run_number},run,{wantPhi},{apply_forward_jet_horns_fix},
                                                                                                                       GenJetAK8_pt, FatJet_genJetAK8Idx)""",
                )
            else:
                df = df.Define(
                    "Jet_p4_shifted_map",
                    f"""::correction::JetCorrectionProvider::getGlobal().getShiftedP4(Jet_pt, Jet_eta, Jet_phi, Jet_mass, Jet_rawFactor, Jet_area, Rho_fixedGridRhoFastjetAll,event, {apply_jer},{reapply_jec}, {require_run_number}, run,{wantPhi},{apply_forward_jet_horns_fix})""",
                )
                df = df.Define(
                    "FatJet_p4_shifted_map",
                    f"""::correction::JetCorrectionProvider::getGlobal().getShiftedP4(FatJet_pt, FatJet_eta, FatJet_phi, FatJet_mass, FatJet_rawFactor, FatJet_area, Rho_fixedGridRhoFastjetAll, event, {apply_jer},{reapply_jec}, {require_run_number},run,{wantPhi},{apply_forward_jet_horns_fix})""",
                )
            class_name = "JetCorrectionProvider"
        else:
            df = df.Define(
                "Jet_p4_shifted_map",
                f"""::correction::JetCorrProvider::getGlobal().getShiftedP4(
                            Jet_pt, Jet_eta, Jet_phi, Jet_mass, Jet_rawFactor, Jet_area,
                            Jet_jetId, Rho_fixedGridRhoFastjetAll, Jet_partonFlavour, 0, GenJet_pt, GenJet_eta,
                            GenJet_phi, GenJet_mass, event)""",
            )
            class_name = "JetCorrProvider"

        apply_jer_list = []
        if apply_JER:
            apply_jer_list.append("JER")
        apply_jes_list = self.uncSources_toUse if apply_JES else []
        # central variable is imported from CorrectionsCore.py, where it is defined
        for source in [central] + apply_jes_list + apply_jer_list:
            source_eff = source
            if source in apply_jes_list:  # source!=central and source != "JER":
                source_eff = "JES_" + source_eff
            if source.endswith("_"):
                source_eff = source_eff + JetCorrProducer.period.split("_")[0]
                source += "year"
            updateSourceDict(source_dict, source_eff, "Jet")
            updateSourceDict(source_dict, source_eff, "FatJet")
            for scale in getScales(source):
                syst_name = getSystName(source_eff, scale)
                df = df.Define(
                    f"Jet_p4_{syst_name}",
                    f"Jet_p4_shifted_map.at({{::correction::{class_name}::UncSource::{source}, ::correction::UncScale::{scale}}})",
                )
                df = df.Define(
                    f"Jet_p4_{syst_name}_delta", f"Jet_p4_{syst_name} - Jet_p4_{nano}"
                )

                df = df.Define(
                    f"FatJet_p4_{syst_name}",
                    f"FatJet_p4_shifted_map.at({{::correction::{class_name}::UncSource::{source}, ::correction::UncScale::{scale}}})",
                )
                df = df.Define(
                    f"FatJet_p4_{syst_name}_delta",
                    f"FatJet_p4_{syst_name} - FatJet_p4_{nano}",
                )

        return df, source_dict

    def getEnergyResolution(self, df):
        if self.use_corrlib:
            df = df.Define(
                "Jet_ptRes",
                "::correction::JetCorrectionProvider::getGlobal().GetResolutions(Jet_pt, Jet_mass, Jet_rawFactor, Jet_eta, Rho_fixedGridRhoFastjetAll)",
            )
        else:
            df = df.Define(
                "Jet_ptRes",
                "::correction::JetCorrProvider::getGlobal().getResolution(Jet_pt, Jet_eta, Rho_fixedGridRhoFastjetAll)",
            )
        return df
