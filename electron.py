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

ele_files_names = {
    "2018_UL": {
        "eleID": "electron",
        "eleES": "electronSS",
    },
    "2017_UL": {
        "eleID": "electron",
        "eleES": "electronSS",
    },
    "2016preVFP_UL": {
        "eleID": "electron",
        "eleES": "electronSS",
    },
    "2016postVFP_UL": {
        "eleID": "electron",
        "eleES": "electronSS",
    },
    "2022_Summer22": {
        "eleID": "electron",
        "eleHLT": "electronHlt",
        "eleID_highPt": "electronID_highPt",
        "eleES_EtDependent": "electronSS_EtDependent",
    },
    "2022_Prompt": {
        "eleID": "electron",
        "eleHLT": "electronHlt",
        "eleID_highPt": "electronID_highPt",
        "eleES_EtDependent": "electronSS_EtDependent",
    },
    "2022_Summer22EE": {
        "eleID": "electron",
        "eleHLT": "electronHlt",
        "eleID_highPt": "electronID_highPt",
        "eleES_EtDependent": "electronSS_EtDependent",
    },
    "2023_Summer23": {
        "eleID": "electron",
        "eleHLT": "electronHlt",
        "eleID_highPt": "electronID_highPt",
        "eleES_EtDependent": "electronSS_EtDependent",
    },
    "2023_Summer23BPix": {
        "eleID": "electron",
        # "eleES": "electronSS",
        "eleHLT": "electronHlt",
        "eleID_highPt": "electronID_highPt",
        "eleES_EtDependent": "electronSS_EtDependent",
    },
    "2024_Summer24": {
        "eleID": "electron",
        "eleHLT": "electronHlt",
        "eleID_highPt": "electronID_highPt",
        "eleES_EtDependent": "electronSS_EtDependent",  # The 2022, 2023, and 2024 Scale and Smearing corrections are provided separately for electrons and photons. In addition, two "flavours" can be used for 2022 and 2023: a standard one, and an eT-dependent one (marked as such in the json file name). The eT-dependent corrections generally yield a better data/MC agreement for objects in the phase space they were derived upon. For 2024, only eT-dependent corrections are available. The Scale and Smearing corrections should not be used for electrons and photons below ~15 GeV and should be used with caution between 15 and 20 GeV, as they were not tuned for this pT range. They might also be ineffective at very high pT (hundreds of GeV).
    },
    "2025_Summer24": {
        "eleID": "",  # currently not available
        "eleHLT": "",  # currently not available
        "eleID_highPt": "",  # currently not available
        "eleES_EtDependent": "electronSS_EtDependent",  # The 2022, 2023, and 2024 Scale and Smearing corrections are provided separately for electrons and photons. In addition, two "flavours" can be used for 2022 and 2023: a standard one, and an eT-dependent one (marked as such in the json file name). The eT-dependent corrections generally yield a better data/MC agreement for objects in the phase space they were derived upon. For 2024, only eT-dependent corrections are available. The Scale and Smearing corrections should not be used for electrons and photons below ~15 GeV and should be used with caution between 15 and 20 GeV, as they were not tuned for this pT range. They might also be ineffective at very high pT (hundreds of GeV).
    },
}


