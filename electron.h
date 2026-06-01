#pragma once

#include "correction.h"
#include "corrections.h"

namespace correction {
    class EleCorrProvider : public CorrectionsBase<EleCorrProvider> {
      public:
        enum class UncSource : int {
            Central = -1,
            EleID = 0,
            EleES = 1,
            Ele_dEsigma = 2,
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
                       std::string period,
                       UncSource source,
                       UncScale scale) const {
            const UncScale jet_scale = sourceApplies(source) ? scale : UncScale::Central;
            float value = 1.0;
            if (period.starts_with("2023")) {
                value = safeEvaluate(EleIDSF_,
                                     period,
                                     getIDScaleStr(jet_scale),
                                     working_point,
                                     Electron_p4.eta(),
                                     Electron_p4.pt(),
                                     Electron_p4.phi());
            } else {
                value = safeEvaluate(
                    EleIDSF_, period, getIDScaleStr(jet_scale), working_point, Electron_p4.eta(), Electron_p4.pt());
            }
            return value;
        }
        // https://gitlab.cern.ch/cms-analysis-corrections/EGM/examples/-/blob/latest/egmScaleAndSmearingExample.py?ref_type=heads
        RVecLV getESEtDep_data(const RVecLV& Electron_p4,
                     const RVecI& Electron_genMatch,
                     const RVecUC& Electron_seedGain,
                     const RVecF& Electron_SCeta,
                     unsigned int run,
                     const RVecUC& Electron_r9,
                     UncSource source,
                     UncScale scale) const {
            RVecLV final_p4 = Electron_p4;
            for (size_t n = 0; n < Electron_p4.size(); ++n) {
                const GenLeptonMatch genMatch = static_cast<GenLeptonMatch>(Electron_genMatch.at(n));
                if (scale != UncScale::Central &&
                    (genMatch == GenLeptonMatch::Electron || genMatch == GenLeptonMatch::TauElectron)) {
                    double sf = Electron_p4[n].pt() < 15 ? 0. : correctionsES_->compound().at("Scale")->evaluate({"scale",  // or SmearAndSyst ??? and smear?
                                                static_cast<double>(run),
                                                Electron_SCeta[n],
                                                static_cast<double>(Electron_r9.at(n)),
                                                Electron_p4[n].pt(),
                                                Electron_seedGain.at(n)});
                    final_p4[n] *= 1 + static_cast<int>(scale) * sf;
                }
            }
            return final_p4;
        }

        RVecLV getESEtDep_MC(const RVecLV& Electron_p4,
                     const RVecI& Electron_genMatch,
                     const RVecUC& Electron_seedGain,
                     const RVecF& Electron_SCeta,
                     unsigned int run,
                     const RVecUC& Electron_r9,
                     UncSource source,
                     UncScale scale) const {
            TRandom3 rng(0);
            RVecLV final_p4 = Electron_p4;
            for (size_t n = 0; n < Electron_p4.size(); ++n) {
                const GenLeptonMatch genMatch = static_cast<GenLeptonMatch>(Electron_genMatch.at(n));
                if (scale != UncScale::Central &&
                    (genMatch == GenLeptonMatch::Electron || genMatch == GenLeptonMatch::TauElectron)) {
                    double smear = Electron_p4[n].pt() < 15 ? 0. : EleES_->evaluate({"smear",  // or SmearAndSyst ??? and smear?
                                                // static_cast<double>(run),
                                                Electron_p4[n].pt(),
                                                static_cast<double>(Electron_r9.at(n)),
                                                Electron_SCeta[n]});
                    const double random_number = rng.Gaus(0.0, 1.0);
                    const double sf = 1.0 + static_cast<int>(scale) * smear * random_number;

                    final_p4[n] = LorentzVectorM(Electron_p4[n].pt() * sf, Electron_p4[n].eta(),Electron_p4[n].phi(),Electron_p4[n].M());
                    // const double energyErr_corr = std::sqrt(
                    //     std::pow(mc_electrons_energyErr[i], 2) +
                    //     std::pow(mc_electrons_energy[i] * smear, 2)
                    // ) * smearing;
                }
            }
            return final_p4;
        }

        RVecLV getES(const RVecLV& Electron_p4,
                     const RVecI& Electron_genMatch,
                     const RVecUC& Electron_seedGain,
                     int run,
                     const RVecUC& Electron_r9,
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
