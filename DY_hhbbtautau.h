#pragma once

#include <cmath>
#include <iostream>

#include "correction.h"
#include "corrections.h"

namespace correction {

    class DYbbtautauCorrProvider : public CorrectionsBase<DYbbtautauCorrProvider> {
      public:
        explicit DYbbtautauCorrProvider(const std::string& fileName)
            : corrections_(CorrectionSet::from_file(fileName)), dyWeight_(corrections_->at("dy_weight")) {}

        // template <typename LV1, typename LV2>
        double getWeight(const std::string& era,
                         int njets,
                         int ntags,
                         float pt_ll_gen,
                         const std::string& syst,
                         bool isValid) const {
            const float ptll = pt_ll_gen;
            static constexpr int kMinNJets = 2;

            double weight = 1.0;

            if (!isValid) {
                weight = 1.0;
            } else {
                if (njets < kMinNJets) {
                    weight = 1.0;
                } else {
                    weight = safeEvaluate(dyWeight_, era, njets, ntags, ptll, syst);
                }
            }
            return weight;
        }

      private:
        std::unique_ptr<CorrectionSet> corrections_;
        Correction::Ref dyWeight_;
    };

}  // namespace correction