#pragma once

#include "correction.h"
#include "corrections.h"

namespace correction {
    class JetCorrectionProvider : public CorrectionsBase<JetCorrectionProvider> {
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

        // json_file_name - path to json file with corrections
        // e.g. /cvmfs/cms-griddata.cern.ch/cat/metadata/JME/2022_Summer2022/jet_jerc.json.gz

        // jecTag_corrName_algoType

        // jec_tag - a string describing when sample was produced and type of sample
        // e.g. Summer22_22Sep2023_V2_MC

        // algo - type of jet algorithm
        // e.g. AK4PFPuppi
        JetCorrectionProvider(std::string const& json_file_name,
                              std::string const& jetsmear_file_name,
                              std::string const& jec_tag,
                              std::string const& other_jec_tag,
                              std::string const& jer_tag,
                              std::string const& algo,
                              std::string const& fatjson_file_name,
                              std::string const& fatjec_tag,
                              std::string const& other_fatjec_tag,
                              std::string const& fatjer_tag,
                              std::string const& fatalgo,
                              std::string const& year,
                              bool is_data,
                              bool use_regrouped,
                              bool use_cmpd_jec)
            : corrset_(CorrectionSet::from_file(json_file_name)),
              jersmear_corr_(CorrectionSet::from_file(jetsmear_file_name)->at("JERSmear")),
              corr_jer_sf_(corrset_->at(jer_tag + "_ScaleFactor_" + algo)),
              corr_jer_res_(corrset_->at(jer_tag + "_PtResolution_" + algo)),
              cmpd_corr_(corrset_->compound().at(other_jec_tag + "_L1L2L3Res_" + algo)),
              corr_l1_(corrset_->at(other_jec_tag + "_L1FastJet_" + algo)),
              corr_l2_(corrset_->at(other_jec_tag + "_L2Relative_" + algo)),
              corr_l2l3res_(corrset_->at(other_jec_tag + "_L2L3Residual_" + algo)),
              fat_corrset_(CorrectionSet::from_file(fatjson_file_name)),
              fat_jersmear_corr_(CorrectionSet::from_file(jetsmear_file_name)->at("JERSmear")),
              fat_corr_jer_sf_(fat_corrset_->at(fatjer_tag + "_ScaleFactor_" + fatalgo)),
              fat_corr_jer_res_(fat_corrset_->at(fatjer_tag + "_PtResolution_" + fatalgo)),
              fat_cmpd_corr_(fat_corrset_->compound().at(other_fatjec_tag + "_L1L2L3Res_" + fatalgo)),
              is_data_(is_data),
              year_(year),
              use_cmpd_jec_(use_cmpd_jec) {
            // map with uncertainty sources should only be filled for MC
            std::cout << "JetCorrectionProvider: init" << std::endl;
            if (!is_data_) {
                auto const& unc_map_ref = use_regrouped ? unc_map_regrouped : unc_map_total;
                for (auto const& [unc_source, unc_name] : unc_map_ref) {
                    std::string full_name = jec_tag;
                    full_name += '_';
                    full_name += unc_name;
                    full_name += '_';
                    if (year_dep_map.at(unc_source)) {
                        full_name += year;
                        full_name += '_';
                    }
                    full_name += algo;
                    unc_map_[unc_source] = full_name;
                }
            }
        }

        float evaluateJECCompound(float pt_raw,
                       float eta,
                       float phi,
                       float area,
                       float rho,
                       unsigned int run,
                       bool require_run_number,
                       bool wantPhi) const {
            float sf = 1.0;

            if (require_run_number) {
                if (wantPhi) {
                    sf = cmpd_corr_->evaluate({area, eta, pt_raw, rho, phi, (float)run});
                } else {
                    sf = cmpd_corr_->evaluate({area, eta, pt_raw, rho, (float)run});
                }
            } else {
                if (wantPhi) {
                    sf = cmpd_corr_->evaluate({area, eta, pt_raw, rho, phi});
                } else {
                    sf = cmpd_corr_->evaluate({area, eta, pt_raw, rho});
                }
            }

            return sf;
        }

