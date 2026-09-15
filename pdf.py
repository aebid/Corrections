import os
import sys

import ROOT

from .CorrectionsCore import *

PDF_MODES = {
    "replicas": 0,
    "hessian": 1,
}


class pdfWeightProducer:
    """PDF acceptance variations from the NanoAOD LHEPdfWeight vector, as a shape weight.

    The members are reduced per event to a relative spread r (see pdf.h), and
    (Down, Central, Up) = (1 - r, 1, 1 + r). This approximates PDF4LHC15, which takes
    the spread per bin.
    """

    initialized = False

    uncSource = ["pdf"]

    warned_missing = set()

    def __init__(self, branch="LHEPdfWeight", mode="replicas", first=1, n=100):
        # The NanoAOD name: the denominator is summed before anaTupleDef renames it.
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
