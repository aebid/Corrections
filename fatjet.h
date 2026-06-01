#pragma once

#include "correction.h"
#include "corrections.h"

namespace correction {
    class FatJetCorrProvider : public CorrectionsBase<FatJetCorrProvider> {
      public:
        enum class UncSource : int {
            Central = -1,
            Hbb = 0,
            Hcc = 1,
            tau21 = 2,
        };

        static bool sourceApplies(UncSource source, int hadronFlavour) {
            if (source == UncSource::Hbb)
                return hadronFlavour == 5;
            if (source == UncSource::Hcc)
                return hadronFlavour == 4;
            if (source == UncSource::tau21)
                return true;
            return false;
        }

        static std::string getScaleStr(UncSource source, UncScale scale) {
            static const std::map<std::pair<UncSource, UncScale>, std::string> scale_names = {
                {{UncSource::Central, UncScale::Central}, "nominal"},
                {{UncSource::Hbb, UncScale::Up}, "up"},
                {{UncSource::Hbb, UncScale::Down}, "down"},
                {{UncSource::Hcc, UncScale::Up}, "up"},
                {{UncSource::Hcc, UncScale::Down}, "down"},
                {{UncSource::tau21, UncScale::Up}, "tau21Up"},
                {{UncSource::tau21, UncScale::Down}, "tau21Down"},
            };
            const auto key = std::make_pair(source, scale);
            const auto iter = scale_names.find(key);
            if (iter == scale_names.end())
                throw std::runtime_error("Could not find fatjet scale key");
            return iter->second;
        }

        FatJetCorrProvider(const std::string& fatjetFile,
                        const std::string& Hbb_key,
                        const std::string& Hcc_key)
            : corrections_(CorrectionSet::from_file(fatjetFile)),
              Hbb_(corrections_->at(Hbb_key)),
              Hcc_(corrections_->at(Hcc_key)) {}

        float get_SF(const bool FatJet_isValid, const float FatJet_pt,
                     const int FatJet_HadronFlavour,
                     const UncSource source,
                     const UncScale scale) const {
            const bool applies = sourceApplies(source, FatJet_HadronFlavour);
            const UncScale jet_scale = applies ? scale : UncScale::Central;
            const UncSource jet_source = applies ? source : UncSource::Central;
            float value = 1.0;
            if(FatJet_isValid) {
                if (FatJet_HadronFlavour == 5){
                    value = safeEvaluate(Hbb_, FatJet_pt, getScaleStr(jet_source, jet_scale));
                }
                else if (FatJet_HadronFlavour == 4){
                    value = safeEvaluate(Hcc_, FatJet_pt, getScaleStr(jet_source, jet_scale));
                }
            }
            return value;
        }

        RVecF get_SF(const RVecB& FatJet_isValid, const RVecF& FatJet_pt,
                     const RVecI& FatJet_HadronFlavour,
                     const UncSource source,
                     const UncScale scale) const {
            RVecF result(FatJet_isValid.size(), 1.f);
            assert(FatJet_isValid.size() == FatJet_pt.size());
            assert(FatJet_isValid.size() == FatJet_HadronFlavour.size());
            for(size_t n = 0; n < FatJet_isValid.size(); ++n)
                result[n] = get_SF(FatJet_isValid[n], FatJet_pt[n], FatJet_HadronFlavour[n], source, scale);
            return result;
        }

    private:
        std::unique_ptr<CorrectionSet> corrections_;
        Correction::Ref Hbb_, Hcc_;
    };

}  //namespace correction
