import os
import re
import itertools

from .CorrectionsCore import *
from FLAF.RunKit.run_tools import ps_call
from FLAF.Common.shared_mc import shared_mc_in_era_expr, shared_mc_split


def _ana_caches_with_denom_key(ana_caches, key):
    """Expose ``ana_caches[*][key]`` as ``denominator`` for defineDenominator."""
    if key == "denominator":
        return ana_caches
    remapped = {}
    for ds_name, cache in ana_caches.items():
        if key not in cache:
            raise RuntimeError(
                f"AnaCache for '{ds_name}' has no '{key}'. Re-run AnaTupleFileTask "
                "so both the full and in-era denominators are stored."
            )
        remapped[ds_name] = dict(cache)
        remapped[ds_name]["denominator"] = cache[key]
    return remapped


def findLibLocation(lib_name, first_guess=None):
    paths_to_check = []
    if first_guess is not None:
        paths_to_check.append(first_guess)
    other_paths = os.environ.get("LD_LIBRARY_PATH", "").split(":")
    paths_to_check.extend(other_paths)
    full_lib_name = f"lib{lib_name}.so"
    for path in paths_to_check:
        lib_path = os.path.join(path, full_lib_name)
        if os.path.exists(lib_path):
            return lib_path
    raise RuntimeError(f"Library {lib_name} not found.")