        float evaluateJECSeparately(float pt_raw,
                                         float eta,
                                         float phi,
                                         float area,
                                         float rho,
                                         unsigned int run,
                                         bool require_run_number,
                                         bool wantPhi,
                                         bool isdata_,
                                        bool is2024Eta2To2p5) const {

            if (pt_raw <= 0.0) return 1.0;

            float pt_after = pt_raw;

            // 2) L1FastJet
            float c1 = corr_l1_->evaluate({area, eta, pt_after, rho});
            pt_after *= c1;
            // mass_after *= c1;

            // 3) L2Relative
            float c2 = 1.0;
            if (wantPhi) {
                c2 = corr_l2_->evaluate({eta, phi, pt_after});
            } else {
                c2 = corr_l2_->evaluate({eta, pt_after});
            }
            pt_after *= c2;
            // mass_after *= c2;

            // 4) Residual (solo data)
            // For MC-truth corrected pT < 30 GeV use L2L3Residual correction factor of MC-truth corrected pT = 30 GeV in 2.0 < |eta| < 2.5

            float cRes = 1.0;
            float pt_for_corr = pt_after;

            if(is2024Eta2To2p5 and pt_after < 30. ){
                pt_for_corr = 30.;
            }
            if (isdata_ && require_run_number) {
                    cRes = corr_l2l3res_->evaluate({float(run),eta,pt_for_corr});
                // }
            } else {
                cRes = corr_l2l3res_->evaluate({eta,pt_for_corr});
            }

            pt_after *= cRes;
            // mass_after *= cRes;


            return pt_after / pt_raw ;
        }

        float getJERSmearFactor(float pt,
                        float eta,
                        float rho,
                        float gen_pt,
                        int event,
                        float& jer_res_out) const {

            float jer_sf = corr_jer_sf_->evaluate({eta, pt, "nom"});
            float jer_res = corr_jer_res_->evaluate({eta, pt, rho});
            jer_res_out = jer_res;

            float smear = jersmear_corr_->evaluate({
                pt, eta, gen_pt, rho, event, jer_res, jer_sf
            });

            return smear;
        }
        std::map<std::pair<UncSource, UncScale>, RVecLV> getShiftedP4(RVecF Jet_pt,
                                                                      const RVecF& Jet_eta,
                                                                      const RVecF& Jet_phi,
                                                                      RVecF Jet_mass,
                                                                      const RVecF& Jet_rawFactor,
                                                                      const RVecF& Jet_area,
                                                                      const float rho,
                                                                      int event,
                                                                      bool apply_jer,
                                                                      bool reapply_jec,
                                                                      bool require_run_number,
                                                                      const unsigned int run,
                                                                      bool wantPhi,
                                                                      bool apply_forward_jet_horns_fix,
                                                                      const RVecF& GenJet_pt = {},
                                                                      const RVecI& Jet_genJetIdx = {}) const {
            std::map<std::pair<UncSource, UncScale>, RVecLV> all_shifted_p4;
            std::vector<UncScale> uncScales = {UncScale::Up, UncScale::Down};

            size_t sz = Jet_pt.size();
            std::vector<float> jer_pt_resolutions(sz);
            std::vector<float> jet_pt_corr(sz);
            std::vector<float> jet_m_corr(sz);
            RVecLV central_p4(sz);
            for (size_t i = 0; i < sz; ++i) {
                jet_pt_corr[i] = Jet_pt[i];
                jet_m_corr[i] = Jet_mass[i];
                float jec_sf = 1.;
                if (reapply_jec){
                    // undo Nano, common place
                    const float raw_sf = 1.0 - Jet_rawFactor[i];
                    float pt_raw = Jet_pt[i] * raw_sf;
                    float mass_raw = Jet_mass[i] * raw_sf;
                    bool is2024Eta2To2p5 = (year_ == "2024" && std::abs(Jet_eta[i]) > 2 && std::abs(Jet_eta[i]) < 2.5);
                    if (use_cmpd_jec_ && !(is2024Eta2To2p5)){
                        jec_sf = evaluateJECCompound(pt_raw,
                                            Jet_eta[i],
                                            Jet_phi[i],
                                            Jet_area[i],
                                            rho,
                                            run,
                                            require_run_number,
                                            wantPhi);
                    }
                    else{
                        jec_sf = evaluateJECSeparately(pt_raw,
                                            Jet_eta[i],
                                            Jet_phi[i],
                                            Jet_area[i],
                                            rho,
                                            run,
                                            require_run_number,
                                            wantPhi,
                                            is_data_,
                                            is2024Eta2To2p5
                                        );
                    }
                    jet_pt_corr[i] = pt_raw * jec_sf;
                    jet_m_corr[i] = mass_raw * jec_sf;
                }

                bool is_jet_in_horn =
                    std::abs(Jet_eta[i]) > 2.5 && std::abs(Jet_eta[i]) < 3 ; // JET in horn: 2.5 < |eta| <3
                if (!is_data_ && apply_jer) {
                    bool is_gen_matched = Jet_genJetIdx[i] >= 0;
                    float gen_pt = is_gen_matched ? GenJet_pt[Jet_genJetIdx[i]] : -1.f;

                    float jer_sf = corr_jer_sf_->evaluate({Jet_eta[i], jet_pt_corr[i], "nom"});
                    float jer_pt_res = corr_jer_res_->evaluate({Jet_eta[i], jet_pt_corr[i], rho});
                    jer_pt_resolutions[i] = jer_pt_res;

                    int genjet_idx = Jet_genJetIdx[i];
                    float genjet_pt = genjet_idx != -1 ? GenJet_pt[genjet_idx] : -1.0;
                    float jersmear_factor =
                        jersmear_corr_->evaluate({jet_pt_corr[i], Jet_eta[i], genjet_pt, rho, event, jer_pt_res, jer_sf});
                    // temporary fix for jet horn issue --> do not apply JER for eta range and jet matched to genjet

                    if (is_jet_in_horn && ! (is_gen_matched)) { // for jets in horn: JER for gen-matched only (2022-2023-2024. 2025 is still in doubt ??)
                        jersmear_factor = 1.0;  // do not apply JER for jets in the horn
                    }

                    // // apply jer smearing (only for MC)
                    jet_pt_corr[i] *= jersmear_factor;
                    jet_m_corr[i] *= jersmear_factor;
                }
                central_p4[i] = LorentzVectorM(jet_pt_corr[i], Jet_eta[i], Jet_phi[i], jet_m_corr[i]);
            }

            all_shifted_p4.insert({{UncSource::Central, UncScale::Central}, central_p4});

            // apply uncertainties from uncertainty map
            // this part should not be executed for data

            if (!is_data_) {
                for (auto const& uncScale : uncScales) {
                    for (auto const& [unc_source, unc_name] : unc_map_) {
                        RVecLV shifted_p4(sz);
                        if (unc_source == UncSource::JER) {
                            if (apply_jer) {
                                for (size_t jet_idx = 0; jet_idx < sz; ++jet_idx) {
                                    float sf = 1.0;
                                    bool is_jet_in_horn = std::abs(Jet_eta[jet_idx]) >= 2.5 &&
                                                          std::abs(Jet_eta[jet_idx]) <= 3;
                                    bool is_gen_matched = Jet_genJetIdx[jet_idx] >= 0;
                                    sf += static_cast<int>(uncScale) * jer_pt_resolutions[jet_idx];
                                    if (is_jet_in_horn && !(is_gen_matched)) {
                                        sf = 1.0;  //for jets in horn: JER for gen-matched only
                                    }
                                    shifted_p4[jet_idx] = LorentzVectorM(sf * Jet_pt[jet_idx],
                                                                         Jet_eta[jet_idx],
                                                                         Jet_phi[jet_idx],
                                                                         sf * Jet_mass[jet_idx]);
                                }
                                all_shifted_p4.insert({{unc_source, uncScale}, shifted_p4});
                            }
                        } else {
                            for (size_t i = 0; i < sz; ++i) {
                                float sf = 1.0;
                                Correction::Ref corr = corrset_->at(unc_name);
                                float unc = corr->evaluate({Jet_eta[i], Jet_pt[i]});
                                sf += static_cast<int>(uncScale) * unc;
                                shifted_p4[i] = LorentzVectorM(
                                    sf * Jet_pt[i], Jet_eta[i], Jet_phi[i], sf * Jet_mass[i]);
                            }
                            all_shifted_p4.insert({{unc_source, uncScale}, shifted_p4});
                        }
                    }
                }
            }
            return all_shifted_p4;
        }

