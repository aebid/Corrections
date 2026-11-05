import os
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


class JetCorrProducer:
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

    # Freeze from latest so the code doesn't break from new corr styles
    jet_jsonPath = (
        # "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/{}/latest/jet_jerc.json.gz"
        "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/{}/jet_jerc.json.gz"
    )
    fatjet_jsonPath = (
        # "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/{}/latest/fatJet_jerc.json.gz"
        "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/{}/fatJet_jerc.json.gz"
    )
    # jersmear_jsonPath = "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/JER-Smearing/latest/jer_smear.json.gz"
    jersmear_jsonPath = "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/JER-Smearing/2026-09-18/jer_smear.json.gz"

    # maps campaign to JER tag (only for MC!)
    jer_tag_map = {
        "2022_Summer22": "Summer22_22Sep2023_JRV2_MC",
        "2022_Prompt": "JR_Winter22Run3_V2_MC",
        "2022_Summer22EE": "Summer22EE_22Sep2023_JRV2_MC",
        "2023_Summer23BPix": "Summer23BPixPrompt23_RunD_JRV3_MC",
        "2023_Summer23": "Summer23Prompt23_RunCv1234_JRV3_MC",
        "2024_Summer24": "Summer24Prompt24_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2024 data. The JER MC_ScaleFactor and MC_PtResolution for the Summer24 samples will be announced soon. from https://cms-jerc.web.cern.ch/Recommendations/#2024_1
        "2025_Summer24": "Summer24Prompt25_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2025 data. The JER MC_ScaleFactor and MC_PtResolution for the Winter25 samples will be announced soon.  https://cms-jerc.web.cern.ch/Recommendations/#2025_1 # tmp patch because 2025_Summer24 does not exist
        "2025_Winter25": "Summer24Prompt25_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2025 data. The JER MC_ScaleFactor and MC_PtResolution for the Winter25 samples will be announced soon. https://cms-jerc.web.cern.ch/Recommendations/#2025_1
        "2026_Summer24": "Summer24Prompt26_RunBD_JRV1_MC",  # RunC (low PU) has its own JER, but no certified luminosity
    }

    # maps campaign to JEC tag
    jec_tag_map_mc = {
        "2022_Prompt": ["Winter22Run3_V4_MC"],
        "2022_Summer22": [
            "Summer22_22Sep2023_V4_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2022-preee
        "2022_Summer22EE": [
            "Summer22EE_22Sep2023_V4_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2022-postee
        "2023_Summer23BPix": [
            "Summer23BPixPrompt23_V4_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2023-postbpix
        "2023_Summer23": [
            "Summer23Prompt23_V4_MC",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2023-prebpix
        "2024_Summer24": [
            "Summer24Prompt24_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024
        "2025_Summer24": [
            "Winter25Prompt25_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2025 # tmp patch because 2025_Summer24 does not exist
        "2025_Winter25": [
            "Winter25Prompt25_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2025
        "2026_Summer24": ["Summer24Prompt26_V1_MC"],
    }

    # maps campaign to base tag
    # for DATA: jec_tag = {base_tag}_Run{letters}_V{version}_DATA
    jec_tag_map_data = {
        "2022_Prompt": ["Winter22Run3_Run{}_V4_DATA"],
        "2022_Summer22": [
            # "Summer22_22Sep2023_Run{}_V3_DATA",
            f"Summer22_22Sep2023_V4_DATA"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2022-preee
        "2022_Summer22EE": [
            "Summer22EE_22Sep2023_Run{}_V4_DATA",
            "Summer22EE_22Sep2023_V4_DATA",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2022-postee
        "2023_Summer23BPix": [
            "Summer23BPixPrompt23_Run{}_V4_DATA",
            "Summer23BPixPrompt23_V4_DATA",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2023-postbpix
        "2023_Summer23": [
            "Summer23Prompt23_Run{}_V4_DATA",
            "Summer23Prompt23_V4_DATA",
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2023
        "2024_Summer24": [
            "Summer24Prompt24_V3_DATA"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024
        "2025_Summer24": [
            "Winter25Prompt25_V3_DATA",
        ],  # 2025 JSON has no per-era Run letter
        "2025_Winter25": [
            "Winter25Prompt25_V3_DATA",
        ],
        "2026_Summer24": [
            "Summer24Prompt26_V1_DATA",
        ],
    }

    # maps campaign to JER tag (only for MC!)
    fatjer_tag_map = {
        "2022_Summer22": "Summer22_22Sep2023_JRV2_MC",
        "2022_Prompt": "JR_Winter22Run3_V2_MC",
        "2022_Summer22EE": "Summer22EE_22Sep2023_JRV2_MC",
        "2023_Summer23BPix": "Summer23BPixPrompt23_RunD_JRV3_MC",
        "2023_Summer23": "Summer23Prompt23_RunCv1234_JRV3_MC",
        "2024_Summer24": "Summer24Prompt24_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2024 data. The JER MC_ScaleFactor and MC_PtResolution for the Summer24 samples will be announced soon. from https://cms-jerc.web.cern.ch/Recommendations/#2024_1
        "2025_Summer24": "Summer24Prompt25_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2025 data. The JER MC_ScaleFactor and MC_PtResolution for the Winter25 samples will be announced soon.  https://cms-jerc.web.cern.ch/Recommendations/#2025_1 # tmp patch because 2025_Summer24 does not exist
        "2025_Winter25": "Summer24Prompt25_JRV1_MC",  # For the time being, use the Summer23BPix JERs for 2025 data. The JER MC_ScaleFactor and MC_PtResolution for the Winter25 samples will be announced soon. https://cms-jerc.web.cern.ch/Recommendations/#2025_1
        "2026_Summer24": "Summer24Prompt26_RunBD_JRV1_MC",  # RunC (low PU) has its own JER, but no certified luminosity
    }

    # maps campaign to JEC tag
    fatjec_tag_map_mc = {
        "2022_Summer22": ["Summer22_22Sep2023_V4_MC"],
        "2022_Prompt": ["Winter22Run3_V4_MC"],
        "2022_Summer22EE": ["Summer22EE_22Sep2023_V4_MC"],
        "2023_Summer23BPix": ["Summer23BPixPrompt23_V4_MC"],
        "2023_Summer23": [
            "Summer23Prompt23_V4_MC",
        ],  # Summer23Prompt23_V3_MC should be there (https://cms-jerc.web.cern.ch/Recommendations/#2023) but it does not find any key, so keep v2 for the moment... https://cms-jerc.web.cern.ch/Recommendations/#2023
        "2024_Summer24": [
            "Summer24Prompt24_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024
        "2025_Summer24": [
            "Winter25Prompt25_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024 # tmp patch because 2025_Summer24 does not exist
        "2025_Winter25": [
            "Winter25Prompt25_V3_MC"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024
        "2026_Summer24": ["Summer24Prompt26_V1_MC"],
    }

    fatjec_tag_map_data = {
        "2022_Summer22": [
            "Summer22_22Sep2023_V4_DATA"
        ],  # "Summer22_22Sep2023_Run{}_V3_DATA",
        "2023_Summer23BPix": [
            "Summer23BPixPrompt23_Run{}_V4_DATA",
            "Summer23BPixPrompt23_V4_DATA",
        ],
        "2022_Prompt": ["Winter22Run3_Run{}_V4_DATA"],
        "2023_Summer23": [
            "Summer23Prompt23_Run{}_V4_DATA",
            "Summer23Prompt23_V4_DATA",
        ],  # Summer23Prompt23_V3_DATA should be there (https://cms-jerc.web.cern.ch/Recommendations/#2023) but it does not find any key, so keep v2 for the moment... https://cms-jerc.web.cern.ch/Recommendations/#2023
        "2022_Summer22EE": [
            "Summer22EE_22Sep2023_Run{}_V4_DATA",
            "Summer22EE_22Sep2023_V4_DATA",
        ],
        "2024_Summer24": [
            "Summer24Prompt24_V3_DATA"
        ],  # https://cms-jerc.web.cern.ch/Recommendations/#2024
        "2025_Summer24": [
            "Winter25Prompt25_V3_DATA",
        ],
        "2025_Winter25": [
            "Winter25Prompt25_V3_DATA",
        ],
        "2026_Summer24": [
            "Summer24Prompt26_V1_DATA",
        ],
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
        "2026_Summer24": [],
    }

    run_letters = {
        "2022_Summer22": ["CD"],
        "2023_Summer23BPix": ["D"],
        "2022_Prompt": ["C", "D"],
        "2023_Summer23": ["C"],
        "2022_Summer22EE": ["E", "F", "G"],
        "2024_Winter24": ["BCD", "E", "F", "G", "H"],
        "2024_Summer24": ["CDEReprocessing", "FGHIPrompt"],
        "2025_Winter25": ["B", "C", "D", "E", "F", "G"],
        "2025_Summer24": ["B", "C", "D", "E", "F", "G"],
        "2026_Summer24": ["A", "B", "C", "D"],
    }

    # Sources = []

    def __init__(self, campaign, isData, sample_name, use_regrouped=False):
        self.isData = isData
        self.sample_name = sample_name
        self.use_regrouped = use_regrouped
        self.uncSources_toUse = []
        if self.use_regrouped:
            self.uncSources_toUse = JetCorrProducer.uncSources_regrouped
        else:
            self.uncSources_toUse = JetCorrProducer.uncSources_minimal
        self.year = int(campaign[:4])
        self.campaign = campaign
        print("Initializing new JetCorrProducer")

        jet_path = JetCorrProducer.jet_jsonPath.format(
            pog_folder_names["JERC"][campaign]
        )
        jet_jsonFile = os.path.join(os.environ["ANALYSIS_PATH"], jet_path)
        jersmear_path = JetCorrProducer.jersmear_jsonPath
        jetsmear_jsonFile = os.path.join(os.environ["ANALYSIS_PATH"], jersmear_path)
        year = campaign.split("_")[0]
        jec_tag_map = (
            JetCorrProducer.jec_tag_map_data
            if self.isData
            else JetCorrProducer.jec_tag_map_mc
        )

        jec_tag_array = jec_tag_map[campaign]
        jec_tag = jec_tag_array[0]
        other_jec_tag = jec_tag_array[1] if len(jec_tag_array) > 1 else jec_tag_array[0]
        # print(f"jec_tag is {jec_tag}")
        fatjet_path = JetCorrProducer.fatjet_jsonPath.format(
            pog_folder_names["JERC"][campaign]
        )
        fatjet_jsonFile = os.path.join(os.environ["ANALYSIS_PATH"], fatjet_path)
        fatjec_tag_map = (
            JetCorrProducer.fatjec_tag_map_data
            if self.isData
            else JetCorrProducer.fatjec_tag_map_mc
        )

        fatjec_tag_array = fatjec_tag_map[campaign]
        fatjec_tag = fatjec_tag_array[0]
        other_fatjec_tag = (
            fatjec_tag_array[1] if len(fatjec_tag_array) > 1 else fatjec_tag_array[0]
        )

        if self.isData:
            letter_list = JetCorrProducer.run_letters[campaign]
            version_list = JetCorrProducer.run_versions[campaign]
            sample_letter = ""
            sample_version = ""
            if sample_name[-1].isalpha():
                sample_letter = sample_name[-1]
            elif sample_name[-1].isnumeric():
                tokens = sample_name.split("_")
                sample_version = tokens[-1]
                sample_letter = tokens[-2][-1]
            if campaign in ("2025_Summer24", "2026_Summer24"):
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

        jer_tag = JetCorrProducer.jer_tag_map[campaign]
        algo = JetCorrProducer.jet_algorithm

        fatjer_tag = JetCorrProducer.jer_tag_map[campaign]
        fatalgo = JetCorrProducer.fatjet_algorithm

        declareProviderHeader("jet.h")
        self.provider = CppProvider(
            "correction::JetCorrectionProvider",
            jet_jsonFile,
            jetsmear_jsonFile,
            jec_tag,
            other_jec_tag,
            jer_tag,
            algo,
            fatjet_jsonFile,
            fatjec_tag,
            other_fatjec_tag,
            fatjer_tag,
            fatalgo,
            year,
            self.isData,
            self.use_regrouped,
            True,
        )

    def getP4Variations(
        self, df, source_dict, apply_JER, apply_JES, apply_forward_jet_horns_fix_=False
    ):
        apply_forward_jet_horns_fix = (
            "true" if apply_forward_jet_horns_fix_ else "false"
        )
        apply_jer = "true" if apply_JER and not self.isData else "false"
        reapply_jec = "true"  # by the time being
        require_run_number = "false"
        if self.isData:
            require_run_number = "true"
        if self.campaign == "2023_Summer23BPix":
            require_run_number = "true"
        wantPhi = (
            "true"
            if (self.campaign == "2023_Summer23BPix" and self.isData)
            or (self.campaign in ("2024_Summer24", "2025_Summer24", "2026_Summer24"))
            else "false"
        )
        if not self.isData:
            df = df.Define(
                "Jet_p4_shifted_map",
                f"""{self.provider.ref}->getShiftedP4_Jet(Jet_pt, Jet_eta, Jet_phi, Jet_mass,
                                                                                                                       Jet_rawFactor, Jet_area, Rho_fixedGridRhoFastjetAll, event, {apply_jer},
                                                                                                                       {reapply_jec}, {require_run_number}, run, {wantPhi}, {apply_forward_jet_horns_fix},
                                                                                                                       GenJet_pt, GenJet_eta, GenJet_phi, Jet_genJetIdx)""",
            )

            df = df.Define(
                "FatJet_p4_shifted_map",
                f"""{self.provider.ref}->getShiftedP4_FatJet(FatJet_pt, FatJet_eta, FatJet_phi, FatJet_mass,
                                                                                                                       FatJet_rawFactor, FatJet_area, Rho_fixedGridRhoFastjetAll, event, {apply_jer},
                                                                                                                       {reapply_jec}, {require_run_number}, run, {wantPhi}, {apply_forward_jet_horns_fix},
                                                                                                                       GenJetAK8_pt, GenJetAK8_eta, GenJetAK8_phi, FatJet_genJetAK8Idx)""",
            )
        else:
            df = df.Define(
                "Jet_p4_shifted_map",
                f"""{self.provider.ref}->getShiftedP4_Jet(Jet_pt, Jet_eta, Jet_phi, Jet_mass, Jet_rawFactor, Jet_area, Rho_fixedGridRhoFastjetAll, event, {apply_jer}, {reapply_jec}, {require_run_number}, run, {wantPhi}, {apply_forward_jet_horns_fix})""",
            )
            df = df.Define(
                "FatJet_p4_shifted_map",
                f"""{self.provider.ref}->getShiftedP4_FatJet(FatJet_pt, FatJet_eta, FatJet_phi, FatJet_mass, FatJet_rawFactor, FatJet_area, Rho_fixedGridRhoFastjetAll, event, {apply_jer}, {reapply_jec}, {require_run_number}, run, {wantPhi}, {apply_forward_jet_horns_fix})""",
            )
        class_name = "JetCorrectionProvider"

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
                source_eff = source_eff + self.campaign.split("_")[0]
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
        df = df.Define(
            "Jet_ptRes",
            f"{self.provider.ref}->GetResolutions(Jet_pt, Jet_mass, Jet_rawFactor, Jet_eta, Rho_fixedGridRhoFastjetAll)",
        )
        return df
