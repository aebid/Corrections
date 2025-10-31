#pragma once

#include "correction.h"
#include "corrections.h"
#include "SF_Met.cc"

namespace correction {

    class TrigCorrProvider : public CorrectionsBase<TrigCorrProvider> {
      public:
        enum class UncSource : int {
            Central = -1,
            ditau_DM0 = 0,
            ditau_DM1 = 1,
            ditau_3Prong = 2,
            singleMu = 3,
            singleMu50or24 = 4,
            singleMu50 = 5,
            singleEle = 6,
            etau_ele = 7,
            etau_DM0 = 8,
            etau_DM1 = 9,
            etau_3Prong = 10,
            mutau_mu = 11,
            mutau_DM0 = 12,
            mutau_DM1 = 13,
            mutau_3Prong = 14,
        };
        using wpsMapType = std::map<Channel, std::vector<std::pair<std::string, int> > >;
        static bool isTwoProngDM(int dm) {
            static const std::set<int> twoProngDMs = {5, 6};
            return twoProngDMs.count(dm);
        }
        static const std::string& getTauScaleStr(UncScale scale) {
            static const std::map<UncScale, std::string> tau_names = {
                {UncScale::Down, "down"},
                {UncScale::Central, "nom"},
                {UncScale::Up, "up"},
            };
            return tau_names.at(scale);
        }
        static const std::string& getMuScaleStr(UncScale scale) {
            static const std::map<UncScale, std::string> tau_names = {
                {UncScale::Down, "systdown"},
                {UncScale::Central, "sf"},
                {UncScale::Up, "systup"},
            };
            return tau_names.at(scale);
        }
        static bool sourceApplies_tau_fromCorrLib(UncSource source, int decayMode, const std::string& trg_type) {
            if (trg_type == "ditau") {
                if (source == UncSource::ditau_DM0 && decayMode == 0)
                    return true;
                if (source == UncSource::ditau_DM1 && (decayMode == 1 || decayMode == 2))
                    return true;
                if (source == UncSource::ditau_3Prong && (decayMode == 10 || decayMode == 11))
                    return true;
            }
            if (trg_type == "mutau") {
                if (source == UncSource::mutau_DM0 && decayMode == 0)
                    return true;
                if (source == UncSource::mutau_DM1 && (decayMode == 1 || decayMode == 2))
                    return true;
                if (source == UncSource::mutau_3Prong && (decayMode == 10 || decayMode == 11))
                    return true;
            }
            if (trg_type == "etau") {
                if (source == UncSource::etau_DM0 && decayMode == 0)
                    return true;
                if (source == UncSource::etau_DM1 && (decayMode == 1 || decayMode == 2))
                    return true;
                if (source == UncSource::etau_3Prong && (decayMode == 10 || decayMode == 11))
                    return true;
            }
            return false;
        }
        /*const std::vector<std::string>& mu_trigger,*/
        TrigCorrProvider(const std::string& tauFileName,
                         const std::string& deepTauVersion,
                         const wpsMapType& wps_map,
                         const std::string& muFileName,
                         const std::string& period,
                         const std::vector<std::string>& hist_mu_name,
                         const std::vector<std::string>& hist_eff_mu_name,
                         const std::string& eleFileName,
                         const std::string& eTauFileName,
                         const std::string& muTauFileName,
                         const std::string& metFileName)
            : tau_corrections_(CorrectionSet::from_file(tauFileName)),
              tau_trg_(tau_corrections_->at("tau_trigger")),
              deepTauVersion_(deepTauVersion),
              wps_map_(wps_map),
              //mu_corrections_(CorrectionSet::from_file(muFileName)),
              //mu_trg_(mu_corrections_->at(mu_trigger)),
              period_(period) {
            auto eTauFile = root_ext::OpenRootFile(eTauFileName);
            histo_eTau_ele_SF.reset(root_ext::ReadCloneObject<TH2>(*eTauFile, "SF2D", "SF2D", true));
            histo_eTau_ele_data.reset(root_ext::ReadCloneObject<TH2>(*eTauFile, "eff_data", "eff_data", true));
            histo_eTau_ele_MC.reset(root_ext::ReadCloneObject<TH2>(*eTauFile, "eff_mc", "eff_mc", true));

            auto muTauFile = root_ext::OpenRootFile(muTauFileName);
            histo_muTau_mu_SF.reset(root_ext::ReadCloneObject<TH2>(*muTauFile, "SF2D", "SF2D", true));
            histo_muTau_mu_data.reset(root_ext::ReadCloneObject<TH2>(*muTauFile, "eff_data", "eff_data", true));
            histo_muTau_mu_MC.reset(root_ext::ReadCloneObject<TH2>(*muTauFile, "eff_mc", "eff_mc", true));

            auto eleFile = root_ext::OpenRootFile(eleFileName);
            histo_ele_SF.reset(root_ext::ReadCloneObject<TH2>(*eleFile, "SF2D", "SF2D", true));
            histo_ele_data.reset(root_ext::ReadCloneObject<TH2>(*eleFile, "eff_data", "eff_data", true));
            histo_ele_MC.reset(root_ext::ReadCloneObject<TH2>(*eleFile, "eff_mc", "eff_mc", true));

            auto muFile = root_ext::OpenRootFile(muFileName);
            histo_mu_SF.reset(
                root_ext::ReadCloneObject<TH2>(*muFile, hist_mu_name[0].c_str(), hist_mu_name[0].c_str(), true));
            histo_mu_SF_data.reset(root_ext::ReadCloneObject<TH2>(
                *muFile, hist_mu_name[0].c_str(), (hist_mu_name[0] + "_efficiencyData").c_str(), true));
            histo_mu_SF_MC.reset(root_ext::ReadCloneObject<TH2>(
                *muFile, hist_mu_name[0].c_str(), (hist_mu_name[0] + "_efficiencyMC").c_str(), true));
            histo_mu_SF_50or24.reset(
                root_ext::ReadCloneObject<TH2>(*muFile, hist_mu_name[1].c_str(), hist_mu_name[1].c_str(), true));
            histo_mu_SF_50.reset(
                root_ext::ReadCloneObject<TH2>(*muFile, hist_mu_name[2].c_str(), hist_mu_name[2].c_str(), true));

            auto metFile = root_ext::OpenRootFile(metFileName);
            funcSF.reset(ReadCloneObjectTF1<TF1>(*metFile, "SigmoidFuncSF", "SigmoidFuncSF"));
            funcData.reset(ReadCloneObjectTF1<TF1>(*metFile, "SigmoidFuncData", "SigmoidFuncData"));
            funcMC.reset(ReadCloneObjectTF1<TF1>(*metFile, "SigmoidFuncMC", "SigmoidFuncMC"));
        }

