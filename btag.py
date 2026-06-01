import os
import ROOT
from .CorrectionsCore import *
from FLAF.Common.Utilities import WorkingPointsbTag
import yaml
import json

# https://twiki.cern.ch/twiki/bin/viewauth/CMS/BTagShapeCalibration
# https://twiki.cern.ch/twiki/bin/view/CMS/BTagCalibration
# https://twiki.cern.ch/twiki/bin/view/CMS/BTagSFMethods
# https://github.com/cms-btv-pog
# https://gitlab.cern.ch/cms-nanoAOD/jsonpog-integration/-/tree/master/POG/BTV
# https://twiki.cern.ch/twiki/bin/view/CMS/BtagRecommendation
# https://cms-talk.web.cern.ch/t/ul-b-tagging-sf-update/20209/2
# https://gitlab.cern.ch/cms-btv/btv-json-sf/-/tree/master/data/UL2016preVFP
# https://github.com/hh-italian-group/h-tautau/blob/master/McCorrections/src/BTagWeight.cpp
# https://btv-wiki.docs.cern.ch/PerformanceCalibration/SFUncertaintiesAndCorrelations/working-point-based-sfs-fixedwp-sfs
# https://btv-wiki.docs.cern.ch/PerformanceCalibration/fixedWPSFRecommendations/


# shouldcorrectly process source name containing two underscores (e.g. JES_Absolute_2022)
# will correctly cut out second word and check if its in the list
def IsInJESList(src_name, jes_list):
    split_src_name = src_name.split("_")
    if len(split_src_name) == 1:
        return src_name in jes_list
    elif len(split_src_name) > 1:
        to_check = split_src_name[1] + "_"
        return to_check in jes_list
    else:
        raise RuntimeError(f"Cannot parse source name: {src_name}")


