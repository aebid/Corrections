import os
import urllib.request
import ROOT
from .CorrectionsCore import *
from FLAF.Common.Utilities import DeclareHeader


class MuonEnergyScaleProducer:
    initialized = False
    # jsonPath = "Corrections/data/MUO/MuonScaRe/{}.json.gz"
    # jsonPath = "/cvmfs/cms-griddata.cern.ch/cat/metadata/MUO/{}/latest/muon_scalesmearing.json.gz"
    jsonPath = "Corrections/data/MUO/MuonScaRe/{}/muon_scalesmearing.json.gz"  # tmp patch because currently VXBS ScaRe are copied from /afs/cern.ch/user/f/ferrico/cmsonly/MUON_JSON_VXBS/
    initialized = False
    uncSources = ["ScaRe"]

    period = None

    def __init__(
        self,
        period,
        isData,
        pt_for_ScaRe,
        return_variations=True,
        apply_scare=True,
        apply_fsr_recovery=True,
    ):
        self.period = period
        self.pt_for_ScaRe = pt_for_ScaRe
        self.apply_scare = apply_scare
        self.apply_fsr_recovery = apply_fsr_recovery
        jsonFile_path = MuonEnergyScaleProducer.jsonPath.format(
            pog_folder_names["MUO"][period]
        )
        self.isData = isData
        self.return_variations = return_variations
        jsonFile = os.path.join(os.environ["ANALYSIS_PATH"], jsonFile_path)
        if not MuonEnergyScaleProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            DeclareHeader(os.environ["ANALYSIS_PATH"] + "/FLAF/include/Utilities.h")
            header_path = os.path.join(headers_dir, "MuonScaReProvider.h")
            ROOT.gROOT.ProcessLine(f'#include "{header_path}"')
            ROOT.gInterpreter.ProcessLine(
                f'::correction::MuonScaReCorrProvider::Initialize("{jsonFile}")'
            )
            header_path = os.path.join(headers_dir, "MuonFsrRecoveryProvider.h")
            ROOT.gROOT.ProcessLine(f'#include "{header_path}"')
            MuonEnergyScaleProducer.initialized = True

    def getP4Variations(self, df, source_dict):
        sources = [central]
        if not self.isData:
            sources += MuonEnergyScaleProducer.uncSources
        for source in sources:
            updateSourceDict(source_dict, source, "Muon")
            for scale in getScales(source):
                syst_name = getSystName(source, scale)
                p4 = f"Muon_p4_{self.pt_for_ScaRe}"
                print(
                    f"computing ScaRe on {p4} and defining the scare varied p4 as Muon_p4_{syst_name}"
                )
                scare_branch = f"Muon_p4_scare_{syst_name}"
                if not self.apply_fsr_recovery:
                    # output to the main branch
                    scare_branch = f"Muon_p4_{syst_name}"
                if self.apply_scare:
                    df = df.Define(
                        scare_branch,
                        f"""::correction::MuonScaReCorrProvider::getGlobal().getES(v_ops::pt({p4}), v_ops::eta({p4}), v_ops::phi({p4}), v_ops::mass({p4}), Muon_charge, Muon_nTrackerLayers, isData, event, luminosityBlock, ::correction::MuonScaReCorrProvider::UncSource::{source}, ::correction::UncScale::{scale})""",
                    )
                    p4 = f"Muon_p4_scare_{syst_name}"
                if self.apply_fsr_recovery:
                    df = df.Define(
                        f"Muon_p4_{syst_name}",
                        f"""::correction::MuonFsrRecoveryProvider::fsr_corrected_p4(v_ops::pt({p4}), v_ops::eta({p4}), v_ops::phi({p4}), v_ops::mass({p4}), Muon_fsrPhotonIdx, FsrPhoton_pt, FsrPhoton_eta, FsrPhoton_phi, FsrPhoton_dROverEt2, FsrPhoton_relIso03, FsrPhoton_electronIdx)""",
                    )
                df = df.Define(
                    f"Muon_p4_{syst_name}_delta",
                    f"Muon_p4_{syst_name} - Muon_p4_{nano}",
                )
        return df, source_dict

    def getP4VariationsForLegs(self, df):
        sources = [central]
        if not self.isData:
            sources += MuonEnergyScaleProducer.uncSources
        for source in sources:
            for scale in getScales(source):
                syst_name = getSystName(source, scale)
                for leg_idx in [1, 2]:
                    mu_pt = f"mu{leg_idx}_{self.pt_for_ScaRe}"
                    scare_branch = f"mu{leg_idx}_p4_scare_{syst_name}"
                    if not self.apply_fsr_recovery:
                        scare_branch = f"mu{leg_idx}_p4_{syst_name}"
                    if self.apply_scare:
                        df = df.Define(
                            scare_branch,
                            f"""::correction::MuonScaReCorrProvider::getGlobal().getES({mu_pt}, mu{leg_idx}_eta, mu{leg_idx}_phi, mu{leg_idx}_mass, mu{leg_idx}_charge, mu{leg_idx}_nTrackerLayers, isData, event, luminosityBlock, ::correction::MuonScaReCorrProvider::UncSource::{source}, ::correction::UncScale::{scale})""",
                        )
                        mu_pt = f"mu{leg_idx}_{self.pt_for_ScaRe}"
                    if self.apply_fsr_recovery:
                        df = df.Define(
                            f"mu{leg_idx}_p4_{syst_name}",
                            f"""::correction::MuonFsrRecoveryProvider::fsr_corrected_p4({mu_pt}, mu{leg_idx}_eta, mu{leg_idx}_phi, mu{leg_idx}_mass, mu{leg_idx}_fsrPhotonIdx, FsrPhoton_pt, FsrPhoton_eta, FsrPhoton_phi, FsrPhoton_dROverEt2, FsrPhoton_relIso03, FsrPhoton_electronIdx)""",
                        )
        return df
