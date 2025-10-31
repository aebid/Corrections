import os
import ROOT
from .CorrectionsCore import *

# https://twiki.cern.ch/twiki/bin/viewauth/CMS/SWGuideMuonSelection
# https://gitlab.cern.ch/cms-nanoAOD/jsonpog-integration/-/tree/master/POG/MUO
# note: at the beginning of february 2024, the names have been changed to muon_Z.json.gz and muon_HighPt.json.gz for high pT muons
# https://twiki.cern.ch/twiki/bin/view/CMS/MuonUL2018
# https://twiki.cern.ch/twiki/bin/view/CMS/MuonUL2017
# https://twiki.cern.ch/twiki/bin/view/CMS/MuonUL2016


class JetVetoMapProvider:
    JME_vetoMap_JsonPath = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/{}/jetvetomaps.json.gz"
    initialized = False

    # jetvetomap_names = { "2022_Summer22": ["Summer22_23Sep2023","Summer22_23Sep2023_RunCD_v1"], #period: [filename, entryname]
    #                 "2022_Summer22EE": ["Summer22EE_23Sep2023","Summer22EE_23Sep2023_RunEFG_v1"],
    #                 "2023_Summer23BPix": ["Summer23BPixPrompt23","Summer23BPixPrompt23_RunD_v1"],
    #                 "2023_Summer23": ["Summer23Prompt23","Summer23Prompt23_RunC_v1"]}
    jetvetomap_names = {
        "2022_Summer22": "Summer22_23Sep2023_RunCD_V1",  # period: , entryname
        "2022_Summer22EE": "Summer22EE_23Sep2023_RunEFG_V1",
        "2023_Summer23BPix": "Summer23BPixPrompt23_RunD_V1",
        "2023_Summer23": "Summer23Prompt23_RunC_V1",
    }

    def __init__(self, era):
        period = period_names[era]
        entry_name = JetVetoMapProvider.jetvetomap_names[period]
        JME_vetoMap_JsonFile = os.path.join(
            os.environ["ANALYSIS_PATH"],
            JetVetoMapProvider.JME_vetoMap_JsonPath.format(period),
        )
        if not JetVetoMapProvider.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "JetVetoMap.h")
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')
            ROOT.gInterpreter.ProcessLine(
                f'::correction::JetVetoMapProvider::Initialize("{JME_vetoMap_JsonFile}", "{entry_name}")'
            )
            JetVetoMapProvider.period = period
            JetVetoMapProvider.initialized = True

    def GetJetVetoMap(self, df):
        # jet pT > 15 GeV, tight jet ID, PU jet ID for CHS jets with pT < 50 GeV,  jet EM fraction (charged + neutral) < 0.9
        df = df.Define(
            f"Jet_isInsideVetoRegion",
            f"""::correction::JetVetoMapProvider::getGlobal().GetJetVetoMapValues(Jet_p4)""",
        )
        return df