        std::map<std::pair<UncSource, UncScale>, RVecLV> getShiftedP4_FatJet(RVecF FatJet_pt,
                                                                             const RVecF& FatJet_eta,
                                                                             const RVecF& FatJet_phi,
                                                                             RVecF FatJet_mass,
                                                                             const RVecF& FatJet_rawFactor,
                                                                             const RVecF& FatJet_area,
                                                                             const float rho,
                                                                             int event,
                                                                             bool apply_jer,
                                                                             bool reapply_jec,
                                                                             bool require_run_number,
                                                                             const unsigned int run,
                                                                             bool wantPhi,
                                                                             bool apply_forward_jet_horns_fix,
                                                                             const RVecF& GenFatJet_pt = {},
                                                                             const RVecI& FatJet_genJetIdx = {}) const {
            std::map<std::pair<UncSource, UncScale>, RVecLV> all_shifted_p4;
            std::vector<UncScale> uncScales = {UncScale::Up, UncScale::Down};

            size_t sz = FatJet_pt.size();
            std::vector<float> fatjet_pt_corr(sz);
            std::vector<float> fatjet_m_corr(sz);
            std::vector<float> fatjer_pt_resolutions(sz);
            RVecLV central_p4(sz);

            for (size_t i = 0; i < sz; ++i) {
                fatjet_pt_corr[i] = FatJet_pt[i];
                fatjet_m_corr[i] = FatJet_mass[i];
                float fatjec_sf = 1.;
                if (reapply_jec){
                    // undo Nano, common place
                    const float fatjet_raw_sf = 1.0 - FatJet_rawFactor[i];
                    float fatjet_pt_raw = FatJet_pt[i] * fatjet_raw_sf;
                    float fatjet_mass_raw = FatJet_mass[i] * fatjet_raw_sf;
                    bool is2024Eta2To2p5 = (year_ == "2024" && std::abs(FatJet_eta[i]) > 2 && std::abs(FatJet_eta[i]) < 2.5);
                    if (use_cmpd_jec_ && !(is2024Eta2To2p5)){
                        fatjec_sf = evaluateJECCompound(fatjet_pt_raw,
                                            FatJet_eta[i],
                                            FatJet_phi[i],
                                            FatJet_area[i],
                                            rho,
                                            run,
                                            require_run_number,
                                            wantPhi);
                    }
                    else{
                        fatjec_sf = evaluateJECSeparately(fatjet_pt_raw,
                                            FatJet_eta[i],
                                            FatJet_phi[i],
                                            FatJet_area[i],
                                            rho,
                                            run,
                                            require_run_number,
                                            wantPhi,
                                            is_data_,
                                            is2024Eta2To2p5
                                        );
                    }
                    fatjet_pt_corr[i] = fatjet_pt_raw * fatjec_sf;
                    fatjet_m_corr[i] = fatjet_mass_raw * fatjec_sf;
                }

                bool is_fatjet_in_horn =
                    std::abs(FatJet_eta[i]) >= 2.5 && std::abs(FatJet_eta[i]) <= 3 ;
                if (!is_data_ && apply_jer) {
                    // extract jer scale factor and resolution
                    float fatjer_sf = fat_corr_jer_sf_->evaluate({FatJet_eta[i], fatjet_pt_corr[i], "nom"});
                    float fatjer_pt_res = fat_corr_jer_res_->evaluate({FatJet_eta[i], fatjet_pt_corr[i], rho});
                    fatjer_pt_resolutions[i] = fatjer_pt_res;

                    bool is_fatjet_gen_matched = FatJet_genJetIdx[i] >= 0;
                    int genjet_idx = FatJet_genJetIdx[i];
                    float genjet_pt = genjet_idx != -1 ? GenFatJet_pt[genjet_idx] : -1.0;
                    float jersmear_factor = fat_jersmear_corr_->evaluate(
                        {fatjet_pt_corr[i], FatJet_eta[i], genjet_pt, rho, event, fatjer_pt_res, fatjer_sf});
                        // temporary fix for jet horn issue --> do not apply JER for eta range and jet matched to genjet

                        if (is_fatjet_in_horn && !(is_fatjet_gen_matched)) {
                            jersmear_factor = 1.0;  //for jets in horn: JER for gen-matched only
                        }

                    // // apply jer smearing (only for MC)
                    fatjet_pt_corr[i] *= jersmear_factor;
                    fatjet_m_corr[i] *= jersmear_factor;
                }


                central_p4[i] = LorentzVectorM(fatjet_pt_corr[i], FatJet_eta[i], FatJet_phi[i], fatjet_m_corr[i]);
            }

            all_shifted_p4.insert({{UncSource::Central, UncScale::Central}, central_p4});

            // apply uncertainties from uncertainty map
            // this part should not be executed for data
            if (!is_data_) {
                for (auto const& uncScale : uncScales) {
                    for (auto const& [unc_source, unc_name] : unc_map_) {
                        RVecLV shifted_p4(sz);
                        if (unc_source == UncSource::JER) {
                            if (apply_jer) {
                                for (size_t jet_idx = 0; jet_idx < sz; ++jet_idx) {
                                    float sf = 1.0;
                                    bool is_fatjet_in_horn = std::abs(FatJet_eta[jet_idx]) >= 2.5 &&
                                                          std::abs(FatJet_eta[jet_idx]) <= 3 ;
                                    bool is_fatjet_gen_matched = FatJet_genJetIdx[jet_idx] >= 0;
                                    sf += static_cast<int>(uncScale) * fatjer_pt_resolutions[jet_idx];
                                    if (is_fatjet_in_horn && !(is_fatjet_gen_matched)) {
                                        sf = 1.0;  //for jets in horn: JER for gen-matched only
                                    }
                                    shifted_p4[jet_idx] = LorentzVectorM(sf * FatJet_pt[jet_idx],
                                                                         FatJet_eta[jet_idx],
                                                                         FatJet_phi[jet_idx],
                                                                         sf * FatJet_mass[jet_idx]);
                                }
                                all_shifted_p4.insert({{unc_source, uncScale}, shifted_p4});
                            }
                        } else {
                            for (size_t jet_idx = 0; jet_idx < sz; ++jet_idx) {
                                float sf = 1.0;
                                Correction::Ref corr = fat_corrset_->at(unc_name);
                                float unc = corr->evaluate({FatJet_eta[jet_idx], FatJet_pt[jet_idx]});
                                sf += static_cast<int>(uncScale) * unc;
                                shifted_p4[jet_idx] = LorentzVectorM(sf * FatJet_pt[jet_idx],
                                                                     FatJet_eta[jet_idx],
                                                                     FatJet_phi[jet_idx],
                                                                     sf * FatJet_mass[jet_idx]);
                            }
                            all_shifted_p4.insert({{unc_source, uncScale}, shifted_p4});
                        }
                    }
                }
            }
            return all_shifted_p4;
        }

