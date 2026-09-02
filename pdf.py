import os
import sys

import ROOT

from .CorrectionsCore import *

# Reduction modes understood by ::correction::pdfRelUnc. Names, not bare integers, are
# what appears in global.yaml -- a config that reads `mode: hessian` is checkable by
# eye, `mode: 1` is not.
PDF_MODES = {
    "replicas": 0,
    "hessian": 1,
}


class pdfWeightProducer:
    """PDF acceptance variations from the NanoAOD LHEPdfWeight vector.

    ~100 PDF members are reduced to a single symmetric Up/Down pair, because the shape
    framework has no representation for an N-member family: CorrectionsCore.getScales
    returns [Up, Down] for every non-central source, and the anaCache denominators are
    nested source -> scale -> processor to match. The reduction is done per event, in
    ::correction::pdfRelUnc, giving a relative spread r, and the weights are 1 +/- r.

    What that is, precisely: this is NOT PDF4LHC15 section 6 applied to the binned
    observable. The prescription takes the spread across members *of each bin content*;
    this takes it per event and then sums magnitudes within a bin, which implicitly
    treats bins as fully correlated. After the shape-only normalisation it captures how
    the variation magnitude trends against the observable, but misses genuinely
    anti-correlated bin migrations. The size of that approximation is meant to be
    bounded once, offline, by filling the member histograms directly for one process and
    comparing the per-bin spread against what this produces.

    As for the parton shower, the weights are already w_var / w_nominal, so there is no
    correction to apply centrally -- the nominal sample *is* the nominal PDF member.
    `weight_pdf_Central` is therefore the literal 1.f, which is also what keeps the
    existing pileup and parton-shower denominators bit-identical when this producer is
    added. What makes the nuisance shape-only is the anaCache denominator: each
    variation is divided by its own inclusive sum of weights in Corrections' `base`
    block, so the inclusive yield is unchanged and only acceptance survives. That is
    exactly complementary to the PDF_alphas lnN in the datacards, which carries the
    rate -- the two do not double count.

    See pdf.h for why the reduction mode must come from config rather than from the
    length of the vector.
    """

    initialized = False

    uncSource = ["pdf"]

    warned_missing = set()

    def __init__(self, branch="LHEPdfWeight", mode="replicas", first=1, n=100):
        # LHEPdfWeight, not LHEPdf_Weight. The anaCache denominator is accumulated in
        # anaTupleProducer.updateDenomEntry, which runs before addAllVariables defines
        # the renamed LHEPdf_Weight column, so only the original NanoAOD name is
        # available at that point. This is the same trap documented in parton_shower.py.
        self.branch = branch
        if mode not in PDF_MODES:
            raise RuntimeError(
                f"pdfWeightProducer: unknown mode '{mode}'. "
                f"Expected one of {sorted(PDF_MODES)}."
            )
        self.mode = mode
        self.mode_code = PDF_MODES[mode]
        self.first = int(first)
        self.n = int(n)
        if self.n < 2:
            raise RuntimeError(
                f"pdfWeightProducer: n = {self.n} is too few members to take a spread."
            )
        if not pdfWeightProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "pdf.h")
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')
            pdfWeightProducer.initialized = True

    @staticmethod
    def branchName(source, scale):
        return f"weight_pdf_{getSystName(source, scale)}"

    def relUncBranchName(self):
        """Intermediate column holding the per-event relative spread.

        Defined once and used by both Up and Down, so the ~100-member reduction runs
        once per event rather than twice. It is never appended to colToSave, so it does
        not reach the tuple.
        """
        return "pdf_rel_unc"

    def getWeight(
        self,
        df,
        return_variations=True,
        return_list_of_branches=False,
        enabled=True,
    ):
        sf_sources = pdfWeightProducer.uncSource if return_variations else []
        branches = []

        rel_unc = self.relUncBranchName()
        if enabled:
            columns = {str(c) for c in df.GetColumnNames()}
            has_input = self.branch in columns
            if not has_input:
                # A stage where the branch has been renamed away (AnaTupleMerge holds
                # LHEPdf_Weight, not LHEPdfWeight) must not silently define 1.f on top
                # of the correct values already persisted -- that would shadow them and
                # make the nuisance null with nothing to show for it. The producer is
                # meant to be disabled there via `enabled` in global.yaml.
                already_built = any(c.startswith("weight_pdf_") for c in columns)
                if already_built:
                    raise RuntimeError(
                        f"pdfWeightProducer: '{self.branch}' is not available but "
                        "weight_pdf_* columns already exist. Defining them again would "
                        "shadow the persisted values. Set enabled: false for "
                        "pdf at this stage."
                    )
                if self.branch not in pdfWeightProducer.warned_missing:
                    pdfWeightProducer.warned_missing.add(self.branch)
                    print(
                        f"WARNING: '{self.branch}' not found; the pdf shape "
                        "uncertainty will be a no-op for this dataset.",
                        file=sys.stderr,
                    )
            elif sf_sources and rel_unc not in columns:
                df = df.Define(
                    rel_unc,
                    f"::correction::pdfRelUnc({self.branch}, {self.mode_code}, "
                    f"{self.first}, {self.n})",
                )

        for source in [central] + sf_sources:
            for scale in getScales(source):
                branch_name = pdfWeightProducer.branchName(source, scale)
                if enabled:
                    if source == central:
                        # Exactly 1.0f, so adding this producer leaves the pileup and
                        # parton-shower denominators bit-identical: multiplying by an
                        # IEEE-754 1.0f is the identity.
                        expr = "1.f"
                    elif has_input:
                        sign = "+" if scale == up else "-"
                        expr = f"1.f {sign} {rel_unc}"
                    else:
                        expr = "1.f"
                    df = df.Define(branch_name, expr)
                    branches.append(branch_name)

        if return_list_of_branches:
            return df, branches
        return df
