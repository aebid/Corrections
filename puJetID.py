import os
import ROOT
from .CorrectionsCore import *

# https://twiki.cern.ch/twiki/bin/viewauth/CMS/PileupJetIDUL
# https://indico.cern.ch/event/1118864/contributions/4734428/attachments/2388825/4120443/Tanmay_Slide_February_22_2022_Modified.pdf
# https://twiki.cern.ch/twiki/bin/viewauth/CMS/PileupJetIDUL#Data_MC_Efficiency_Scale_Factors


class puJetIDCorrProducer:
    PUJetID_JsonPath = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/{}/jmar.json.gz"
    initialized = False
    puJetID_SF_Sources = ["PUJetID_eff"]
    period = None
    puJetID = "L"

    def __init__(self, period):
        jsonFile_eff = os.path.join(
            os.environ["ANALYSIS_PATH"],
            puJetIDCorrProducer.PUJetID_JsonPath.format(period),
        )
        if not puJetIDCorrProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "puJetID.h")
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')
            ROOT.gInterpreter.ProcessLine(
                f'::correction::PUJetIDCorrProvider::Initialize("{jsonFile_eff}")'
            )
            puJetIDCorrProducer.period = period
            puJetIDCorrProducer.initialized = True

    def getPUJetIDEff(self, df, isCentral=True, return_variations=True):
        puJetID_SF_branches = []
        for source in [central] + puJetIDCorrProducer.puJetID_SF_Sources:
            for scale in getScales(source):
                if not isCentral and scale != central:
                    continue
                if not return_variations and scale != central:
                    continue
                syst_name = getSystName(source, scale)
                if source == central:
                    syst_name = "PUJetID_Central"
                branch_name_jets = f"weight_Jet_{syst_name}_"
                branch_central_jets = f"""weight_Jet_PUJetID_Central_"""
                df = df.Define(
                    f"{branch_name_jets}",
                    f"""::correction::PUJetIDCorrProvider::getGlobal().getPUJetID_eff(
                                        Jet_pt, Jet_eta, "{puJetIDCorrProducer.puJetID}",
                                        ::correction::PUJetIDCorrProvider::UncSource::{source}, ::correction::UncScale::{scale});""",
                )
                if source != central:
                    branch_name_jet_rel = f"{branch_name_jets}rel_tmp"
                    df = df.Define(
                        branch_name_jet_rel,
                        f"""RVecF weights_rel({branch_name_jets}.size(),1); for(size_t weight_idx = 0; weight_idx<{branch_name_jets}.size(); weight_idx++)
                                {{
                                weights_rel[weight_idx] = {branch_name_jets}[weight_idx]/{branch_central_jets}[weight_idx];
                                }}
                                return weights_rel;""",
                    )
                else:
                    branch_name_jet_rel = f"{branch_central_jets}tmp"
                    df = df.Define(branch_name_jet_rel, branch_central_jets)
                puJetID_SF_branches.append(branch_name_jet_rel)
        return df, puJetID_SF_branches
