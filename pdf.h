#pragma once

#include <atomic>
#include <cmath>
#include <cstddef>
#include <iostream>

#include "ROOT/RVec.hxx"

namespace correction {

// PDF uncertainty from LHEPdfWeight, following PDF4LHC15 (arXiv:1510.03865): section 6.1
// for MC replicas, section 6.2 for symmetric Hessian sets. The mode comes from config,
// since the vector length cannot tell the two apart. `first`/`n` exclude the nominal
// and the trailing alphaS members, which the PDF_alphas lnN already covers.

inline void warnPdfMembersOnce(std::size_t observed, std::size_t needed) {
  static std::atomic<bool> warned{false};
  if (!warned.exchange(true)) {
    std::cerr << "WARNING: LHEPdfWeight has " << observed << " members but the "
              << "configured range needs at least " << needed
              << "; the pdf shape uncertainty is a no-op for this dataset.\n";
  }
}

// Relative spread sigma / w[0], or 0 if it cannot be computed.
// mode: 0 = MC replicas, 1 = symmetric Hessian.
inline float pdfRelUnc(const ROOT::VecOps::RVec<float>& w, int mode, std::size_t first,
                       std::size_t n) {
  if (n < 2) return 0.f;
  if (w.size() < first + n) {
    warnPdfMembersOnce(w.size(), first + n);
    return 0.f;
  }

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
  return static_cast<float>(r);
}

}  // namespace correction