class Corrections:
    _global_instance = None
    _corr_lib_loaded = False

    @staticmethod
    def initializeGlobal(load_corr_lib=False, **kwargs):
        if Corrections._global_instance is not None:
            print(
                f"WARNING: Global instance of Corrections was already initialized. Overwriting it.",
                file=sys.stderr,
            )

        if load_corr_lib and not Corrections._corr_lib_loaded:
            returncode, output, err = ps_call(
                ["correction", "config", "--cflags", "--ldflags"],
                catch_stdout=True,
                decode=True,
                verbose=0,
            )
            params = output.split(" ")
            lib_path = None
            for param in params:
                if param.startswith("-I"):
                    ROOT.gInterpreter.AddIncludePath(param[2:].strip())
                elif param.startswith("-L"):
                    lib_path = param[2:].strip()
                elif param.startswith("-l"):
                    lib_name = param[2:].strip()

            # ROOT.gInterpreter.AddIncludePath(os.environ['FLAF_ENVIRONMENT_PATH']+"/include")
            corr_lib = findLibLocation(lib_name, lib_path)
            ROOT.gSystem.Load(corr_lib)
            Corrections._corr_lib_loaded = True

        Corrections._global_instance = Corrections(**kwargs)

    @staticmethod
    def getGlobal():
        if Corrections._global_instance is None:
            raise RuntimeError("Global instance is not initialized")
        return Corrections._global_instance

    def __init__(
        self,
        *,
        setup,
        stage,
        dataset_name,
        dataset_cfg,
        process_name,
        process_cfg,
        processors,
        isData,
        trigger_class,
        aggregated_caches=None,
    ):
        self.global_params = setup.global_params
        # {producer -> localized aggregated-cache file path}, provided by the task layer
        # (law localizes the AnalysisCacheAggregationTask output). Used for version-dependent
        # inputs such as the BtagShape normalization, instead of reconstructing the path.
        self.aggregated_caches = aggregated_caches or {}
        self.dataset_name = dataset_name
        self.dataset_cfg = dataset_cfg
        self.process_name = process_name
        self.process_cfg = process_cfg
        self.isData = isData
        self.trigger_dict = trigger_class.trigger_dict if trigger_class else {}

        self.period = self.global_params["era"]
        self.stage = stage
        self.law_run_version = setup.law_run_version

        self.to_apply = {}
        correction_origins = {}
        for cfg_name, cfg in [
            ("dataset", dataset_cfg),
            ("process", process_cfg),
            ("global", self.global_params),
        ]:
            if not cfg:
                continue
            for corr_name, corr_params in cfg.get("corrections", {}).items():
                if "stage" in corr_params and "stages" in corr_params:
                    raise RuntimeError(
                        f"correction {corr_name} in {cfg_name} has both 'stage' and 'stages' defined. Please use only one of them."
                    )
                corr_stages = corr_params.get("stages", [])
                if "stage" in corr_params:
                    corr_stages.append(corr_params["stage"])
                if stage not in corr_stages:
                    continue
                if corr_name not in self.to_apply:
                    if (
                        "processes" in corr_params
                        and process_name not in corr_params["processes"]
                    ):
                        continue
                    self.to_apply[corr_name] = corr_params
                    correction_origins[corr_name] = cfg_name
                else:
                    print(
                        f"Warning: correction {corr_name} is already defined in {correction_origins[corr_name]}. Skipping definition from {cfg_name}",
                        file=sys.stderr,
                    )

        if len(self.to_apply) > 0:
            print(
                f"Corrections to apply: {', '.join(self.to_apply.keys())}",
                file=sys.stderr,
            )

        self.all_processors = processors

        if "xs" in self.to_apply or "base" in self.to_apply:
            self.xs_denom_processors = {}
            self.xs_print_history = set()
            self.denom_print_history = set()

            for p_name, proc in self.all_processors.items():
                has_xs_fn = hasattr(proc, "onAnaTuple_defineCrossSection")
                has_denom_fn = hasattr(proc, "onAnaTuple_defineDenominator")
                has_default_denom_attr = hasattr(proc, "default_denom_processor")
                if not (has_xs_fn or has_denom_fn or has_default_denom_attr):
                    continue
                if not (has_xs_fn and has_denom_fn and has_default_denom_attr):
                    raise RuntimeError(
                        f"Processor {p_name} must implementonAnaTuple_defineCrossSection, onAnaTuple_defineDenominator and default_denom_processor, or neither of them."
                    )
                is_default = proc.default_denom_processor
                suffix = "" if is_default else f"_{p_name}"
                if suffix in self.xs_denom_processors:
                    raise RuntimeError(
                        f"Multiple processors have the same suffix {suffix} for cross section and denominator definition. This is not supported."
                    )
                self.xs_denom_processors[suffix] = p_name
            if len(self.xs_denom_processors) > 0 and "" not in self.xs_denom_processors:
                raise RuntimeError(
                    "No processor is set as default for cross section and denominator definition."
                )

        self.xs_db_ = None
        self.tau_ = None
        self.met_ = None
        self.trg_ = None
        self.btag_ = None
        self.pu_ = None
        self.parton_shower_ = None
        self.pdf_ = None
        self.dy_hhbbtautau_ = None
        self.dy_hhbbww_ = None
        self.mu_ = None
        self.muScaRe_ = None
        self.ele_ = None
        self.puJetID_ = None
        self.jet_ = None
        self.fatjet_ = None
        self.Vpt_ = None
        self.JetVetoMap_ = None
        self.btag_shape_norm_ = None
        self.bosonicRecoil_ = None

    @property
    def xs_db(self):
        if self.xs_db_ is None:
            from FLAF.Common.CrossSectionDB import CrossSectionDB

            self.xs_db_ = CrossSectionDB.Load(
                os.environ["ANALYSIS_PATH"],
                self.global_params["crossSectionsFile"],
            )
        return self.xs_db_

    @property
    def pu(self):
        if self.pu_ is None:
            from .pu import puWeightProducer

            self.pu_ = puWeightProducer(period=period_names[self.period])
        return self.pu_

    @property
    def parton_shower(self):
        if self.parton_shower_ is None:
            from .parton_shower import psWeightProducer

            self.parton_shower_ = psWeightProducer(
                branch=self.to_apply.get("parton_shower", {}).get("branch", "PSWeight")
            )
        return self.parton_shower_

    @property
    def pdf(self):
        if self.pdf_ is None:
            from .pdf import pdfWeightProducer

            cfg = self.to_apply.get("pdf", {})
            self.pdf_ = pdfWeightProducer(
                branch=cfg.get("branch", "LHEPdfWeight"),
                mode=cfg.get("mode", "replicas"),
                first=cfg.get("first", 1),
                n=cfg.get("n", 100),
            )
        return self.pdf_

    @property
    def dy_hhbbtautau(self):
        if self.dy_hhbbtautau_ is None:
            from .DY_hhbbtautau import DYbbtautauCorrProducer

            njets_branch = self.to_apply.get("dy_hhbbtautau", {}).get(
                "njets_branch", "nJet"
            )
            ntags_branch = self.to_apply.get("dy_hhbbtautau", {}).get(
                "ntags_branch", "nBJets"
            )
            pt_ll_gen = self.to_apply.get("dy_hhbbtautau", {}).get(
                "pt_ll_gen", "pt_ll_gen"
            )
            self.dy_hhbbtautau_ = DYbbtautauCorrProducer(
                era=self.period,
                njets_branch=njets_branch,
                ntags_branch=ntags_branch,
                pt_ll_gen=pt_ll_gen,
            )
        return self.dy_hhbbtautau_

    @property
    def dy_hhbbww(self):
        if self.dy_hhbbww_ is None:
            from .DY_hhbbww import DYbbwwCorrProducer

            njets_branch = self.to_apply.get("dy_hhbbww", {}).get(
                "njets_branch", "nJet"
            )
            pt_ll = self.to_apply.get("dy_hhbbww", {}).get("pt_ll", "pt_lep1_lep2")
            self.dy_hhbbww_ = DYbbwwCorrProducer(
                era=self.period,
                njets_branch=njets_branch,
                pt_ll=pt_ll,
            )
        return self.dy_hhbbww_

    @property
    def Vpt(self):
        if self.Vpt_ is None:
            from .Vpt import VptCorrProducer

            self.Vpt_ = VptCorrProducer(self.to_apply["Vpt"]["type"], self.period)
        return self.Vpt_

    @property
    def JetVetoMap(self):
        if self.JetVetoMap_ is None:
            from .JetVetoMap import JetVetoMapProvider

            self.JetVetoMap_ = JetVetoMapProvider(self.period)
        return self.JetVetoMap_

    @property
    def tau(self):
        if self.tau_ is None:
            from .tau import TauCorrProducer

            self.tau_ = TauCorrProducer(
                period=self.period,
                config=self.global_params,
                columns=self.to_apply.get("tauID", {}).get("columns", {}),
            )
        return self.tau_

    @property
    def jet(self):
        if self.jet_ is None:
            from .jet import JetCorrProducer

            self.jet_ = JetCorrProducer(
                period_names[self.period], self.isData, self.dataset_name
            )
        return self.jet_

    @property
    def fatjet(self):
        if self.fatjet_ is None:
            from .fatjet import FatJetCorrProducer

            self.fatjet_ = FatJetCorrProducer(
                period=period_names[self.period],
                ana=self.to_apply.get("fatjet", {}).get("ana", ""),
                tagger=self.to_apply.get("fatjet", {}).get("tagger", ""),
                fatjetName=self.to_apply.get("fatjet", {}).get("fatJetName", ""),
                isData=self.isData,
            )
        return self.fatjet_

    @property
    def btag(self):
        if self.btag_ is None:
            from .btag import bTagCorrProducer

            params = self.to_apply["btag"]
            self.btag_ = bTagCorrProducer(
                period=period_names[self.period],
                jetCollection=params["jetCollection"],
                tagger=params["tagger"],
                loadEfficiency=params.get("loadEfficiency", False),
                useSplitJes=params.get("useSplitJes", False),
                wantShape=params.get("wantShape", True),
            )
        return self.btag_

    @property
    def met(self):
        if self.met_ is None:
            from .met import METCorrProducer

            self.met_ = METCorrProducer()
        return self.met_

    @property
    def mu(self):
        if self.mu_ is None:
            from .mu import MuCorrProducer

            self.mu_ = MuCorrProducer(
                era=self.period, columns=self.to_apply["mu"].get("columns", {})
            )
        return self.mu_

    @property
    def muScaRe(self):
        if self.muScaRe_ is None:
            from .MuonEnergyScale_corr import MuonEnergyScaleProducer

            apply_scare = (
                self.to_apply["muScaRe"].get("scare_enabled", {}).get(self.stage, True)
            )
            apply_FSR = (
                self.to_apply["muScaRe"].get("fsr_enabled", {}).get(self.stage, False)
            )
            id_selection = self.to_apply["muScaRe"].get("id_selection", "Muon_looseId")
            self.muScaRe_ = MuonEnergyScaleProducer(
                period_names[self.period],
                self.isData,
                self.to_apply["muScaRe"].get("mu_pt_for_ScaReApplication", "nano"),
                apply_scare=apply_scare,
                apply_fsr_recovery=apply_FSR,
                id_selection=id_selection,
            )
        return self.muScaRe_

    @property
    def ele(self):
        if self.ele_ is None:
            from .electron import EleCorrProducer

            self.ele_ = EleCorrProducer(
                period=period_names[self.period],
                columns=self.to_apply.get("ele", {}).get("columns", {}),
                isData=self.isData,
            )
        return self.ele_

    @property
    def puJetID(self):
        if self.puJetID_ is None:
            from .puJetID import puJetIDCorrProducer

            self.puJetID_ = puJetIDCorrProducer(period_names[self.period])
        return self.puJetID_

    @property
    def trg(self):
        if self.trg_ is None:
            if self.period.split("_")[0].startswith("Run3"):
                from .triggersRun3 import TrigCorrProducer
            else:
                from .triggers import TrigCorrProducer
            self.trg_ = TrigCorrProducer(
                period_names[self.period], self.global_params, self.trigger_dict
            )
        return self.trg_

    @property
    def bosonicRecoil(self):
        if self.bosonicRecoil_ is None:
            from .bosonicRecoil import BosonicRecoilCorrection

            self.bosonicRecoil_ = BosonicRecoilCorrection(
                period=self.period,
                config=self.to_apply.get("bosonicRecoil", {}),
                isData=self.isData,
                dataset_name=self.dataset_name,
                process_name=self.process_name,
                process_cfg=self.process_cfg,
            )
        return self.bosonicRecoil_

    @property
    def btag_norm(self):
        if self.btag_shape_norm_ is None:
            if not self.isData:
                from .btag import btagShapeWeightCorrector

                params = self.to_apply["btag"]
                producer = params["normCacheProducer"]
                producers = self.global_params["payload_producers"]
                bins = producers[producer]["bins"]
                if producer not in self.aggregated_caches:
                    raise RuntimeError(
                        f"Aggregated cache for producer '{producer}' was not provided to "
                        f"Corrections (available: {sorted(self.aggregated_caches)}). It must "
                        f"be localized and passed by the task layer (HistTupleProducerTask)."
                    )
                norm_file_path = self.aggregated_caches[producer]
                print(f"Applying shape weight normalization from {norm_file_path}")
                self.btag_shape_norm_ = btagShapeWeightCorrector(
                    norm_file_path=norm_file_path, bins=bins
                )
            else:
                raise RuntimeError("btag_shape_norm not applicable to data.")
        return self.btag_shape_norm_

    def applyScaleUncertainties(self, df, ana_reco_objects):
        source_dict = {central: []}
        if "tauES" in self.to_apply and not self.isData:
            df, source_dict = self.tau.getES(df, source_dict)
        if "eleES" in self.to_apply:
            df, source_dict = self.ele.getES(df, source_dict)
        if "JEC" in self.to_apply or "JER" in self.to_apply:
            apply_jes = "JEC" in self.to_apply and not self.isData
            apply_jer = "JER" in self.to_apply and not self.isData
            apply_jet_horns_fix_ = (
                "JER" in self.to_apply
                and self.to_apply["JER"].get("apply_jet_horns_fix", False)
                and not self.isData
            )
            df, source_dict = self.jet.getP4Variations(
                df, source_dict, apply_jer, apply_jes, apply_jet_horns_fix_
            )
        if "muScaRe" in self.to_apply:
            if self.stage == "AnaTuple":
                df, source_dict = self.muScaRe.getP4Variations(df, source_dict)
            elif self.stage == "HistTuple" or self.stage == "AnalysisCache":
                df = self.muScaRe.getP4VariationsForLegs(df)
            else:
                raise RuntimeError("No known stages for muon ScaRe application")
        if (
            "tauES" in self.to_apply
            or "JEC" in self.to_apply
            or "JER" in self.to_apply
            or "eleES" in self.to_apply
            or "muScaRe" in self.to_apply
        ):
            df, source_dict = self.met.getMET(
                df, source_dict, self.global_params["met_type"]
            )

        syst_dict = {}
        for source, source_objs in source_dict.items():
            for scale in getScales(source):
                syst_name = getSystName(source, scale)
                syst_dict[syst_name] = (source, scale)
                for obj in ana_reco_objects:
                    if obj not in source_objs:
                        suffix = (
                            "Central"
                            if f"{obj}_p4_Central" in df.GetColumnNames()
                            else "nano"
                        )
                        if (
                            obj == "boostedTau"
                            and "{obj}_p4_{suffix}" not in df.GetColumnNames()
                        ):
                            continue
                        if f"{obj}_p4_{syst_name}" not in df.GetColumnNames():
                            # print(
                            #     f"Defining nominal {obj}_p4_{syst_name} as {obj}_p4_{suffix}"
                            # )
                            df = df.Define(
                                f"{obj}_p4_{syst_name}", f"{obj}_p4_{suffix}"
                            )
        return df, syst_dict

    def prepareStitchingVariables(self, df):
        # Define any columns the stitching processors select on (e.g. a gen-level
        # decay-mode or dilepton mass) once, before the cross-section and denominator
        # expressions reference them. Processors that only use native nanoAOD branches
        # (e.g. LHE_Vpt/LHE_NpNLO) leave the frame unchanged.
        prepared = set()
        for p_name in self.xs_denom_processors.values():
            if p_name in prepared:
                continue
            prepared.add(p_name)
            df = self.all_processors[p_name].onAnaTuple_prepareDataFrame(df)
        return df

    def defineCrossSection(self, df, crossSectionBranchBase):
        branches = []
        if len(self.xs_denom_processors) == 0:
            raise RuntimeError(
                "No processor implements onAnaTuple_defineCrossSection method"
            )
        for suffix, p_name in self.xs_denom_processors.items():
            branch = f"{crossSectionBranchBase}{suffix}"
            if branch not in self.xs_print_history:
                print(f"Using processor {p_name} to define {branch}.", file=sys.stderr)
                self.xs_print_history.add(branch)
            xs_processor = self.all_processors[p_name]
            df = xs_processor.onAnaTuple_defineCrossSection(
                df, branch, self.xs_db, self.dataset_name, self.dataset_cfg
            )
            branches.append(branch)
        return df, branches

    # Corrections whose weights enter the normalisation weight as shape variations,
    # in the order getNormalisationCorrections runs them. Both the anaCache denominator
    # and the `base` numerator are built from this one list, so they cannot disagree
    # about which factors belong to a variation.
    shape_weight_producers = [
        ("pu", "pu"),  # (correction name in global.yaml, attribute on self)
        ("parton_shower", "parton_shower"),
        ("pdf", "pdf"),
    ]

    def _shapeWeightClasses(self):
        from .pu import puWeightProducer
        from .parton_shower import psWeightProducer
        from .pdf import pdfWeightProducer

        return {
            "pu": puWeightProducer,
            "parton_shower": psWeightProducer,
            "pdf": pdfWeightProducer,
        }

    def registerShapeWeights(self, registry, return_variations=True):
        """Populate a ShapeWeightRegistry with the shape producers active here.

        Registration does not depend on whether a producer is enabled at this stage:
        a branch written at AnaTuple has to be nameable again at AnaTupleMerge, where
        the producer is disabled and the branch is read back from the tuple.
        """
        classes = self._shapeWeightClasses()
        for corr_name, _ in self.shape_weight_producers:
            if corr_name not in self.to_apply:
                continue
            cls = classes[corr_name]
            registry.register(
                corr_name,
                cls.uncSource if return_variations else [],
                cls.branchName,
            )
        return registry

    def defineShapeWeights(self, df, return_variations=True, respect_enabled=True):
        """Define the shape-weight branches themselves."""
        branches = []
        for corr_name, attr in self.shape_weight_producers:
            if corr_name not in self.to_apply:
                continue
            enabled = True
            if respect_enabled:
                enabled = (
                    self.to_apply[corr_name].get("enabled", {}).get(self.stage, True)
                )
            df, producer_branches = getattr(self, attr).getWeight(
                df,
                return_variations=return_variations,
                return_list_of_branches=True,
                enabled=enabled,
            )
            branches.extend(producer_branches)
        return df, branches

    def defineDenominator(self, df, denomBranch, unc_source, unc_scale, ana_caches):
        branches = []
        if len(self.xs_denom_processors) == 0:
            raise RuntimeError(
                "No processor implements onAnaTuple_defineDenominator method"
            )
        for suffix, p_name in self.xs_denom_processors.items():
            branch = f"{denomBranch}{suffix}"
            if branch not in self.denom_print_history:
                print(
                    f"Using processor {p_name} to define {branch}.",
                    file=sys.stderr,
                )
                self.denom_print_history.add(branch)
            denom_processor = self.all_processors[p_name]
            df = denom_processor.onAnaTuple_defineDenominator(
                df,
                branch,
                p_name,
                self.dataset_name,
                unc_source,
                unc_scale,
                ana_caches,
            )
            branches.append((suffix, branch))
        return df, branches

    def getNormalisationCorrections(
        self,
        df,
        *,
        lepton_legs,
        offline_legs,
        trigger_names,
        unc_source,
        unc_scale,
        ana_caches,
        return_variations=True,
        use_genWeight_sign_only=True,
    ):
        # print(f"corrections to apply {self.to_apply}")
        isCentral = unc_source == central
        all_weights = []
        lumi_weight_name = "weight_lumi"
        if "lumi" in self.to_apply:
            lumi = self.global_params["luminosity"]
            df = df.Define(lumi_weight_name, f"float({lumi})")
            all_weights.append(lumi_weight_name)

        # xs_denom_processors only exists when "xs"/"base" normalisation is set up (anaTuple
        # stage). getNormalisationCorrections is also called at the histogram stage (via the
        # analysis histTupleDef) where it is absent, so guard with getattr.
        if getattr(self, "xs_denom_processors", None):
            df = self.prepareStitchingVariables(df)

        crossSectionBranchBase = "weight_xs"
        if "xs" in self.to_apply:
            df, crossSectionBranches = self.defineCrossSection(
                df, crossSectionBranchBase
            )
            all_weights.extend(crossSectionBranches)

        gen_weight_name = "weight_gen"
        if "gen" in self.to_apply:
            genWeight_def = (
                "std::copysign<float>(1.f, genWeight)"
                if use_genWeight_sign_only
                else "genWeight"
            )
            df = df.Define(gen_weight_name, genWeight_def)
            all_weights.append(gen_weight_name)

        shape_weight_registry = self.registerShapeWeights(
            ShapeWeightRegistry(),
            return_variations=return_variations and isCentral,
        )
        shape_weights_dict = shape_weight_registry.asDict()
        df, shape_weight_branches = self.defineShapeWeights(
            df, return_variations=return_variations and isCentral
        )
        all_weights.extend(shape_weight_branches)

        if "dy_hhbbtautau" in self.to_apply:
            df, dy_branches = self.dy_hhbbtautau.getWeight(
                df,
                return_variations=return_variations and isCentral,
                return_list_of_branches=True,
            )

            all_weights.extend(dy_branches)

        if "dy_hhbbww" in self.to_apply:
            df, dy_bbww_branches = self.dy_hhbbww.getWeight(
                df,
                return_variations=return_variations and isCentral,
                return_list_of_branches=True,
            )

            all_weights.extend(dy_bbww_branches)

        if "base" in self.to_apply:
            shared_mc = self.global_params.get("shared_mc")
            if shared_mc and not self.isData:
                split_mod, lo, hi, _ = shared_mc_split(
                    self.global_params["era"], shared_mc
                )
                df = df.Define(
                    "__shared_mc_in_era", shared_mc_in_era_expr(split_mod, lo, hi)
                )
            for (
                shape_unc_source,
                shape_unc_scale,
            ), shape_weights in shape_weights_dict.items():
                shape_unc_name = getSystName(shape_unc_source, shape_unc_scale)
                denomBranchBase = f"__denom_{shape_unc_name}"
                df, denom_branches = self.defineDenominator(
                    df, denomBranchBase, shape_unc_source, shape_unc_scale, ana_caches
                )
                denom_cmb_by_suffix = {}
                if shared_mc and not self.isData and shape_unc_name == central:
                    df, denom_cmb_branches = self.defineDenominator(
                        df,
                        f"{denomBranchBase}_cmb",
                        shape_unc_source,
                        shape_unc_scale,
                        _ana_caches_with_denom_key(ana_caches, "denominator_cmb"),
                    )
                    denom_cmb_by_suffix = {
                        suffix: branch for suffix, branch in denom_cmb_branches
                    }
                shape_weights_product = (
                    " * ".join(shape_weights) if len(shape_weights) > 0 else "1.0"
                )
                for suffix, denomBranch in denom_branches:
                    weight_name_central = f"weight_base{suffix}"
                    crossSectionBranch = f"{crossSectionBranchBase}{suffix}"
                    if shape_unc_name == central:
                        weight_name = weight_name_central
                        weight_out_name = weight_name
                    else:
                        weight_name = f"{weight_name_central}_{shape_unc_name}"
                        weight_out_name = f"{weight_name}_rel"
                    numer = (
                        f"{gen_weight_name} * {lumi_weight_name} * "
                        f"{crossSectionBranch} * {shape_weights_product}"
                    )
                    weight_formula = f"{numer} / {denomBranch}"
                    df = df.Define(weight_name, f"static_cast<float>({weight_formula})")
                    if shape_unc_name != central:
                        df = df.Define(
                            weight_out_name,
                            f"static_cast<float>({weight_name}/{weight_name_central})",
                        )
                    all_weights.append(weight_out_name)
                    if shared_mc and shape_unc_name == central:
                        cmb_weight = f"{weight_name_central}_cmb"
                        if self.isData:
                            df = df.Define(
                                cmb_weight,
                                f"static_cast<float>({weight_name_central})",
                            )
                        else:
                            cmb_denom = denom_cmb_by_suffix[suffix]
                            df = df.Define(
                                cmb_weight,
                                f"static_cast<float>(__shared_mc_in_era && ({cmb_denom} != 0) "
                                f"? ({numer} / {cmb_denom}) : 0.f)",
                            )
                        all_weights.append(cmb_weight)

        if "Vpt" in self.to_apply:
            df, Vpt_SF_branches = self.Vpt.getSF(df, isCentral, return_variations)
            all_weights.extend(Vpt_SF_branches)
            df, Vpt_DYw_branches = self.Vpt.getDYSF(df, isCentral, return_variations)
            all_weights.extend(Vpt_DYw_branches)
        if "tauID" in self.to_apply:
            df, tau_SF_branches = self.tau.getSF(
                df, lepton_legs, isCentral, return_variations
            )
            all_weights.extend(tau_SF_branches)
        if "btag" in self.to_apply:
            btag_sf_mode = self.to_apply["btag"]["modes"].get(self.stage, "none")
            if btag_sf_mode in ["shape", "shape_and_norm", "wp"]:
                if btag_sf_mode == "shape":
                    df, bTagSF_branches = self.btag.getBTagShapeSF(
                        df, unc_source, unc_scale, isCentral, return_variations
                    )
                elif btag_sf_mode == "shape_and_norm":
                    assert (
                        self.btag_norm is not None
                    ), "btagShapeWeightCorrector must be initialzied at in `shape_and_norm` mode."

                    df, bTagSF_branches = self.btag.getBTagShapeSF(
                        df, unc_source, unc_scale, isCentral, return_variations
                    )

                    df = self.btag_norm.UpdateBtagWeight(
                        df=df,
                        unc_src=unc_source,
                        unc_scale=unc_scale,
                        sf_branches=bTagSF_branches,
                    )
                else:
                    df, bTagSF_branches = self.btag.getBTagWPSF(
                        df, isCentral and return_variations, isCentral
                    )
                all_weights.extend(bTagSF_branches)
            elif btag_sf_mode != "none":
                raise RuntimeError(
                    f"btag mode {btag_sf_mode} not recognized. Supported modes are 'shape', 'shape_and_norm', 'wp' and 'none'."
                )

        if "mu" in self.to_apply:
            lowPt = self.to_apply["mu"].get("lowPt", True)
            if self.mu.low_available and lowPt:
                df, lowPtmuID_SF_branches = self.mu.getLowPtMuonIDSF(
                    df, lepton_legs, isCentral, return_variations
                )
                all_weights.extend(lowPtmuID_SF_branches)
            midPt = self.to_apply["mu"].get("midPt", True)
            if self.mu.med_available and midPt:
                df, muID_SF_branches = self.mu.getMuonIDSF(
                    df, lepton_legs, isCentral, return_variations
                )
                all_weights.extend(muID_SF_branches)
            hiPt = self.to_apply["mu"].get("hiPt", True)
            if self.mu.high_available and hiPt:
                df, highPtmuID_SF_branches = self.mu.getHighPtMuonIDSF(
                    df, lepton_legs, isCentral, return_variations
                )
                all_weights.extend(highPtmuID_SF_branches)

        if "ele" in self.to_apply:
            df, eleID_SF_branches = self.ele.getIDSF(
                df, lepton_legs, isCentral, return_variations
            )
            all_weights.extend(eleID_SF_branches)

        if "puJetID" in self.to_apply:
            df, puJetID_SF_branches = self.puJetID.getPUJetIDEff(
                df, isCentral, return_variations
            )
            all_weights.extend(puJetID_SF_branches)
        if "trigger" in self.to_apply:
            mode = self.to_apply["trigger"]["mode"]
            if mode == "SF":
                df, trg_SF_branches = self.trg.getSF(
                    df,
                    trigger_names,
                    lepton_legs,
                    isCentral and return_variations,
                    isCentral,
                    extraFormat=self.to_apply["trigger"].get("extraFormat", {}),
                )
                all_weights.extend(trg_SF_branches)
            elif mode == "efficiency":
                df, trg_SF_branches = self.trg.getEff(
                    df, trigger_names, offline_legs, self.trigger_dict
                )
                all_weights.extend(trg_SF_branches)
            else:
                raise RuntimeError(
                    f"Trigger correction mode {mode} not recognized. Supported modes are 'SF' and 'efficiency'."
                )

        if "fatjet" in self.to_apply:
            # bbWW fatjet corrections taken from here
            # https://indico.cern.ch/event/1573622/#6-updates-on-ak8-calibration-f
            df, fatjet_SF_branches = self.fatjet.getSF(df, isCentral, return_variations)
            all_weights.extend(fatjet_SF_branches)

        return df, all_weights

    def applyBosonicRecoil(self, df):
        if self.stage != "HistTuple":
            return df

        if self.isData:
            return df

        if "bosonicRecoil" not in self.to_apply:
            return df

        return self.bosonicRecoil.applyBosonicRecoilCorrections(
            df, self.process_cfg, self.to_apply
        )


# amcatnlo problem
# https://cms-talk.web.cern.ch/t/correct-way-to-stitch-lo-w-jet-inclusive-and-jet-binned-samples/17651/3
# https://cms-talk.web.cern.ch/t/stitching-fxfx-merged-njet-binned-samples/16751/7
