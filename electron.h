#pragma once

#include <cstdint>

#include "correction.h"
#include "corrections.h"

namespace correction {
    // Seed of the random number that smears one electron: a function of the event and the
    // electron's index only, so every job and every rerun smears it the same way, and the nominal
    // smearing and all its variations use the same number, as the EGM recipe requires. TRandom3(0)
    // would seed from the clock, which is why 0 is never returned.
    inline UInt_t electronSmearingSeed(unsigned int run,
                                       unsigned int luminosityBlock,
                                       unsigned long long event,
                                       size_t index) {
        auto mix = [](uint64_t x) {  // one splitmix64 step
            x += 0x9E3779B97F4A7C15ULL;
            x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
            x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
            return x ^ (x >> 31);
        };
        uint64_t x = mix(event);
        x = mix(x ^ luminosityBlock);
        x = mix(x ^ run);
        x = mix(x ^ index);
        const UInt_t seed = static_cast<UInt_t>(x ^ (x >> 32));
        return seed == 0 ? 1 : seed;
    }

    class EleCorrProvider {
      public:
        enum class UncSource : int {
            Central = -1,
            EleID = 0,
            EleES = 1,
            Ele_dEsigma = 2,
            EleSmear = 3,
            EleReco = 4,
        };

        static std::string getESScaleStr(UncScale scale) {
            static const std::map<UncScale, std::string> scale_names = {
                {UncScale::Down, "scaledown"},
                {UncScale::Up, "scaleup"},
            };
            return scale_names.at(scale);
        }

        static std::string getIDScaleStr(UncScale scale) {
            static const std::map<UncScale, std::string> scale_names = {
                {UncScale::Down, "sfdown"},
                {UncScale::Central, "sf"},
                {UncScale::Up, "sfup"},
            };
            return scale_names.at(scale);
        }

        static bool sourceApplies(UncSource source) {
            if (source == UncSource::EleID)
                return true;
            if (source == UncSource::EleReco)
                return true;
            if (source == UncSource::EleES)
                return true;
            return false;
        }

        EleCorrProvider(const std::string& EleIDFile,
                        const std::string& EleESFile,
                        const std::string& EleIDFile_key,
                        const std::string& EleESFile_key)
            : corrections_(CorrectionSet::from_file(EleIDFile)),
              correctionsES_(CorrectionSet::from_file(EleESFile)),
              EleIDSF_(corrections_->at(EleIDFile_key)),
              EleES_(correctionsES_->at(EleESFile_key)) {}

        float getID_SF(const LorentzVectorM& Electron_p4,
                       std::string working_point,
                       std::string year,
                       UncSource source,
                       UncScale scale) const {
            const UncScale jet_scale = sourceApplies(source) ? scale : UncScale::Central;
            float value = 1.0;
            if (year.starts_with("2023")) {
                value = safeEvaluate(EleIDSF_,
                                     year,
                                     getIDScaleStr(jet_scale),
                                     working_point,
                                     Electron_p4.eta(),
                                     Electron_p4.pt(),
                                     Electron_p4.phi());
            } else {
                value = safeEvaluate(
                    EleIDSF_, year, getIDScaleStr(jet_scale), working_point, Electron_p4.eta(), Electron_p4.pt());
            }
            return value;
        }

        // EGM reconstruction-efficiency SFs are working points of the same Electron-ID-SF
        // correction, one per electron pT range.
        static std::string recoWorkingPoint(double pt) {
            if (pt < 20.)
                return "RecoBelow20";
            if (pt < 75.)
                return "Reco20to75";
            return "RecoAbove75";
        }

        float getReco_SF(const LorentzVectorM& Electron_p4, std::string year, UncSource source, UncScale scale) const {
            return getID_SF(Electron_p4, recoWorkingPoint(Electron_p4.pt()), year, source, scale);
        }
        // https://gitlab.cern.ch/cms-analysis-corrections/EGM/examples/-/blob/latest/egmScaleAndSmearingExample.py?ref_type=heads
        // Data gets the energy-scale correction, MC the smearing; the scale and smearing
        // uncertainties are MC-only. EGM did not tune the corrections below about 15 GeV, so such
        // electrons are left as they are.
        static constexpr double minScaleAndSmearingPt = 15.;