        RVecF GetResolutions(RVecF pt, RVecF mass, RVecF const& raw_factor, RVecF const& eta, float rho) const {
            size_t sz = pt.size();
            RVecF res(sz);
            for (size_t i = 0; i < sz; ++i) {
                pt[i] *= 1.0 - raw_factor[i];
                mass[i] *= 1.0 - raw_factor[i];
                float jer_sf = corr_jer_sf_->evaluate({eta[i], pt[i], "nom"});
                float jer_pt_res = corr_jer_res_->evaluate({eta[i], pt[i], rho});
                res[i] = jer_pt_res;
            }
            return res;
        }

      private:
        std::map<UncSource, std::string> unc_map_;
        std::unique_ptr<CorrectionSet> corrset_;
        Correction::Ref jersmear_corr_;  // aka shared_ptr<Correction const>, sizeof = 8
        Correction::Ref corr_l1_;
        Correction::Ref corr_l2_;
        Correction::Ref corr_l2l3res_;
        Correction::Ref corr_jer_sf_;
        Correction::Ref corr_jer_res_;
        CompoundCorrection::Ref cmpd_corr_;
        std::unique_ptr<CorrectionSet> fat_corrset_;
        Correction::Ref fat_jersmear_corr_;  // aka shared_ptr<Correction const>, sizeof = 8
        Correction::Ref fat_corr_jer_sf_;
        Correction::Ref fat_corr_jer_res_;
        CompoundCorrection::Ref fat_cmpd_corr_;
        bool is_data_;
        std::string year_;
        bool use_cmpd_jec_;