        float getTauEffData_fromCorrLib(const LorentzVectorM& Tau_p4,
                                        int Tau_decayMode,
                                        const std::string& trg_type,
                                        Channel ch,
                                        UncSource source,
                                        UncScale scale) const {
            if (isTwoProngDM(Tau_decayMode))
                throw std::runtime_error("no SF for two prong tau decay modes");
            const auto& wpVSjet = wps_map_.count(ch) ? wps_map_.at(ch).at(2).first : "Loose";
            const UncScale tau_scale =
                sourceApplies_tau_fromCorrLib(source, Tau_decayMode, trg_type) ? scale : UncScale::Central;
            const std::string& scale_str = getTauScaleStr(tau_scale);

            auto effdata = tau_trg_->evaluate({Tau_p4.pt(), Tau_decayMode, trg_type, wpVSjet, "eff_data", scale_str});
            return sourceApplies_tau_fromCorrLib(source, Tau_decayMode, trg_type) ? effdata : 1.f;
            // return tau_trg_->evaluate({Tau_p4.pt(), Tau_decayMode, trg_type, wpVSjet,"eff_data", scale_str});
        }
        float getTauEffMC_fromCorrLib(const LorentzVectorM& Tau_p4,
                                      int Tau_decayMode,
                                      const std::string& trg_type,
                                      Channel ch,
                                      UncSource source,
                                      UncScale scale) const {
            if (isTwoProngDM(Tau_decayMode))
                throw std::runtime_error("no SF for two prong tau decay modes");
            const auto& wpVSjet = wps_map_.count(ch) ? wps_map_.at(ch).at(2).first : "Loose";
            const UncScale tau_scale =
                sourceApplies_tau_fromCorrLib(source, Tau_decayMode, trg_type) ? scale : UncScale::Central;
            const std::string& scale_str = getTauScaleStr(tau_scale);
            auto effmc = tau_trg_->evaluate({Tau_p4.pt(), Tau_decayMode, trg_type, wpVSjet, "eff_mc", scale_str});
            return sourceApplies_tau_fromCorrLib(source, Tau_decayMode, trg_type) ? effmc : 1.f;
        }

