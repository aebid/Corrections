#pragma once

#include "correction.h"
#include "corrections.h"

namespace correction {

    class VptCorrProvider : public CorrectionsBase<VptCorrProvider> {
      public:
        enum class UncSource : int { Central = -1, ewcorr = 0, Vpt = 1, DYWeight = 2 };

        enum class DYUncScale : int {
            nom = -1,
            up1 = 1,
            up2 = 2,
            up3 = 3,
            up4 = 4,
            up5 = 5,
            up6 = 6,
            up7 = 7,
            up8 = 8,
            up9 = 9,
            up10 = 10,
            down1 = 11,
            down2 = 12,
            down3 = 13,
            down4 = 14,
            down5 = 15,
            down6 = 16,
            down7 = 17,
            down8 = 18,
            down9 = 19,
            down10 = 20
        };

        // The number of uncertainties depends on the order of the used DY samples. It's 8 for LO samples, 10 for NLO samples and 9 for NNLO samples. This same number can be extracted from the DY_pTll_reweighting_N_uncertainty set in the correctionlib file. Each uncertainty corresponds to the uncertainty of one fit parameter from the function used to obtain the weights from. Therefore, all uncertainties are required to be included and are fully uncorrelated from each other.

        std::vector<std::string> getSystScale(const std::string& order, UncSource source, UncScale scale) const {
            static const std::map<std::string, int> order_to_n_params = {{"LO", 8}, {"NLO", 10}, {"NNLO", 9}};

            // Se qualsiasi delle due è "central", ritorna solo "nom"
            if (source == UncSource::Central || scale == UncScale::Central) {
                return {"nom"};
            }

            auto it = order_to_n_params.find(order);
            if (it == order_to_n_params.end()) {
                throw std::invalid_argument("Unknown DY sample order: " + order);
            }

            int n = it->second;
            std::vector<std::string> out;

            if (source == UncSource::DYWeight) {
                if (scale == UncScale::Up || scale == UncScale::Down) {
                    std::string scale_str = (scale == UncScale::Up) ? "up" : "down";
                    for (int i = 1; i <= n; ++i) {
                        out.push_back(scale_str + std::to_string(i));
                    }
                } else {
                    out.push_back("nom");
                    // throw std::invalid_argument("Invalid UncScale: must be 'central', 'up' or 'down'");
                }
            }

            return out;
        }

        static const std::string& getDYScaleStr(UncSource source, DYUncScale scale) {
            static const std::map<std::pair<UncSource, DYUncScale>, std::string> names = {
                {{UncSource::Central, DYUncScale::nom}, "nom"},
                {{UncSource::DYWeight, DYUncScale::nom}, "nom"},
                {{UncSource::DYWeight, DYUncScale::down1}, "down1"},
                {{UncSource::DYWeight, DYUncScale::up1}, "up1"},
                {{UncSource::DYWeight, DYUncScale::down2}, "down2"},
                {{UncSource::DYWeight, DYUncScale::up2}, "up2"},
                {{UncSource::DYWeight, DYUncScale::down3}, "down3"},
                {{UncSource::DYWeight, DYUncScale::up3}, "up3"},
                {{UncSource::DYWeight, DYUncScale::down4}, "down4"},
                {{UncSource::DYWeight, DYUncScale::up4}, "up4"},
                {{UncSource::DYWeight, DYUncScale::down5}, "down5"},
                {{UncSource::DYWeight, DYUncScale::up5}, "up5"},
                {{UncSource::DYWeight, DYUncScale::down6}, "down6"},
                {{UncSource::DYWeight, DYUncScale::up6}, "up6"},
                {{UncSource::DYWeight, DYUncScale::down7}, "down7"},
                {{UncSource::DYWeight, DYUncScale::up7}, "up7"},
                {{UncSource::DYWeight, DYUncScale::down8}, "down8"},
                {{UncSource::DYWeight, DYUncScale::up8}, "up8"},
                {{UncSource::DYWeight, DYUncScale::down9}, "down9"},
                {{UncSource::DYWeight, DYUncScale::up9}, "up9"},
                {{UncSource::DYWeight, DYUncScale::down10}, "down10"},
                {{UncSource::DYWeight, DYUncScale::up10}, "up10"},
            };
            return names.at(std::make_pair(source, scale));
        }