        RVecLV getESEtDep_data(const RVecLV& Electron_p4,
                               const RVecUC& Electron_seedGain,
                               const RVecF& Electron_SCeta,
                               unsigned int run,
                               const RVecF& Electron_r9) const {
            const auto& scale_correction = correctionsES_->compound().at("Scale");
            RVecLV final_p4 = Electron_p4;
            for (size_t n = 0; n < Electron_p4.size(); ++n) {
                const double pt = Electron_p4[n].pt();
                if (pt < minScaleAndSmearingPt)
                    continue;
                const double scale = scale_correction->evaluate({"scale",
                                                                 static_cast<double>(run),
                                                                 static_cast<double>(Electron_SCeta[n]),
                                                                 static_cast<double>(Electron_r9[n]),
                                                                 pt,
                                                                 static_cast<double>(Electron_seedGain[n])});
                final_p4[n] =
                    LorentzVectorM(pt * scale, Electron_p4[n].eta(), Electron_p4[n].phi(), Electron_p4[n].M());
            }
            return final_p4;
        }

        // The nominal is pt * (1 + smear * r). EleSmear replaces smear by smear_up/smear_down with the
        // same r; EleES multiplies the smeared pt by scale_up/scale_down. Every width and uncertainty
        // is evaluated at the uncorrected pt.
        RVecLV getESEtDep_MC(const RVecLV& Electron_p4,
                             const RVecF& Electron_SCeta,
                             unsigned int run,
                             unsigned int luminosityBlock,
                             unsigned long long event,
                             const RVecF& Electron_r9,
                             UncSource source,
                             UncScale scale) const {
            const bool shift_smear = source == UncSource::EleSmear && scale != UncScale::Central;
            const bool shift_scale = source == UncSource::EleES && scale != UncScale::Central;
            const std::string smear_name = shift_smear ? (scale == UncScale::Up ? "smear_up" : "smear_down") : "smear";
            const std::string scale_name = scale == UncScale::Up ? "scale_up" : "scale_down";
            RVecLV final_p4 = Electron_p4;
            for (size_t n = 0; n < Electron_p4.size(); ++n) {
                const double pt = Electron_p4[n].pt();
                if (pt < minScaleAndSmearingPt)
                    continue;
                const double r9 = Electron_r9[n];
                const double sc_eta = Electron_SCeta[n];
                const double smear = EleES_->evaluate({smear_name, pt, r9, sc_eta});
                TRandom3 rng(electronSmearingSeed(run, luminosityBlock, event, n));
                double factor = 1. + smear * rng.Gaus(0., 1.);
                if (shift_scale)
                    factor *= EleES_->evaluate({scale_name, pt, r9, sc_eta});
                final_p4[n] =
                    LorentzVectorM(pt * factor, Electron_p4[n].eta(), Electron_p4[n].phi(), Electron_p4[n].M());
            }
            return final_p4;
        }

        RVecLV getES(const RVecLV& Electron_p4,
                     const RVecI& Electron_genMatch,
                     const RVecUC& Electron_seedGain,
                     int run,
                     const RVecF& Electron_r9,
                     UncSource source,
                     UncScale scale) const {
            RVecLV final_p4 = Electron_p4;
            for (size_t n = 0; n < Electron_p4.size(); ++n) {
                const GenLeptonMatch genMatch = static_cast<GenLeptonMatch>(Electron_genMatch.at(n));
                if (scale != UncScale::Central &&
                    (genMatch == GenLeptonMatch::Electron || genMatch == GenLeptonMatch::TauElectron)) {
                    double sf = EleES_->evaluate({"total_uncertainty",
                                                  static_cast<int>(Electron_seedGain.at(n)),
                                                  static_cast<double>(run),
                                                  Electron_p4[n].eta(),
                                                  static_cast<double>(Electron_r9.at(n)),
                                                  Electron_p4[n].pt()});
                    final_p4[n] *= 1 + static_cast<int>(scale) * sf;
                }
            }
            return final_p4;
        }

      private:
        std::unique_ptr<CorrectionSet> corrections_, correctionsES_;
        Correction::Ref EleIDSF_, EleES_;
    };

}  //namespace correction