        float getTauSF_fromCorrLib(const LorentzVectorM& Tau_p4,
                                   int Tau_decayMode,
                                   const std::string& trg_type,
                                   Channel ch,
                                   UncSource source,
                                   UncScale scale) const {
            if (isTwoProngDM(Tau_decayMode))
                throw std::runtime_error("no SF for two prong tau decay modes");
            const auto& wpVSjet = wps_map_.count(ch) ? wps_map_.at(ch).at(2).first : "Loose";
            // std::cout<< "WP VS jet = " ;
            // std::cout << wpVSjet << std::endl ;
            const UncScale tau_scale =
                sourceApplies_tau_fromCorrLib(source, Tau_decayMode, trg_type) ? scale : UncScale::Central;
            // std::cout<< "decay mode = " ;
            // std::cout << Tau_decayMode << "\n trigger = " << trg_type << std::endl;
            const std::string& scale_str = getTauScaleStr(tau_scale);
            // std::cout<< "scale = " ;
            // std::cout << scale_str << std::endl;
            // std::cout << "pt " << Tau_p4.pt()<< std::endl;
            auto sf = tau_trg_->evaluate({Tau_p4.pt(), Tau_decayMode, trg_type, wpVSjet, "sf", scale_str});
            // std::cout<< "sf = " ;
            // std::cout << sf << std::endl;
            // std::cout << std::endl;
            return sourceApplies_tau_fromCorrLib(source, Tau_decayMode, trg_type) ? sf : 1.f;
        }

        float getMETTrgSF(const std::string year,
                          const float& metnomu_pt,
                          const float& metnomu_phi,
                          UncScale scale) const {
            ScaleFactorMET metSF(year, funcSF.get(), funcMC.get(), funcData.get());
            float tau_thresh;
            float met_thresh = metSF.getMinThreshold();
            LorentzVectorM vMETnoMu4(metnomu_pt, 0, metnomu_phi, 0);
            TVector2 vMETnoMu2(vMETnoMu4.Px(), vMETnoMu4.Py());

            /*
        if (PERIOD=="2016preVFP" or PERIOD=="2016postVFP") {
            tau_thresh = 130.;
        }
        else if (PERIOD=="2017") {
            tau_thresh = 190.;
        }
        else { // 2018
            tau_thresh = 190.;
        }*/
            if (scale == UncScale::Central) {
                return metSF.getSF(vMETnoMu2.Mod());
            }
            return scale == UncScale::Up ? metSF.getSF(vMETnoMu2.Mod()) + metSF.getSFError(vMETnoMu2.Mod())
                                         : metSF.getSF(vMETnoMu2.Mod()) - metSF.getSFError(vMETnoMu2.Mod());
        }