class bTagCorrProducer:
    jsonPath = "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/{}/latest/btagging.json.gz"
    alternative_jsonPath = "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/{}/add_2025_b_and_c_WPs/btagging.json.gz"
    bTagEff_JsonPath = "Corrections/data/BTV/{}/btagEff.root"
    initialized = False
    uncSource_bTagWP = [
        "btagSFbc_uncorrelated",
        "btagSFlight_uncorrelated",
        "btagSFbc_correlated",
        "btagSFlight_correlated",
    ]
    uncSources_bTagShape_jes = [
        "Total",
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
    uncSources_bTagShape_norm = [
        "lf",
        "hf",
        "lfstats1",
        "lfstats2",
        "hfstats1",
        "hfstats2",
        "cferr1",
        "cferr2",
    ]

    tagger_to_brag_branch = {
        "particleNet": "PNetB",
        "deepJet": "DeepFlavB",
        "UParTAK4": "UParTAK4B",
    }

    # important note: From the 2024 campaign onwards, only the UParTAK4 tagger is supported, and only json files are provided.
    def __init__(
        self,
        *,
        period,
        jetCollection,
        loadEfficiency=False,
        tagger="particleNet",
        useSplitJes=False,
        wantShape=False,
    ):
        print(f"tagger={tagger}")
        self.tagger = tagger
        self.btag_branch = bTagCorrProducer.tagger_to_brag_branch[tagger]
        self.jetCollection = jetCollection
        self.useSplitJes = useSplitJes
        jsonFile = bTagCorrProducer.jsonPath.format(
            pog_folder_names["BTV"][period]
        )  # for 2025 latest is not available, but files are in this folder available: add_2025_b_and_c_WPs (?) bah
        if not os.path.exists(jsonFile):
            jsonFile = bTagCorrProducer.alternative_jsonPath.format(
                pog_folder_names["BTV"][period]
            )
        jsonFile_eff = os.path.join(
            os.environ["ANALYSIS_PATH"],
            bTagCorrProducer.bTagEff_JsonPath.format(period),
        )
        if not loadEfficiency:
            jsonFile_eff = ""
        if not bTagCorrProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "btag.h")
            headershape_path = os.path.join(headers_dir, "btagShape.h")
            ROOT.gInterpreter.Declare(f'#include "{headershape_path}"')
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')

            ROOT.gInterpreter.ProcessLineSynch(
                f'::correction::bTagCorrProvider::Initialize("{jsonFile}", "{jsonFile_eff}", "{self.tagger}")'
            )
            # ROOT.correction.bTagCorrProvider.Initialize(
            #     jsonFile, jsonFile_eff, self.tagger
            # )
            ROOT.correction.bTagCorrProvider.getGlobal()
            wantShape_str = "false"
            if wantShape:
                wantShape_str = "true"
            ROOT.gInterpreter.ProcessLineSynch(
                f"""::correction::bTagShapeCorrProvider::Initialize("{jsonFile}", "{periods[period]}", "{self.tagger}", {wantShape_str})"""
            )
            # ROOT.correction.bTagShapeCorrProvider.Initialize(
            #     jsonFile, periods[period], self.tagger
            # )
            ROOT.correction.bTagShapeCorrProvider.getGlobal()

            bTagCorrProducer.initialized = True

    def getWPValues(self):
        wp_values = {}
        for wp in WorkingPointsbTag:
            root_wp = getattr(ROOT.WorkingPointsbTag, wp.name)
            wp_values[wp] = ROOT.correction.bTagCorrProvider.getGlobal().getWPvalue(
                root_wp
            )
        return wp_values

    def getWPid(self, df, jetCollection=None):
        jetCollection = jetCollection or self.jetCollection
        df = df.Define(
            f"{jetCollection}_idbtag{self.btag_branch}",
            f"::correction::bTagCorrProvider::getGlobal().getWPBranch({jetCollection}_btag{self.btag_branch})",
        )
        return df

    def getBTagWPSF(self, df, return_variations=True, isCentral=True):
        sf_sources = bTagCorrProducer.uncSource_bTagWP
        SF_branches = []
        sf_scales = [up, down] if return_variations else []
        for source in [central] + sf_sources:
            for scale in [central] + sf_scales:
                if source == central and scale != central:
                    continue
                if not isCentral and scale != central:
                    continue
                # syst_name = source+scale if source != central else 'Central'
                syst_name = source + scale
                for wp in WorkingPointsbTag:
                    branch_name = f"weight_bTagSF_{wp.name}_{syst_name}"
                    # print(branch_name)
                    branch_central = f"""weight_bTagSF_{wp.name}_{source+central}"""
                    # branch_central = f"""weight_bTagSF_{wp.name}_{getSystName(central, central)}"""
                    p4 = f"{self.jetCollection}_p4"
                    hadronFlavour = f"{self.jetCollection}_hadronFlavour"
                    btagScore = f"{self.jetCollection}_btag{self.btag_branch}"
                    df = df.Define(
                        f"{branch_name}_double",
                        f""" ::correction::bTagCorrProvider::getGlobal().getSF(
                                {p4}, {hadronFlavour}, {btagScore}, WorkingPointsbTag::{wp.name},
                                ::correction::bTagCorrProvider::UncSource::{source}, ::correction::UncScale::{scale}) """,
                    )
                    if scale != central:
                        branch_name_final = branch_name + "_rel"
                        df = df.Define(
                            branch_name_final,
                            f"static_cast<float>({branch_name}_double/{branch_central})",
                        )
                    else:
                        if source == central:
                            branch_name_final = f"""weight_bTagSF_{wp.name}_{central}"""
                        else:
                            branch_name_final = branch_name
                        df = df.Define(
                            branch_name_final,
                            f"static_cast<float>({branch_name}_double)",
                        )
                    SF_branches.append(branch_name_final)
        return df, SF_branches

    def getBTagShapeSF(self, df, src_name, scale_name, isCentral, return_variations):
        sf_sources_norm = bTagCorrProducer.uncSources_bTagShape_norm
        sf_scales = [up, down] if return_variations else []
        SF_branches = []
        src_list = []
        scale_list = []
        force_name_as_central = False

        # here list must be corrected
        if isCentral:
            src_list = [central]
            scale_list = [central]
            if return_variations:
                src_list += bTagCorrProducer.uncSources_bTagShape_norm
                scale_list += sf_scales
        else:
            if IsInJESList(src_name, bTagCorrProducer.uncSources_bTagShape_jes):
                src_list = [
                    f"jes{src_name}"
                ]  # Right now, src name was 'Total', but should be 'jesTotal'
                scale_list = [scale_name]
                force_name_as_central = True
            else:
                src_list = [central]
                scale_list = [central]

        print(f"src_name={src_name}, scale_name={scale_name}")
        print(f"\tsrc_list={src_list}")
        print(f"\tscale_list={scale_list}")

        for source in src_list:
            for scale in scale_list:
                if (source == central and scale != central) or (
                    source != central and scale == central
                ):
                    continue
                syst_name = getSystName(
                    source, scale
                )  # if source != central else 'Central'
                branch_name = f"weight_bTagShape_{syst_name}"
                branch_central = f"weight_bTagShape_{central}"

                p4 = f"{self.jetCollection}_p4"
                hadronFlavour = f"{self.jetCollection}_hadronFlavour"
                btagScore = f"{self.jetCollection}_btag{self.btag_branch}"

                df = df.Define(
                    f"{branch_name}_double",
                    f"""::correction::bTagShapeCorrProvider::getGlobal().getBTagShapeSF(
                    {p4}, {hadronFlavour}, {btagScore},
                    ::correction::bTagShapeCorrProvider::UncSource::{source},
                    ::correction::UncScale::{scale}
                    ) """,
                )

                if (
                    scale != central and not force_name_as_central
                ):  # If jes unc we do not want relative
                    branch_name_final = branch_name + "_rel"
                    df = df.Define(
                        branch_name_final,
                        f"static_cast<float>({branch_name}_double/{branch_central})",
                    )
                else:
                    if (
                        source == central or force_name_as_central
                    ):  # If jes unc, we want to give the fake name 'weight_btagShape_Central' but this is not actually central, it uses the up/down_jes keys in btagShape
                        branch_name_final = f"""weight_bTagShape_{central}"""
                    else:
                        branch_name_final = branch_name
                    df = df.Define(
                        branch_name_final, f"static_cast<float>({branch_name}_double)"
                    )
                SF_branches.append(branch_name_final)
        return df, SF_branches


