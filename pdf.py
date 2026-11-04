import sys


from .CorrectionsCore import *


class pdfWeightProducer:
    """PDF members as an indexed shape-weight source.

    PDF4LHC15 (arXiv:1510.03865) takes the spread across members of each bin of the
    fitted distribution, so the members cannot be reduced per event. Each one is a scale
    of the `pdf` source and therefore gets its own anaCache denominator and its own
    weight_base_pdf<k>_rel, the same way pileup gets one per Up/Down.

    How CMS applies the PDF and QCD-scale uncertainties: "CMS theory uncertainties",
    Physics Days,
    https://indico.cern.ch/event/1685006/contributions/7200117/attachments/3339004/5983688/CMS%20theory%20uncertainties%20Physics%20Days.pdf

    Member 0 is the Central branch, the way the nominal pileup weight is: it multiplies
    into weight_base and into the Central denominator, so the nominal is reweighted onto
    the stored set's central PDF with the sample's total normalisation preserved -- only
    the distribution, and hence the selected yield, moves. It matters for the
    samples whose member 0 is not 1 -- see pdf.h. A variation replaces it with member k,
    so weight_base_pdf<k>_rel carries w[k]/w[0] without the accessor ever dividing.

    A vector shorter than the 101 base members throws, as does a non-finite weight. The
    two optional alphaS members are 0 where a sample does not carry them (the
    four-flavour-scheme samples stop at 101), which makes weight_base_pdf101/102_rel come
    out NaN for those samples rather than passing as a weight of 1.

    The members are computed at AnaTuple from the NanoAOD branch, where the denominators
    are summed, and read back at AnaTupleMerge.
    """

    uncSource = ["pdf"]

    warned_missing = False

    @classmethod
    def scales(cls, cfg):
        return [str(member) for member in range(int(cfg.get("n_members", 103)))]

    @staticmethod
    def branchName(source, scale):
        if source == central:
            return "weight_pdf_Central"
        return f"weight_pdf_{scale}"

    def __init__(self, branch="LHEPdfWeight", n_members=103):
        self.branch = branch
        self.n_members = int(n_members)
        if self.n_members < 1:
            raise RuntimeError(
                f"pdfWeightProducer: n_members = {self.n_members} is not a member count."
            )
        registerSourceScales("pdf", self.scales({"n_members": self.n_members}))
        declareProviderHeader("pdf.h")

    def getWeight(
        self,
        df,
        return_variations=True,
        return_list_of_branches=False,
    ):
        sf_sources = pdfWeightProducer.uncSource if return_variations else []
        branches = []

        columns = {str(c) for c in df.GetColumnNames()}
        if any(c.startswith("weight_pdf_") for c in columns):
            raise RuntimeError(
                "pdfWeightProducer: weight_pdf_* columns already exist. Defining "
                "them again would shadow the persisted values."
            )
        has_input = self.branch in columns
        if not has_input and not pdfWeightProducer.warned_missing:
            pdfWeightProducer.warned_missing = True
            print(
                f"WARNING: '{self.branch}' not found; the pdf members are all 1 for "
                "this dataset.",
                file=sys.stderr,
            )

        for source in [central] + sf_sources:
            for scale in getScales(source):
                branch_name = pdfWeightProducer.branchName(source, scale)
                if not has_input:
                    expr = "1.f"
                else:
                    member = 0 if source == central else scale
                    expr = f"::correction::pdfMemberWeight({self.branch}, {member})"
                df = df.Define(branch_name, expr)
                branches.append(branch_name)

        if return_list_of_branches:
            return df, branches
        return df