        inline static const std::map<UncSource, std::string> unc_map_total = {{UncSource::Total, "Total"},
                                                                              {UncSource::JER, "JER"}};

        inline static const std::map<UncSource, bool> year_dep_map = {{UncSource::Central, false},
                                                                      {UncSource::JER, false},
                                                                      {UncSource::Total, false},
                                                                      {UncSource::RelativeBal, false},
                                                                      {UncSource::HF, false},
                                                                      {UncSource::BBEC1, false},
                                                                      {UncSource::EC2, false},
                                                                      {UncSource::Absolute, false},
                                                                      {UncSource::FlavorQCD, false},
                                                                      {UncSource::BBEC1_year, true},
                                                                      {UncSource::Absolute_year, true},
                                                                      {UncSource::EC2_year, true},
                                                                      {UncSource::HF_year, true},
                                                                      {UncSource::RelativeSample_year, true}};

        inline static const std::map<UncSource, std::string> unc_map_regrouped = {
            {UncSource::JER, "JER"},
            {UncSource::RelativeBal, "Regrouped_RelativeBal"},
            {UncSource::HF, "Regrouped_HF"},
            {UncSource::BBEC1, "Regrouped_BBEC1"},
            {UncSource::EC2, "Regrouped_EC2"},
            {UncSource::Absolute, "Regrouped_Absolute"},
            {UncSource::FlavorQCD, "Regrouped_FlavorQCD"},
            {UncSource::BBEC1_year, "Regrouped_BBEC1"},
            {UncSource::Absolute_year, "Regrouped_Absolute"},
            {UncSource::EC2_year, "Regrouped_EC2"},
            {UncSource::HF_year, "Regrouped_RelativeStatHF"},
            {UncSource::RelativeSample_year, "Regrouped_RelativeSample"}};
    };

}  // namespace correction
