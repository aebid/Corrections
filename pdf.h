#pragma once

#include <atomic>
#include <cmath>
#include <cstddef>
#include <iostream>

#include "ROOT/RVec.hxx"

namespace correction {

// PDF uncertainty from the NanoAOD LHEPdfWeight vector.
//
// The reduction formula is NOT the same for the two families of PDF set, and the
// difference is not small: applying the replica standard deviation to a Hessian set
// understates the spread by roughly sqrt(n-1), i.e. about a factor of 10 for a
// 100-member set. The mode is therefore taken from config and never guessed from
// w.size(): a length of 103 is genuinely ambiguous (NNPDF31_nnlo_hessian_pdfas is
// Hessian+alphaS, CT18 is also 103).
//
// The authoritative discriminator is the branch title written by CMSSW, e.g.
//   "LHE pdf variation weights (w_var / w_nominal) for LHA IDs 306000 - 306102"
// which the Define-rename in AnaProd/anaTupleDef.py drops, exactly as it drops the
// PSWeight title (see parton_shower.h). It has to be read from a source NanoAOD.
//
// `first` and `n` select the member range that carries the PDF variations, so the
// alphaS members that trail a "_pdfas" set (and member 0, the nominal) stay out of the
// spread. alphaS is covered separately by the PDF_alphas lnN in the datacards; folding
// it in here would double count it.
//
// Prescription: PDF4LHC15 recommendations, arXiv:1510.03865 -- section 6.1 / eq. (11)
// for Monte-Carlo replicas, section 6.2 / eq. (20) for symmetric Hessian sets. See also
// PDF4LHC21, arXiv:2203.05506.

inline void warnPdfMembersOnce(std::size_t observed, std::size_t needed) {
  static std::atomic<bool> warned{false};
  if (!warned.exchange(true)) {
    std::cerr << "WARNING: LHEPdfWeight has " << observed << " members but the "
              << "configured range needs at least " << needed
              << "; the pdf shape uncertainty is a no-op for this dataset.\n";
  }
}

// Returns the relative PDF spread sigma / w_ref, or 0 when it cannot be computed.
// Zero is the no-op value: the caller forms 1 +/- r, so r = 0 leaves the weight at 1.
//
// mode: 0 = Monte-Carlo replicas (sample standard deviation over the members)
//       1 = symmetric Hessian (deviations from the central member, in quadrature)
inline float pdfRelUnc(const ROOT::VecOps::RVec<float>& w, int mode, std::size_t first,
                       std::size_t n) {
  if (n < 2) return 0.f;
  if (w.size() < first + n) {
    warnPdfMembersOnce(w.size(), first + n);
    return 0.f;
  }

  // Reference member. NanoAOD documents these as w_var / w_nominal, so w[0] is
  // nominally 1 -- but that normalisation is not reliable across campaigns. Dividing
  // the spread by w[0] at the end is what makes the result relative either way; it is
  // the renormalisation, not an assumption that one was already applied.
  const double w0 = static_cast<double>(w[0]);
  if (!std::isfinite(w0) || w0 == 0.) return 0.f;

  double sigma2 = 0.;
  if (mode == 1) {
    for (std::size_t i = first; i < first + n; ++i) {
      const double d = static_cast<double>(w[i]) - w0;
      if (!std::isfinite(d)) return 0.f;
      sigma2 += d * d;
    }
  } else {
    double sum = 0.;
    for (std::size_t i = first; i < first + n; ++i) {
      const double v = static_cast<double>(w[i]);
      if (!std::isfinite(v)) return 0.f;
      sum += v;
    }
    const double mean = sum / static_cast<double>(n);
    for (std::size_t i = first; i < first + n; ++i) {
      const double d = static_cast<double>(w[i]) - mean;
      sigma2 += d * d;
    }
    sigma2 /= static_cast<double>(n - 1);
  }

  const double r = std::sqrt(sigma2) / std::abs(w0);
  if (!std::isfinite(r)) return 0.f;
  // Deliberately not clamped. r > 1 makes the Down weight negative, which is a
  // generator or configuration pathology worth seeing downstream rather than quietly
  // rewriting -- the same choice psWeight makes for zero and negative PS weights.
  return static_cast<float>(r);
}

}  // namespace correction