        static bool sourceApplies(UncSource source) {
            if (source == UncSource::ewcorr)
                return true;
            if (source == UncSource::Vpt)
                return true;
            if (source == UncSource::DYWeight)
                return true;
            return false;
        }

        VptCorrProvider(const std::string& VptCorrRootFileName,
                        const std::string& VptCorrLibWeightsFileName,
                        const std::string& VptCorrLibRecoilFileName,
                        const std::string& hist_name,
                        const std::string& hist_ewcorr_weight)
            : vpt_weights_corrections_(CorrectionSet::from_file(VptCorrLibWeightsFileName)),
              vpt_weights_(vpt_weights_corrections_->at("DY_pTll_reweighting")) {
            // VptCorrProvider(const std::string& VptCorrRootFileName, const std::string& hist_name, const std::string& hist_ewcorr_weight)
            // {
            auto VptCorrFile = root_ext::OpenRootFile(VptCorrRootFileName);
            histo_Vpt_SF.reset(
                root_ext::ReadCloneObject<TH1>(*VptCorrFile, hist_name.c_str(), hist_name.c_str(), true));
            histo_ewcorr_SF.reset(root_ext::ReadCloneObject<TH1>(
                *VptCorrFile, hist_ewcorr_weight.c_str(), hist_ewcorr_weight.c_str(), true));
        }

        float getSF_fromRootFile(const float& LHE_Vpt, UncSource source, UncScale scale) const {
            float sf = 1.;
            if (source == UncSource::Vpt) {
                const UncScale Vpt_scale = source == UncSource::Vpt ? scale : UncScale::Central;
                sf = getSFsFromHisto(histo_Vpt_SF, LHE_Vpt, Vpt_scale);
            }
            if (source == UncSource::ewcorr) {
                const UncScale nom_scale = source == UncSource::ewcorr ? scale : UncScale::Central;
                sf = getSFsFromHisto(histo_ewcorr_SF, LHE_Vpt, nom_scale);
            }
            return sf;
        }

        /*
    input for vpt_weights_corrections from corrlib:

    - order = Order of samples: LO, NLO, NNLO [type = string]
    - ptll = Gen-level pTll: Obtained from gen-level Electrons/Muons with status==1, or gen-level Taus with status==2, both also requiring status flag 'fromHardProcess' [type = "real" --> float/double]
    - syst = Systematic variations: 'nom', 'up1', 'down1', 'up2', 'down2', ... [type = string]
    */

        //taking DY reweighting weight from corrLib --> caveat: the input should be the generated di-leptons pT, whereas currently it takes the LHE Vpt
        // returns a vector of weights for the different uncertainties

        float getDY_weight(const float& LHE_Vpt, std::string sample_order, UncSource source, DYUncScale scale) const {
            float sf = 1.;
            const DYUncScale DYScale = sourceApplies(source) ? scale : DYUncScale::nom;
            // std::vector<std::string> scales = getSystScale(sample_order, source, scale);
            // std::map<std::string, float> sf_map;
            // for (const auto& s : scales) {
            std::string DYScale_str = getDYScaleStr(source, DYScale);
            sf = vpt_weights_->evaluate({sample_order, LHE_Vpt, DYScale_str});
            return sf;
            // std::cout << s << std::endl;
            // sf_map.insert(std::make_pair(s, sf));
            // std::cout << s << " : " << sf << std::endl;
            // }
            // return sf_map;
        }

        float getSFsFromHisto(const std::unique_ptr<TH1>& histo, const float& LHE_Vpt, UncScale scale) const {
            const auto x_axis = histo->GetXaxis();
            int x_bin = x_axis->FindFixBin(LHE_Vpt);
            if (x_bin < 1)
                x_bin = 1;
            if (x_bin > x_axis->GetNbins())
                x_bin = x_axis->GetNbins();
            return histo->GetBinContent(x_bin) + static_cast<int>(scale) * histo->GetBinError(x_bin);
        }

      private:
        std::unique_ptr<TH1> histo_Vpt_SF;
        std::unique_ptr<TH1> histo_ewcorr_SF;
        std::unique_ptr<CorrectionSet> vpt_weights_corrections_;
        Correction::Ref vpt_weights_;
    };

}  // namespace correction