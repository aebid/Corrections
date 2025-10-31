#pragma once

#include "correction.h"
#include "corrections.h"

namespace correction {
    class FatJetCorrProvider : public CorrectionsBase<FatJetCorrProvider> {
      public:
        enum class UncSource : int {
            Central = -1,
            JER = 0,
            Total = 1,
            RelativeBal = 2,
            HF = 3,
            BBEC1 = 4,
            EC2 = 5,
            Absolute = 6,
            FlavorQCD = 7,
            BBEC1_year = 8,
            Absolute_year = 9,
            EC2_year = 10,
            HF_year = 11,
            RelativeSample_year = 12
        };

        static const std::string getFullNameUnc(const std::string source_name, const std::string year, bool need_year) {
            return need_year ? source_name + year : source_name;
        }
        static const std::string& getScaleStr(UncScale scale) {
            static const std::map<UncScale, std::string> names = {
                {UncScale::Down, "down"},
                {UncScale::Central, "nom"},
                {UncScale::Up, "up"},
            };
            return names.at(scale);
        }
        static const int GetScaleIdx(UncScale scale) {
            static const std::map<UncScale, int> scale_indexes = {
                {UncScale::Up, 1},
                {UncScale::Down, 2},
                {UncScale::Central, 0},
            };
            return scale_indexes.at(scale);
        }
        static const int GetJesIdx(UncSource source, UncScale scale) {
            int index = static_cast<int>(source) * 2 + GetScaleIdx(scale);
            return std::max(index, 0);
        }
        static const std::map<UncSource, std::tuple<std::string, bool, bool>> getUncMap() {
            static const std::map<UncSource, std::tuple<std::string, bool, bool>> UncMap = {
                {UncSource::Central, {"Central", false, false}},
                {UncSource::JER, {"JER", false, false}},
                {UncSource::FlavorQCD, {"FlavorQCD", true, false}},
                {UncSource::RelativeBal, {"RelativeBal", true, false}},
                {UncSource::HF, {"HF", true, false}},
                {UncSource::BBEC1, {"BBEC1", true, false}},
                {UncSource::EC2, {"EC2", true, false}},
                {UncSource::Absolute, {"Absolute", true, false}},
                {UncSource::Total, {"Total", true, false}},
                {UncSource::BBEC1_year, {"BBEC1_", true, true}},
                {UncSource::Absolute_year, {"Absolute_", true, true}},
                {UncSource::EC2_year, {"EC2_", true, true}},
                {UncSource::HF_year, {"HF_", true, true}},
                {UncSource::RelativeSample_year, {"RelativeSample_", true, true}},
            };
            return UncMap;
        }

        FatJetCorrProvider(const std::string& ptResolution,
                           const std::string& ptResolutionSF,
                           const std::string& JesTxtFile,
                           const std::string& year) {
            // THIS HAS BEEN TAKEN FROM https://bamboo-hep.readthedocs.io/en/latest/_modules/bamboo/analysisutils.html
            const std::string puppiGenFormula =
                "1.0062610283313527+(-1.061605139842829*((x*0.07999000770091785)^-1.2045376937033758))";
            const std::array<double, 6> reco_cen_params = {1.0930197734452352,
                                                           -0.00015006788774298745,
                                                           3.4486611503791434e-07,
                                                           -2.681003093847412e-10,
                                                           8.674402290776817e-14,
                                                           -1.0011358570698617e-17};
            const std::array<double, 6> reco_for_params = {1.2721151537214315,
                                                           -0.0005716403627542301,
                                                           8.372894123074334e-07,
                                                           -5.204332049858346e-10,
                                                           1.4537520981877012e-13,
                                                           -1.5038869243803616e-17};
            const std::array<double, 6> resol_cen_params = {1.092735080341856,
                                                            4.142622682579229e-05,
                                                            -1.3736805733597026e-07,
                                                            1.2295818250625584e-10,
                                                            -4.197075395161288e-14,
                                                            4.923792745086088e-18};
            const std::array<double, 6> resol_for_params = {1.1649278339374347,
                                                            -0.00012678902807057208,
                                                            1.0594037344842974e-07,
                                                            6.072087019460118e-12,
                                                            -1.992427482862693e-14,
                                                            3.644006510237158e-18};
            fjvc_total.setPuppiCorrections(
                puppiGenFormula, reco_cen_params, reco_for_params, resol_cen_params, resol_for_params);
            fjvc_total.setSmearing(ptResolution, ptResolutionSF, false, true, 0.2, 3);
            fjvc_total.setAddHEM2018Issue(year == "2018");
            for (auto& [unc_source, unc_features] : getUncMap()) {
                if (!std::get<1>(unc_features))
                    continue;
                std::string jes_name = getFullNameUnc(std::get<0>(unc_features), year, std::get<2>(unc_features));
                fjvc_total.addJESUncertainty(jes_name, JetCorrectorParameters{JesTxtFile, jes_name});
            }
        }