class EleCorrProducer:
    EleID_JsonPath = "/cvmfs/cms-griddata.cern.ch/cat/metadata/EGM/{folderName}/latest/{filenameID}.json.gz"
    EleES_JsonPath = "Corrections/data/EGM/{}/EGM_ScaleUnc.json.gz"
    EleES_JsonPath_Run3 = "/cvmfs/cms-griddata.cern.ch/cat/metadata/EGM/{folderName}/latest/{filenameES}.json.gz"
    initialized = False
    ID_sources = ["EleID"]
    working_points = ["wp80iso", "wp80noiso"]
    energyScaleSources_ele = ["EleES"]
    year = ""

    inputColumns = [
        "gen_kind",
        "legType",
        "p4",
    ]

    def __init__(self, *, period, columns, isData=False):
        self.isData = isData
        file_nameID = ele_files_names[period]["eleID"]
        file_nameES = (
            ele_files_names[period]["eleES"]
            if "eleES" in ele_files_names[period].keys()
            else ele_files_names[period]["eleES_EtDependent"]
        )  # in 2024 there is no electronSS...
        EleID_JsonFile = EleCorrProducer.EleID_JsonPath.format(
            folderName=pog_folder_names["EGM"][period], filenameID=file_nameID
        )

        if period.startswith("Run2"):
            EleES_JsonFile = os.path.join(
                os.environ["ANALYSIS_PATH"],
                EleCorrProducer.EleES_JsonPath.format(period),
            )
            EleID_JsonFile_key = "UL-Electron-ID-SF"
            EleES_JsonFile_key = "UL-EGM_ScaleUnc"
        else:
            EleES_JsonFile = EleCorrProducer.EleES_JsonPath_Run3.format(
                folderName=pog_folder_names["EGM"][period], filenameES=file_nameES
            )  # patch since in 2024 there is no eleES without EtDependent
            EleID_JsonFile_key = "Electron-ID-SF"
            EleES_JsonFile_key = "SmearAndSyst"
            # if period == "2023_Summer23":
            #     EleES_JsonFile_key = "SmearAndSyst" #"2023PromptC_ScaleJSON"
            # if period == "2023_Summer23BPix":
            #     EleES_JsonFile_key = "SmearAndSyst" #"2023PromptD_ScaleJSON"
            # if period == "2024_Summer24":
            #     EleES_JsonFile_key = "SmearAndSyst"  # "compound corrections
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

        self.period = period
        self.columns = {}
        for col in EleCorrProducer.inputColumns:
            self.columns[col] = columns.get(col, col)

    def getES(self, df, source_dict):
        sources = [central]
        if not self.isData:
            sources += EleCorrProducer.energyScaleSources_ele
        for source in sources:
            updateSourceDict(source_dict, source, "Electron")
            for scale in getScales(source):
                syst_name = getSystName(source, scale)
                # if self.period.split("_")[0] == "2024" or self.period.split("_")[0] == "2023" or self.period.split("_")[0] == "2023BPix":
                func_name = "getESEtDep_data" if self.isData else "getESEtDep_MC"
                if (
                    "Electron_superclusterEta" not in df.GetColumnNames()
                ):  # Please note that the correct eta to use to fetch the electron and photon S&S corrections is the supercluster eta (that is Electron(Photon)_superclusterEta in NanoAOD v15). For NanoAOD versions < 15 this variable is not directly available, but one can calculate it as "Electron_eta + Electron_deltaEtaSC". This is unfortunately not the case for photons, for which deltaEtaSC does not exist. In this latter case, Photon_eta can be used instead. Ultimately, the difference between using supercluster era or eta should be minimal.
                    df = df.Define(
                        "Electron_superclusterEta",
                        "RVecF ele_SC_eta; for(size_t i = 0 ; i < Electron_eta.size(); i++) {{ele_SC_eta.push_back(Electron_deltaEtaSC[i]+Electron_eta[i]);}} return ele_SC_eta;",
                    )
                df = df.Define(
                    f"Electron_p4_{syst_name}",
                    f"""::correction::EleCorrProvider::getGlobal().{func_name}(Electron_p4_{nano}, Electron_genMatch, Electron_seedGain, Electron_superclusterEta, run,
                Electron_r9,::correction::EleCorrProvider::UncSource::{source}, ::correction::UncScale::{scale})""",
                )
                # else:
                #     df = df.Define(
                #         f"Electron_p4_{syst_name}",
                #         f"""::correction::EleCorrProvider::getGlobal().getES(Electron_p4_{nano}, Electron_genMatch,  Electron_seedGain, run,
                #     Electron_r9,::correction::EleCorrProvider::UncSource::{source}, ::correction::UncScale::{scale})""",
                #     )
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
                    for leg_name in lepton_legs:
                        branch_name = (
                            f"weight_{leg_name}_EleSF_{working_point}_{source+scale}"
                        )
                        branch_central = f"""weight_{leg_name}_EleSF_{working_point}_{source+central}"""

                        gen_kind = f"{leg_name}_{self.columns['gen_kind']}"
                        legType = f'{leg_name}_{self.columns["legType"]}'
                        p4 = f'{leg_name}_{self.columns["p4"]}'

                        genMatch_bool = f"{gen_kind} == 1 || {gen_kind} == 3"
                        legType = getLegTypeString(df, legType)

                        df = df.Define(
                            f"{branch_name}_double",
                            f"""{legType} == Leg::e && {p4}.pt() >= 10 && ({genMatch_bool})
                                ? ::correction::EleCorrProvider::getGlobal().getID_SF(
                                    {p4}, "{working_point}", "{EleCorrProducer.year}",
                                    ::correction::EleCorrProvider::UncSource::{source},
                                    ::correction::UncScale::{scale})
                                : 1.""",
                        )

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