        float getSFsFromHisto(const std::unique_ptr<TH2>& histo,
                              const LorentzVectorM& part_p4,
                              UncScale scale,
                              bool inverted_bins,
                              bool wantAbsEta,
                              bool verbose = false) const {
            const auto x_axis = histo->GetXaxis();
            const auto eta = wantAbsEta ? std::abs(part_p4.Eta()) : part_p4.Eta();
            int x_bin = x_axis->FindFixBin(part_p4.Pt());
            if (inverted_bins) {
                x_bin = x_axis->FindFixBin(eta);
            }
            if (x_bin < 1)
                x_bin = 1;
            if (x_bin > x_axis->GetNbins())
                x_bin = x_axis->GetNbins();
            const auto y_axis = histo->GetYaxis();

            int y_bin = y_axis->FindFixBin(eta);
            if (inverted_bins) {
                y_bin = y_axis->FindFixBin(part_p4.Pt());
            }
            if (y_bin < 1)
                y_bin = 1;
            if (y_bin > y_axis->GetNbins())
                y_bin = y_axis->GetNbins();
            // if (verbose)
            // {std::cout << "x, y = " << x_bin << "," << y_bin << " bin content " << histo->GetBinContent(x_bin,y_bin) << " scale " << static_cast<int>(scale) << " bin error " << histo->GetBinError(x_bin,y_bin) << std::endl;}
            return histo->GetBinContent(x_bin, y_bin) + static_cast<int>(scale) * histo->GetBinError(x_bin, y_bin);
        }
        float getEffMC_fromRootFile(const LorentzVectorM& part_p4,
                                    UncSource source,
                                    UncScale scale,
                                    bool wantAbsEta = false,
                                    bool isMuTau = false) const {
            float sf = 1.;
            if (source == UncSource::singleMu) {
                const UncScale mu_scale = source == UncSource::singleMu ? scale : UncScale::Central;
                sf = getSFsFromHisto(histo_mu_SF_MC, part_p4, mu_scale, true, true);
            }
            if (source == UncSource::singleEle) {
                const UncScale ele_scale = source == UncSource::singleEle ? scale : UncScale::Central;
                sf = getSFsFromHisto(histo_ele_MC, part_p4, ele_scale, false, false);
                // std::cout << "applying SF single ele for " << static_cast<int>(ele_scale) << " scale " << sf << std::endl;
            }
            if (source == UncSource::mutau_mu || source == UncSource::etau_ele) {
                UncScale xTrg_scale = UncScale::Central;
                if (source == UncSource::mutau_mu && isMuTau) {
                    xTrg_scale = scale;
                    sf = getSFsFromHisto(histo_muTau_mu_MC, part_p4, xTrg_scale, false, false);
                }
                if (source == UncSource::etau_ele && !(isMuTau)) {
                    xTrg_scale = scale;
                    sf = getSFsFromHisto(histo_eTau_ele_MC, part_p4, xTrg_scale, false, false);
                }
            }
            return sf;
        }

        float getEffData_fromRootFile(const LorentzVectorM& part_p4,
                                      UncSource source,
                                      UncScale scale,
                                      bool wantAbsEta = false,
                                      bool isMuTau = false) const {
            float sf = 1.;
            if (source == UncSource::singleMu) {
                const UncScale mu_scale = source == UncSource::singleMu ? scale : UncScale::Central;
                sf = getSFsFromHisto(histo_mu_SF_data, part_p4, mu_scale, true, true);
            }
            if (source == UncSource::singleEle) {
                const UncScale ele_scale = source == UncSource::singleEle ? scale : UncScale::Central;
                sf = getSFsFromHisto(histo_ele_data, part_p4, ele_scale, false, false);
            }
            if (source == UncSource::mutau_mu || source == UncSource::etau_ele) {
                UncScale xTrg_scale = UncScale::Central;
                if (source == UncSource::mutau_mu && isMuTau) {
                    xTrg_scale = scale;
                    sf = getSFsFromHisto(histo_muTau_mu_data, part_p4, xTrg_scale, false, false);
                }
                if (source == UncSource::etau_ele && !(isMuTau)) {
                    xTrg_scale = scale;
                    sf = getSFsFromHisto(histo_eTau_ele_data, part_p4, xTrg_scale, false, false);
                }
            }
            return sf;
        }

