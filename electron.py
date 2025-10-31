import os
import ROOT
from .CorrectionsCore import *

# https://twiki.cern.ch/twiki/bin/viewauth/CMS/EgammaUL2016To2018
# https://github.com/cms-egamma/ScaleFactorsJSON?tab=readme-ov-file
# https://twiki.cern.ch/twiki/bin/view/CMS/EgammaSFJSON
# https://twiki.cern.ch/twiki/bin/view/CMS/EgammaPOG
# https://twiki.cern.ch/twiki/bin/viewauth/CMS/EgammaUL2016To2018#Access_of_SFs_using_JSON_files
# https://twiki.cern.ch/twiki/bin/view/CMS/EgHLTScaleFactorMeasurements
# https://twiki.cern.ch/twiki/bin/viewauth/CMS/EgammaUL2016To2018#Access_of_SFs_using_JSON_files
# https://twiki.cern.ch/twiki/bin/view/CMS/EGMHLTRun3RecommendationForPAG
# https://twiki.cern.ch/twiki/bin/view/CMS/ElectronScaleFactorsRun2#EGM_certified_vs_custom_self_pro


class EleCorrProducer:
    EleID_JsonPath = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/EGM/{}/electron.json.gz"
    EleES_JsonPath = "Corrections/data/EGM/{}/EGM_ScaleUnc.json.gz"
    EleES_JsonPath_Run3 = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/EGM/{}/electronSS.json.gz"
    initialized = False
    ID_sources = ["EleID"]
    working_points = ["wp80iso", "wp80noiso"]
    energyScaleSources_ele = ["EleES"]
    year = ""

    def __init__(self, period):
        EleID_JsonFile = EleCorrProducer.EleID_JsonPath.format(period)

        if period.startswith("Run2"):
            EleES_JsonFile = os.path.join(
                os.environ["ANALYSIS_PATH"],
                EleCorrProducer.EleES_JsonPath.format(period),
            )
            EleID_JsonFile_key = "UL-Electron-ID-SF"
            EleES_JsonFile_key = "UL-EGM_ScaleUnc"
        else:
            EleES_JsonFile = EleCorrProducer.EleES_JsonPath_Run3.format(period)
            EleID_JsonFile_key = "Electron-ID-SF"
            EleES_JsonFile_key = "Scale"
            if period == "2023_Summer23":
                EleES_JsonFile_key = "2023PromptC_ScaleJSON"
            if period == "2023_Summer23BPix":
                EleES_JsonFile_key = "2023PromptD_ScaleJSON"

        if not EleCorrProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "electron.h")
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')
            ROOT.gInterpreter.ProcessLine(
                f'::correction::EleCorrProvider::Initialize("{EleID_JsonFile}", "{EleES_JsonFile}","{EleID_JsonFile_key}","{EleES_JsonFile_key}")'
            )
            EleCorrProducer.year = period.split("_")[0]
            if period.endswith("Summer22"):
                EleCorrProducer.year = period.split("_")[0] + "Re-recoBCD"
            if period.endswith("Summer22EE"):
                EleCorrProducer.year = period.split("_")[0] + "Re-recoE+PromptFG"
            if period.endswith("Summer23"):
                EleCorrProducer.year = period.split("_")[0] + "PromptC"
            if period.endswith("Summer23BPix"):
                EleCorrProducer.year = period.split("_")[0] + "PromptD"
            EleCorrProducer.initialized = True

    def getES(self, df, source_dict):
        for source in EleCorrProducer.energyScaleSources_ele:
            updateSourceDict(source_dict, source, "Ele")
            for scale in getScales(source):
                syst_name = getSystName(source, scale)
                df = df.Define(
                    f"Electron_p4_{syst_name}",
                    f"""::correction::EleCorrProvider::getGlobal().getES(Electron_p4_{nano}, Electron_genMatch,  Electron_seedGain, run,
                Electron_r9,::correction::EleCorrProvider::UncSource::{source}, ::correction::UncScale::{scale})""",
                )
                df = df.Define(
                    f"Electron_p4_{syst_name}_delta",
                    f"Electron_p4_{syst_name} - Electron_p4_{nano}",
                )
        return df, source_dict

    def getIDSF(self, df, lepton_legs, isCentral, return_variations):
        sf_sources = EleCorrProducer.ID_sources
        SF_branches = []
        sf_scales = [up, down] if return_variations else []
        for working_point in EleCorrProducer.working_points:
            for source in sf_sources:
                for scale in [central] + sf_scales:
                    if not isCentral and scale != central:
                        continue
                    # syst_name = getSystName(source, scale)
                    for leg_idx, leg_name in enumerate(lepton_legs):
                        branch_name = (
                            f"weight_{leg_name}_EleSF_{working_point}_{source+scale}"
                        )
                        branch_central = f"""weight_{leg_name}_EleSF_{working_point}_{source+central}"""
                        # print(branch_name)
                        # print(branch_central)
                        df = df.Define(
                            f"{branch_name}_double",
                            f"""({leg_name}_legType == Leg::e && {leg_name}_p4.pt() >= 10 &&  {leg_name}_index >= 0 && (({leg_name}_gen_kind == 1) || ({leg_name}_gen_kind == 3)))  ? ::correction::EleCorrProvider::getGlobal().getID_SF(
                                {leg_name}_p4, "{working_point}",
                                "{EleCorrProducer.year}",::correction::EleCorrProvider::UncSource::{source}, ::correction::UncScale::{scale}) : 1.;""",
                        )  # Changed from leg_name_pt >= 10 to leg_name_p4.pt() >= 10. This is because on the VERY CLOSE edge case where eleES lowers the pt below 10, the code would crash (Seen in file /eos/cms/store/group/phys_higgs/HLepRare/skim_2025_v1/Run3_2023/DYto2Tau_MLL_50_2J_amcatnloFXFX/nano_59.root)

                        if scale != central:
                            branch_name_final = branch_name + "_rel"
                            df = df.Define(
                                branch_name_final,
                                f"static_cast<float>({branch_name}_double/{branch_central})",
                            )
                        else:
                            if source == central:
                                branch_name_final = (
                                    f"""weight_{leg_name}_EleSF_{central}"""
                                )
                            else:
                                branch_name_final = branch_name
                            df = df.Define(
                                branch_name_final,
                                f"static_cast<float>({branch_name}_double)",
                            )

                        SF_branches.append(branch_name_final)
        return df, SF_branches