        std::map<std::pair<UncSource, UncScale>, RVecLV> getShiftedP4(const RVecF& FatJet_pt,
                                                                      const RVecF& FatJet_eta,
                                                                      const RVecF& FatJet_phi,
                                                                      const RVecF& FatJet_mass,
                                                                      const RVecF& FatJet_rawFactor,
                                                                      const RVecF& FatJet_area,
                                                                      const RVecF& FatJet_msoftdrop,
                                                                      const RVecShort& FatJet_subJetIdx1,
                                                                      const RVecShort& FatJet_subJetIdx2,
                                                                      const RVecF& SubJet_pt,
                                                                      const RVecF& SubJet_eta,
                                                                      const RVecF& SubJet_phi,
                                                                      const RVecF& SubJet_mass,
                                                                      const RVecI& FatJet_jetId,
                                                                      const float Rho_fixedGridRhoFastjetAll,
                                                                      std::uint32_t seed,
                                                                      const RVecF& GenJetAK8_pt,
                                                                      const RVecF& GenJetAK8_eta,
                                                                      const RVecF& GenJetAK8_phi,
                                                                      const RVecF& GenJetAK8_mass,
                                                                      const RVecF& SubGenJetAK8_pt,
                                                                      const RVecF& SubGenJetAK8_eta,
                                                                      const RVecF& SubGenJetAK8_phi,
                                                                      const RVecF& SubGenJetAK8_mass,
                                                                      int event) const {
            std::map<std::pair<UncSource, UncScale>, RVecLV> all_shifted_p4;
            //std::cout << FatJet_pt.size() << std::endl;
            //std::cout << event << std::endl;
            auto result = fjvc_total.produce(FatJet_pt,
                                             FatJet_eta,
                                             FatJet_phi,
                                             FatJet_mass,
                                             FatJet_rawFactor,
                                             FatJet_area,
                                             FatJet_msoftdrop,
                                             FatJet_subJetIdx1,
                                             FatJet_subJetIdx2,
                                             SubJet_pt,
                                             SubJet_eta,
                                             SubJet_phi,
                                             SubJet_mass,
                                             FatJet_jetId,
                                             Rho_fixedGridRhoFastjetAll,
                                             seed,
                                             GenJetAK8_pt,
                                             GenJetAK8_eta,
                                             GenJetAK8_phi,
                                             GenJetAK8_mass,
                                             SubGenJetAK8_pt,
                                             SubGenJetAK8_eta,
                                             SubGenJetAK8_phi,
                                             SubGenJetAK8_mass,
                                             event);
            std::vector<UncScale> uncScales = {UncScale::Central, UncScale::Up, UncScale::Down};
            for (auto& uncScale : uncScales) {
                for (auto& [unc_source, unc_features] : getUncMap()) {
                    //if (FatJet_pt.size() > 0 ){
                    RVecLV shifted_p4(FatJet_pt.size());
                    if (unc_source != UncSource::Central && uncScale == UncScale::Central)
                        continue;
                    if (unc_source == UncSource::Central && uncScale != UncScale::Central)
                        continue;
                    int scale_idx = GetJesIdx(unc_source, uncScale);

                    for (int fatjet_idx = 0; fatjet_idx < FatJet_pt.size(); ++fatjet_idx) {
                        shifted_p4[fatjet_idx] = LorentzVectorM(result.pt(scale_idx)[fatjet_idx],
                                                                FatJet_eta[fatjet_idx],
                                                                FatJet_phi[fatjet_idx],
                                                                result.mass(scale_idx)[fatjet_idx]);
                    }

                    all_shifted_p4.insert({{unc_source, uncScale}, shifted_p4});
                    //std::cout << all_shifted_p4.at({unc_source, uncScale});
                    //}
                    //else{
                    //    all_shifted_p4.insert({{unc_source, uncScale},{LorentzVectorM(0.,0.,0.,0.)}});
                    //}
                }
            }
            //std::cout << FatJet_pt.size() << std::endl;
            //std::cout << event << std::endl;
            return all_shifted_p4;
        }
        RVecF getResolution(const RVecF& FatJet_pt, const RVecF& FatJet_eta, const float rho) const {
            return fjvc_total.getResolution(FatJet_pt, FatJet_eta, rho);
        }

      private:
        FatJetVariationsCalculator fjvc_total;
    };
}  // namespace correction