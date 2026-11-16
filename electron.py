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
        "eleID": "electron",
        "eleHLT": "",  # electronHlt.json.gz is not published for 2025
        "eleID_highPt": "",
        "eleES_EtDependent": "electronSS_EtDependent",
    },
    "2026_Summer24": {  # placeholder: same as 2025
        "eleID": "electron",
        "eleHLT": "",
        "eleID_highPt": "",
        "eleES_EtDependent": "electronSS_EtDependent",
    },
}


def electron_id_sf_year(campaign):
    year = campaign.split("_")[0]
    if campaign.endswith("Summer22"):
        return year + "Re-recoBCD"
    if campaign.endswith("Summer22EE"):
        return year + "Re-recoE+PromptFG"
    if campaign.endswith("Summer23"):
        return year + "PromptC"
    if campaign.endswith("Summer23BPix"):
        return year + "PromptD"
    if campaign.startswith("2026"):
        # 2026 EGM has no electron.json; 2025 ID SF year is 2025Prompt.
        return "2025Prompt"
    if campaign.endswith("Summer24"):
        return year + "Prompt"
    return year


class EleCorrProducer:
    EleID_JsonPath = "/cvmfs/cms-griddata.cern.ch/cat/metadata/EGM/{folderName}/latest/{filenameID}.json.gz"
    EleES_JsonPath_Run3 = "/cvmfs/cms-griddata.cern.ch/cat/metadata/EGM/{folderName}/latest/{filenameES}.json.gz"
    ID_sources = ["EleID"]
    Reco_source = "EleReco"
    reco_working_point = "Reco"
    working_points = ["wp80iso", "wp80noiso"]
    energyScaleSources_ele = ["EleES", "EleSmear"]

    inputColumns = [
        "gen_kind",
        "legType",
        "p4",
    ]

    def __init__(self, *, campaign, columns, isData=False, reco_sf=False):
        self.isData = isData
        # EGM reconstruction-efficiency SFs (Reco* working points of Electron-ID-SF), opt-in
        self.reco_sf = reco_sf
        file_nameID = ele_files_names[campaign]["eleID"]
        file_nameES = (
            ele_files_names[campaign]["eleES"]
            if "eleES" in ele_files_names[campaign].keys()
            else ele_files_names[campaign]["eleES_EtDependent"]
        )  # in 2024 there is no electronSS...
        # The 2026 EGM folder has no electron.json: the ID SFs are the 2025 ones, as in electron_id_sf_year.
        id_campaign = "2025_Summer24" if campaign == "2026_Summer24" else campaign
        EleID_JsonFile = EleCorrProducer.EleID_JsonPath.format(
            folderName=pog_folder_names["EGM"][id_campaign], filenameID=file_nameID
        )

        EleES_JsonFile = EleCorrProducer.EleES_JsonPath_Run3.format(
            folderName=pog_folder_names["EGM"][campaign], filenameES=file_nameES
        )  # patch since in 2024 there is no eleES without EtDependent
        EleID_JsonFile_key = "Electron-ID-SF"
        EleES_JsonFile_key = "SmearAndSyst"
        # if campaign == "2023_Summer23":
        #     EleES_JsonFile_key = "SmearAndSyst" #"2023PromptC_ScaleJSON"
        # if campaign == "2023_Summer23BPix":
        #     EleES_JsonFile_key = "SmearAndSyst" #"2023PromptD_ScaleJSON"
        # if campaign == "2024_Summer24":
        #     EleES_JsonFile_key = "SmearAndSyst"  # "compound corrections
        declareProviderHeader("electron.h")
        self.provider = CppProvider(
            "correction::EleCorrProvider",
            EleID_JsonFile,
            EleES_JsonFile,
            EleID_JsonFile_key,
            EleES_JsonFile_key,
        )
        self.year = electron_id_sf_year(campaign)

        self.campaign = campaign
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
                if self.isData:
                    expr = f"getESEtDep_data(Electron_p4_{nano}, Electron_seedGain, Electron_superclusterEta, run, Electron_r9)"
                else:
                    # The smearing of MC is seeded per event and electron.
                    expr = f"""getESEtDep_MC(Electron_p4_{nano}, Electron_superclusterEta, run, luminosityBlock, event, Electron_r9,
                ::correction::EleCorrProvider::UncSource::{source}, ::correction::UncScale::{scale})"""
                df = df.Define(
                    f"Electron_p4_{syst_name}",
                    f"{self.provider.ref}->{expr}",
                )
                df = df.Define(
                    f"Electron_p4_{syst_name}_delta",
                    f"Electron_p4_{syst_name} - Electron_p4_{nano}",
                )
        return df, source_dict

    def getIDSF(self, df, lepton_legs, isCentral, return_variations):
        provider = self.provider.ref
        # (working point label, source, C++ call evaluating the SF of one leg)
        sf_defs = [
            (
                working_point,
                source,
                lambda p4, source, scale, wp=working_point: f"""{provider}->getID_SF(
                    {p4}, "{wp}", "{self.year}",
                    ::correction::EleCorrProvider::UncSource::{source},
                    ::correction::UncScale::{scale})""",
            )
            for working_point in EleCorrProducer.working_points
            for source in EleCorrProducer.ID_sources
        ]
        if self.reco_sf:
            # the Reco working point is chosen by the electron pT in getReco_SF
            sf_defs.append(
                (
                    EleCorrProducer.reco_working_point,
                    EleCorrProducer.Reco_source,
                    lambda p4, source, scale: f"""{provider}->getReco_SF(
                    {p4}, "{self.year}",
                    ::correction::EleCorrProvider::UncSource::{source},
                    ::correction::UncScale::{scale})""",
                )
            )
        SF_branches = []
        sf_scales = [up, down] if return_variations else []
        for working_point, source, sf_call in sf_defs:
            for scale in [central] + sf_scales:
                if not isCentral and scale != central:
                    continue
                for leg_name in lepton_legs:
                    branch_name = (
                        f"weight_{leg_name}_EleSF_{working_point}_{source+scale}"
                    )
                    branch_central = (
                        f"weight_{leg_name}_EleSF_{working_point}_{source+central}"
                    )

                    gen_kind = f"{leg_name}_{self.columns['gen_kind']}"
                    legType = f'{leg_name}_{self.columns["legType"]}'
                    p4 = f'{leg_name}_{self.columns["p4"]}'

                    genMatch_bool = f"{gen_kind} == 1 || {gen_kind} == 3"
                    legType = getLegTypeString(df, legType)

                    df = df.Define(
                        f"{branch_name}_double",
                        f"""{legType} == Leg::e && {p4}.pt() >= 10 && ({genMatch_bool})
                                ? {sf_call(p4, source, scale)}
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
                            branch_name_final = f"""weight_{leg_name}_EleSF_{central}"""
                        else:
                            branch_name_final = branch_name
                        df = df.Define(
                            branch_name_final,
                            f"static_cast<float>({branch_name}_double)",
                        )

                    SF_branches.append(branch_name_final)
        return df, SF_branches
