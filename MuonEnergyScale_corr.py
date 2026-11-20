import os
import urllib.request
from .CorrectionsCore import *
from FLAF.Common.Utilities import DeclareHeader


class MuonEnergyScaleProducer:
    # jsonPath = "Corrections/data/MUO/MuonScaRe/{}.json.gz"
    # jsonPath = "/cvmfs/cms-griddata.cern.ch/cat/metadata/MUO/{}/latest/muon_scalesmearing.json.gz"
    jsonPath_VXBS = "Corrections/data/MUO/MuonScaRe/{}/muon_scalesmearing_VXBS.json.gz"  # tmp patch because currently VXBS ScaRe are copied from /afs/cern.ch/user/f/ferrico/cmsonly/JSON_VXBS/
    jsonPath = "Corrections/data/MUO/MuonScaRe/{}/muon_scalesmearing.json.gz"  # tmp patch because currently VXBS ScaRe are copied from /afs/cern.ch/user/f/ferrico/cmsonly/JSON/
    uncSources = ["MuScale", "MuRes"]

    def __init__(
        self,
        campaign,
        isData,
        pt_for_ScaRe,
        return_variations=True,
        apply_scare=True,
        apply_fsr_recovery=True,
        id_selection="Muon_looseId",
    ):
        self.campaign = campaign
        self.pt_for_ScaRe = pt_for_ScaRe
        self.apply_scare = apply_scare
        self.apply_fsr_recovery = apply_fsr_recovery
        self.id_selection = id_selection
        jsonFile_path = MuonEnergyScaleProducer.jsonPath.format(
            pog_folder_names["MUO"][campaign]
        )
        jsonFile_path_VXBS = MuonEnergyScaleProducer.jsonPath_VXBS.format(
            pog_folder_names["MUO"][campaign]
        )
        self.isData = isData
        self.return_variations = return_variations
        jsonFile = os.path.join(os.environ["ANALYSIS_PATH"], jsonFile_path)
        jsonFile_VXBS = os.path.join(os.environ["ANALYSIS_PATH"], jsonFile_path_VXBS)
        DeclareHeader(os.environ["ANALYSIS_PATH"] + "/FLAF/include/Utilities.h")
        declareProviderHeader("MuonScaReProvider.h")
        declareProviderHeader("MuonFsrRecoveryProvider.h")
        self.provider = CppProvider(
            "correction::MuonScaReCorrProvider", jsonFile, jsonFile_VXBS
        )

    def getP4Variations(self, df, source_dict):
        sources = [central]
        if not self.isData:
            sources += MuonEnergyScaleProducer.uncSources
        for source in sources:
            updateSourceDict(source_dict, source, "Muon")
            for scale in getScales(source):
                syst_name = getSystName(source, scale)
                for suffix in ["nano", "bsConstrainedPt"]:
                    p4 = f"Muon_p4_{suffix}"
                    scare_branch = f"Muon_p4_{syst_name}_{suffix}"
                    scare_FSR_branch = f"Muon_p4_FSR_{syst_name}_{suffix}"
                    # print(
                    #     f"computing ScaRe on {p4} and defining the scare varied p4 as Muon_p4_{syst_name}"
                    # )
                    use_VXBS = "true" if suffix == "bsConstrainedPt" else "false"
                    if self.apply_scare:
                        if suffix == self.pt_for_ScaRe:
                            scare_branch = f"Muon_p4_{syst_name}"
                            scare_FSR_branch = f"Muon_p4_FSR_{syst_name}"
                        df = df.Define(
                            scare_branch,
                            f"""{self.provider.ref}->getES({self.id_selection}, v_ops::pt({p4}), v_ops::eta({p4}), v_ops::phi({p4}), v_ops::mass({p4}), Muon_charge, Muon_nTrackerLayers, isData, event, luminosityBlock, ::correction::MuonScaReCorrProvider::UncSource::{source}, ::correction::UncScale::{scale}, {use_VXBS})""",
                        )
                        p4 = scare_branch
                        df = df.Define(
                            f"{scare_branch}_delta",
                            f"{scare_branch} - Muon_p4_{nano}",
                        )
                    if self.apply_fsr_recovery:
                        df = df.Define(
                            scare_FSR_branch,
                            f"""::correction::MuonFsrRecoveryProvider::fsr_corrected_p4(v_ops::pt({p4}), v_ops::eta({p4}), v_ops::phi({p4}), v_ops::mass({p4}), Muon_fsrPhotonIdx, FsrPhoton_pt, FsrPhoton_eta, FsrPhoton_phi, FsrPhoton_dROverEt2, FsrPhoton_relIso03, FsrPhoton_electronIdx)""",
                        )
                        df = df.Define(
                            f"{scare_FSR_branch}_delta",
                            f"{scare_FSR_branch} - Muon_p4_{nano}",
                        )

        return df, source_dict