        float getSF_fromRootFile(const LorentzVectorM& part_p4,
                                 UncSource source,
                                 UncScale scale,
                                 bool wantAbsEta = false,
                                 bool isMuTau = false) const {
            //bool wantAbsEta = isMuTau ? true : false;
            float sf = 1.;
            if (source == UncSource::singleMu) {
                const UncScale mu_scale = source == UncSource::singleMu ? scale : UncScale::Central;
                sf = getSFsFromHisto(histo_mu_SF, part_p4, mu_scale, true, true);
            }
            if (source == UncSource::singleMu50or24) {
                const UncScale mu_scale = source == UncSource::singleMu50or24 ? scale : UncScale::Central;
                sf = getSFsFromHisto(histo_mu_SF_50or24, part_p4, mu_scale, false, false);
            }

            if (source == UncSource::singleMu50) {
                const UncScale mu_scale = source == UncSource::singleMu50 ? scale : UncScale::Central;
                sf = getSFsFromHisto(histo_mu_SF_50, part_p4, mu_scale, false, false);
            }
            if (source == UncSource::singleEle) {
                const UncScale ele_scale = source == UncSource::singleEle ? scale : UncScale::Central;
                sf = getSFsFromHisto(histo_ele_SF, part_p4, ele_scale, false, false);
                // std::cout << sf << std::endl;
            }
            if (source == UncSource::mutau_mu || source == UncSource::etau_ele) {
                UncScale xTrg_scale = UncScale::Central;
                if (source == UncSource::mutau_mu && isMuTau) {
                    xTrg_scale = scale;
                    sf = getSFsFromHisto(histo_muTau_mu_SF, part_p4, xTrg_scale, false, false);
                }
                if (source == UncSource::etau_ele && !(isMuTau)) {
                    xTrg_scale = scale;
                    sf = getSFsFromHisto(histo_eTau_ele_SF, part_p4, xTrg_scale, false, false);
                }
            }
            return sf;
        }

        float getEleSF_fromRootFile(const LorentzVectorM& Ele_p4, UncSource source, UncScale scale) const {
            const UncScale ele_scale = source == UncSource::singleEle ? scale : UncScale::Central;
            const auto x_axis = histo_ele_SF->GetXaxis();
            int x_bin = x_axis->FindFixBin(Ele_p4.Eta());
            if (x_bin < 1)
                x_bin = 1;
            if (x_bin > x_axis->GetNbins())
                x_bin = x_axis->GetNbins();
            const auto y_axis = histo_ele_SF->GetYaxis();

            int y_bin = y_axis->FindFixBin(Ele_p4.Pt());
            if (y_bin < 1)
                y_bin = 1;
            if (y_bin > y_axis->GetNbins())
                y_bin = y_axis->GetNbins();

            return histo_ele_SF->GetBinContent(x_bin, y_bin) +
                   static_cast<int>(ele_scale) * histo_ele_SF->GetBinError(x_bin, y_bin);
        }

