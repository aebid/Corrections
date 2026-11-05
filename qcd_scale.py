import sys


from .CorrectionsCore import *


class qcdScaleWeightProducer:
    """The nine muR/muF scale weights as an indexed shape-weight source.

    Stored whole, like the PDF members: each entry gets its own anaCache denominator and
    its own weight_base_qcd_scale_muR<r>_muF<f>_rel, and which of them form the envelope is
    decided later, per bin. Being shape-only, they complement the QCD_scale_* rate lnN.

    How CMS applies the QCD-scale and PDF uncertainties: "CMS theory uncertainties",
    Physics Days,
    https://indico.cern.ch/event/1685006/contributions/7200117/attachments/3339004/5983688/CMS%20theory%20uncertainties%20Physics%20Days.pdf

    The scale is the (muR, muF) pair the entry stands for, not its position in the vector,
    so the branch says what it varies. `0p5` spells 0.5 because a column name cannot carry
    a dot, and no label ends in Up or Down, which splitSystName would cut at.

    Entry 4 is not stored as a member. It is the nominal, and where it is not 1 it carries
    the same leftover factor as PDF member 0 (see qcd_scale.h). That factor has to enter
    weight_base exactly once: when pdf is active it comes from pdf's Central, and the
    members are divided by entry 4 so it is not counted again; when pdf is not active
    nothing else carries it, so entry 4 becomes this producer's Central and the members
    are taken as stored. Either way entry 4 is a divisor or the Central, never a variation.
    """

    uncSource = ["qcd_scale"]

    # Label -> its index on the nine-point (muR, muF) grid, muR outermost. [4] is the
    # nominal and [2], [6] are the unphysical corners. qcdScaleWeight remaps these
    # indices when the vector has eight entries and the nominal was left out.
    members = {
        "_muR0p5_muF0p5": 0,
        "_muR0p5_muF1": 1,
        "_muR0p5_muF2": 2,
        "_muR1_muF0p5": 3,
        # 4 is the nominal: the Central branch or the divisor, never a member.
        "_muR1_muF2": 5,
        "_muR2_muF0p5": 6,
        "_muR2_muF1": 7,
        "_muR2_muF2": 8,
    }

    n_members = len(members)

    warned_missing = False

    @classmethod
    def scales(cls, cfg):
        return list(cls.members)

    @staticmethod
    def branchName(source, scale):
        if source == central:
            return "weight_qcd_scale_Central"
        return f"weight_qcd_scale{scale}"

    nominal_index = 4

    def __init__(self, branch="LHEScaleWeight", applies_nominal=True):
        self.branch = branch
        self.applies_nominal = applies_nominal
        registerSourceScales("qcd_scale", self.scales({}))
        declareProviderHeader("qcd_scale.h")

    def getWeight(
        self,
        df,
        return_variations=True,
        return_list_of_branches=False,
    ):
        sf_sources = qcdScaleWeightProducer.uncSource if return_variations else []
        branches = []

        columns = {str(c) for c in df.GetColumnNames()}
        if any(c.startswith("weight_qcd_scale_") for c in columns):
            raise RuntimeError(
                "qcdScaleWeightProducer: weight_qcd_scale_* columns already exist. "
                "Defining them again would shadow the persisted values."
            )
        has_input = self.branch in columns
        if not has_input and not qcdScaleWeightProducer.warned_missing:
            qcdScaleWeightProducer.warned_missing = True
            print(
                f"WARNING: '{self.branch}' not found; the qcd_scale members are all 1 "
                "for this dataset.",
                file=sys.stderr,
            )

        for source in [central] + sf_sources:
            for scale in getScales(source):
                branch_name = qcdScaleWeightProducer.branchName(source, scale)
                # Central is a weight only when this producer owns the nominal factor;
                # otherwise pdf applies it and the members divide it out instead.
                accessor, index = None, None
                if has_input:
                    if source != central:
                        index = qcdScaleWeightProducer.members[scale]
                        accessor = (
                            "qcdScaleWeight"
                            if self.applies_nominal
                            else "qcdScaleNormalisedWeight"
                        )
                    elif self.applies_nominal:
                        index = qcdScaleWeightProducer.nominal_index
                        accessor = "qcdScaleWeight"
                if accessor is None:
                    expr = "1.f"
                else:
                    expr = f"::correction::{accessor}({self.branch}, {index})"
                df = df.Define(branch_name, expr)
                branches.append(branch_name)

        if return_list_of_branches:
            return df, branches
        return df