ROOT.gInterpreter.Declare(r"""
#include <map>
#include <string>

struct BTagMapApplier {
  std::map<std::string,float> corr;

  float operator()(float w, const std::string &key) const {
    auto it = corr.find(key);
    const float r = (it != corr.end()) ? it->second : 1.0;
    return w * r;
  }
};
""")


class btagShapeWeightCorrector:
    def __init__(self, *, norm_file_path, bins):
        self.norm_file_path = norm_file_path
        with open(norm_file_path, "r") as norm_file:
            self.shape_weight_corr_dict = json.load(norm_file)
        self.bins = bins
        self._appliers = []

    def _define_key_column(self, df, keycol, syst):
        # key = norm_<syst>_<bin_name>
        pieces = []
        for bin_name, cut in self.bins.items():
            pieces.append(f'({cut}) ? std::string("norm_{syst}_{bin_name}") : ')
        key_expr = "".join(pieces) + 'std::string("__default__")'

        cols = set(df.GetColumnNames())
        return (
            df.Redefine(keycol, key_expr)
            if keycol in cols
            else df.Define(keycol, key_expr)
        )

    def UpdateBtagWeight(self, *, df, unc_src, unc_scale, sf_branches):
        unc_src_scale = f"{unc_src}_{unc_scale}" if unc_src != unc_scale else unc_src
        if unc_src_scale not in self.shape_weight_corr_dict:
            raise KeyError(
                f"Key `{unc_src_scale}` not found in `{self.norm_file_path}`."
            )

        # btag branches have format weight_bTagShape_{syst}_rel
        # need to extract syst => need token #2
        systs = [b.split("_")[2] for b in sf_branches]

        applier = ROOT.BTagMapApplier()
        applier.corr["__default__"] = 1.0
        for k, v in self.shape_weight_corr_dict[unc_src_scale].items():
            applier.corr[k] = float(v)
        self._appliers.append(applier)

        # only correct weights for uncertainty variations
        # branches are defined as relative, i.e. branch/central
        # to correct, need to first multiply by central
        # after this loop _rel branches will have the full value
        # => will have to divide them by central after it is corrected
        for syst in systs:
            if syst == "Central":
                continue
            keycol = f"btag_shape_norm_key_{syst}"
            df = self._define_key_column(df, keycol, syst)

            branch_name = f"weight_bTagShape_{syst}_rel"
            # rel := rel * central * corr(norm_<syst>_<bin>)
            df = df.Redefine(
                branch_name, f"(float){branch_name} * weight_bTagShape_Central"
            ).Redefine(branch_name, applier, [branch_name, keycol])

        # correct central separately after everything else was corrected and central is not needed
        df = self._define_key_column(df, "btag_shape_norm_key_Central", "Central")
        df = df.Redefine(
            "weight_bTagShape_Central",
            applier,
            ["weight_bTagShape_Central", "btag_shape_norm_key_Central"],
        )

        # redefine all _rel branches by dividing them by updated Central to make them contain relative value
        for syst in systs:
            if syst == "Central":
                continue
            branch_name = f"weight_bTagShape_{syst}_rel"
            df = df.Redefine(
                branch_name, f"(float){branch_name} / weight_bTagShape_Central"
            )

        return df
