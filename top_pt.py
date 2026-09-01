from .CorrectionsCore import *


class TopPtCorrProducer:
    """Top pT reweighting for SM ttbar.

    The top pT spectrum in data is softer than POWHEG+PYTHIA8 predicts. The
    correction is a per-top scale factor whose event weight is the geometric mean of
    the two, following https://twiki.cern.ch/twiki/bin/view/CMS/TopPtReweighting

    Unlike the other reweightings in this directory the correction is a closed-form
    function rather than a correctionlib payload, so there is no JSON to load and no
    header to declare -- a plain Define is enough.

    Two things about the inputs are worth repeating here, because getting either
    wrong silently produces a plausible but invalid weight:

    * The pT must come from the `isLastCopy` parton-level top -- after radiation and
      before decay. The TWiki is explicit that a reco- or particle-level proxy gives
      an invalid reweighting. In particular the LHE-level tops the anaTuple also
      carries are taken *before* radiation and are not a substitute.
    * Only SM ttbar is reweighted, never single top or tops from BSM production. That
      scoping is done in global.yaml with a `processes:` list, the same way the DY
      reweighting is scoped.
    """

    # Confirmed against https://twiki.cern.ch/twiki/bin/view/CMS/TopPtReweighting.
    # Both parameterizations derive from Run 2 13 TeV measurements (TOP-16-011,
    # TOP-16-008); whether they apply to Run 3 at 13.6 TeV is a separate question.
    #
    # Each entry is a C++ expression for the single-top scale factor, with `{pt}`
    # standing in for the top pT.
    parameterizations = {
        # ratio of data to NLO (POWHEG+PYTHIA8)
        "data_nlo": "std::exp(0.0615f - 0.0005f * ({pt}))",
        # ratio of the NNLO QCD + NLO EW prediction to NLO
        "nnlo_nlo": "0.103f * std::exp(-0.0118f * ({pt})) - 0.000134f * ({pt}) + 0.973f",
    }

    default_variations = [up, down]

    central_branch = "weight_top_pt_central"

    def __init__(
        self,
        era,
        *,
        top_pt_branch="genTop_pt",
        antitop_pt_branch="genAntiTop_pt",
        parameterization="nnlo_nlo",
        max_pt=None,
        variations=None,
    ):
        self.era = era

        if parameterization not in self.parameterizations:
            raise RuntimeError(
                f"TopPtCorrProducer: unknown parameterization '{parameterization}'. "
                f"Supported: {sorted(self.parameterizations.keys())}"
            )

        self.top_pt_branch = top_pt_branch
        self.antitop_pt_branch = antitop_pt_branch
        self.parameterization = parameterization
        # The TWiki quotes a validity range for the fitted functions. It is left unset
        # rather than guessed: pass max_pt to clamp the pT the SF is evaluated at once
        # the number is confirmed.
        self.max_pt = max_pt
        self.variations = list(
            self.default_variations if variations is None else variations
        )

    def _sf_expr(self, pt_branch):
        """The single-top scale factor, clamped to be non-negative.

        The nnlo_nlo parameterization carries a linear term and so turns negative for
        absurdly large pT; sqrt of a negative product is NaN, which would poison the
        whole event weight rather than just that one factor.
        """
        pt = f"static_cast<float>({pt_branch})"
        if self.max_pt is not None:
            pt = f"std::min({pt}, {float(self.max_pt)}f)"
        sf = self.parameterizations[self.parameterization].format(pt=pt)
        return f"std::max(0.f, static_cast<float>({sf}))"

    def _central_expr(self):
        """sqrt(SF(top) * SF(antitop)), or 1 where there is no gen top pair.

        genTop_pt/genAntiTop_pt are -1 when the anaTuple found no last-copy top pair,
        which covers every non-ttbar sample and any ttbar event with an incomplete gen
        record. Returning 1 there makes the correction a no-op rather than an error.
        """
        return (
            f"({self.top_pt_branch} >= 0.f && {self.antitop_pt_branch} >= 0.f) ? "
            f"static_cast<float>(std::sqrt("
            f"{self._sf_expr(self.top_pt_branch)} * "
            f"{self._sf_expr(self.antitop_pt_branch)})) : 1.0f"
        )

    def _variation_expr(self, scale):
        """A 100% uncertainty on the correction.

        The TWiki gives the scale factor but prescribes no uncertainty. arXiv:2105.03977
        (ATLAS/CMS) records the common practice: "Usually both ATLAS and CMS assign a
        systematic uncertainty derived from the difference between the applying and not
        the top pT reweighing".

        `Down` is exactly that -- it removes the reweighting. `Up` mirrors it, which the
        reference does *not* prescribe: the prescription is one-sided and Combine's shape
        type wants a pair. Mirrored in log space (Up = SF^2, so Up_rel = SF and
        Down_rel = 1/SF) rather than linear, because the quantity is a multiplicative
        weight and log mirroring cannot go negative.

        Note SF < 1 over most of the spectrum, so `Up` lowers the ttbar yield.
        """
        if scale == up:
            return f"static_cast<float>({self.central_branch} * {self.central_branch})"
        if scale == down:
            return "1.0f"
        raise RuntimeError(f"TopPtCorrProducer: unsupported variation '{scale}'.")

    def getWeight(
        self,
        df,
        return_variations=True,
        return_list_of_branches=False,
        enabled=True,
    ):
        if not enabled:
            if return_list_of_branches:
                return df, []
            return df

        branches = []

        df = df.Define(
            self.central_branch, f"static_cast<float>({self._central_expr()})"
        )
        branches.append(self.central_branch)

        if return_variations:
            for scale in self.variations:
                branch_name = f"weight_top_pt_{scale}"
                df = df.Define(branch_name, self._variation_expr(scale))
                branches.append(branch_name)

                # weights.yaml multiplies a relative branch by final_weight, which
                # already carries the central weight -- the convention every other
                # correction follows (see DY_hhbbtautau.py). The central branch is
                # always defined by the time this runs.
                rel_branch = f"{branch_name}_rel"
                df = df.Define(
                    rel_branch,
                    f"static_cast<float>({self.central_branch} != 0.f "
                    f"? {branch_name} / {self.central_branch} : 1.f)",
                )
                branches.append(rel_branch)

        if return_list_of_branches:
            return df, branches
        return df
