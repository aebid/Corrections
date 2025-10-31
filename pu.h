#pragma once
#include "correction.h"
#include "corrections.h"

namespace correction {

    class puCorrProvider : public CorrectionsBase<puCorrProvider> {
      public:
        static const std::string& getScaleStr(UncScale scale) {
            static const std::map<UncScale, std::string> names = {
                {UncScale::Down, "down"},
                {UncScale::Central, "nominal"},
                {UncScale::Up, "up"},
            };
            return names.at(scale);
        }
        puCorrProvider(const std::string& fileName, const std::string& jsonName)
            : corrections_(CorrectionSet::from_file(fileName)), puweight(corrections_->at(jsonName)) {}

        float getWeight(UncScale scale, float Pileup_nTrueInt) const {
            const std::string& scale_str = getScaleStr(scale);
            return puweight->evaluate({Pileup_nTrueInt, scale_str});
        }

      private:
        std::unique_ptr<CorrectionSet> corrections_;
        Correction::Ref puweight;
    };

}  // namespace correction