        float getXTrgSF_fromRootFile(const LorentzVectorM& leg_p4,
                                     UncSource source,
                                     UncScale scale,
                                     bool isMuTau) const {
            UncScale xTrg_scale = UncScale::Central;
            if (source == UncSource::mutau_mu && isMuTau) {
                xTrg_scale = scale;
            }
            if (source == UncSource::etau_ele && !isMuTau) {
                xTrg_scale = scale;
            }
            const TH2* hist_xTrg = nullptr;

            if (isMuTau) {
                if (histo_muTau_mu_SF) {
                    hist_xTrg = histo_muTau_mu_SF.get();
                }
            } else {
                if (histo_eTau_ele_SF) {
                    hist_xTrg = histo_eTau_ele_SF.get();
                }
            }
            if (!hist_xTrg) {
                return 1.0;
            }
            const auto x_axis = hist_xTrg->GetXaxis();
            int x_bin = x_axis->FindFixBin(leg_p4.Pt());
            if (x_bin < 1)
                x_bin = 1;
            if (x_bin > x_axis->GetNbins())
                x_bin = x_axis->GetNbins();
            const auto y_axis = hist_xTrg->GetYaxis();

            auto eta_value = isMuTau ? std::abs(leg_p4.Eta()) : leg_p4.Eta();
            int y_bin = y_axis->FindFixBin(eta_value);
            if (y_bin < 1)
                y_bin = 1;
            if (y_bin > y_axis->GetNbins())
                y_bin = y_axis->GetNbins();

            return hist_xTrg->GetBinContent(x_bin, y_bin) +
                   static_cast<int>(xTrg_scale) * hist_xTrg->GetBinError(x_bin, y_bin);
        }

      private:
        template <typename Object>
        Object* ReadObjectTF1(TDirectory& file, const std::string& name) {
            if (!name.size())
                throw analysis::exception("Can't read nameless object.");
            TObject* root_object = file.Get(name.c_str());
            if (!root_object)
                throw analysis::exception("Object '%1%' not found in '%2%'.") % name % file.GetName();
            Object* object = dynamic_cast<Object*>(root_object);
            if (!object)
                throw analysis::exception("Wrong object type '%1%' for object '%2%' in '%3%'.") %
                    typeid(Object).name() % name % file.GetName();
            return object;
        }

        template <typename Object>
        Object* CloneObjectTF1(const Object& original_object, const std::string& new_name = "") {
            const std::string new_object_name = new_name.size() ? new_name : original_object.GetName();
            Object* new_object = dynamic_cast<Object*>(original_object.Clone(new_object_name.c_str()));
            if (!new_object)
                throw analysis::exception("Type error while cloning object '%1%'.") % original_object.GetName();
            return new_object;
        }

        template <typename Object>
        Object* ReadCloneObjectTF1(TDirectory& file,
                                   const std::string& original_name,
                                   const std::string& new_name = "") {
            Object* original_object = ReadObjectTF1<Object>(file, original_name);
            return CloneObjectTF1(*original_object, new_name);
        }

      private:
        std::unique_ptr<CorrectionSet> tau_corrections_;
        Correction::Ref tau_trg_;
        const std::string deepTauVersion_;
        const wpsMapType wps_map_;
        //std::unique_ptr<CorrectionSet> mu_corrections_;
        Correction::Ref mu_trg_;
        const std::string period_;
        std::unique_ptr<TH2> histo_ele_SF;
        std::unique_ptr<TH2> histo_ele_data;
        std::unique_ptr<TH2> histo_ele_MC;

        std::unique_ptr<TH2> histo_eTau_ele_SF;
        std::unique_ptr<TH2> histo_eTau_ele_data;
        std::unique_ptr<TH2> histo_eTau_ele_MC;

        std::unique_ptr<TH2> histo_muTau_mu_SF;
        std::unique_ptr<TH2> histo_muTau_mu_data;
        std::unique_ptr<TH2> histo_muTau_mu_MC;

        std::unique_ptr<TH2> histo_mu_SF;
        std::unique_ptr<TH2> histo_mu_SF_data;
        std::unique_ptr<TH2> histo_mu_SF_MC;

        std::unique_ptr<TH2> histo_mu_SF_50or24;
        std::unique_ptr<TH2> histo_mu_SF_50;

        std::unique_ptr<TF1> funcSF;
        std::unique_ptr<TF1> funcData;
        std::unique_ptr<TF1> funcMC;
    };

}  // namespace correction