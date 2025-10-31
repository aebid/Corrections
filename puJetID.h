#pragma once

#include "correction.h"
#include "corrections.h"

namespace correction {

    class PUJetIDCorrProvider : public CorrectionsBase<PUJetIDCorrProvider> {
      public:
        enum class UncSource : int {
            Central = -1,
            PUJetID_eff = 0,
        };

        static const std::string& getScaleStr(UncScale scale) {
            static const std::map<UncScale, std::string> names = {
                {UncScale::Down, "down"},
                {UncScale::Central, "nom"},
                {UncScale::Up, "up"},
            };
            return names.at(scale);
        }

        static bool sourceApplies(UncSource source) {
            if (source == UncSource::PUJetID_eff)
                return true;
            return false;
        }

        PUJetIDCorrProvider(const std::string& fileName)
            : corrections_(CorrectionSet::from_file(fileName)), puJetEff_(corrections_->at("PUJetID_eff")) {}
        RVecF getPUJetID_eff(const RVecF& Jet_pt,
                             const RVecF& Jet_eta,
                             const std::string working_point,
                             UncSource source,
                             UncScale scale) const {
            RVecF weights(Jet_pt.size(), 1.);
            const UncScale PUJetID_scale = sourceApplies(source) ? scale : UncScale::Central;
            const std::string& scale_str = getScaleStr(PUJetID_scale);
            for (size_t jet_idx = 0; jet_idx < Jet_pt.size(); jet_idx++) {
                if (Jet_pt[jet_idx] > 20 && Jet_pt[jet_idx] <= 50. && std::abs(Jet_eta[jet_idx]) < 5) {
                    weights[jet_idx] = static_cast<float>(
                        puJetEff_->evaluate({Jet_eta[jet_idx], Jet_pt[jet_idx], scale_str, working_point}));
                }
            }
            return weights;
        }

      private:
      private:
        std::unique_ptr<CorrectionSet> corrections_;
        Correction::Ref puJetEff_;
    };

}  // namespace correction