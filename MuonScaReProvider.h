#pragma once

#include "correction.h"
#include "corrections.h"

#include <boost/math/special_functions/erf.hpp>

namespace correction {

    class MuonScaReCorrProvider {
      public:
        // The two uncertainties of the MUO scale-and-resolution correction, as in the MUO recipe: the
        // statistical uncertainty of the scale correction and that of the MC smearing factor k.
        enum class UncSource : int {
            Central = -1,
            MuScale = 0,
            MuRes = 1,
        };
        static const std::string& getScaleStr(UncScale scale) {
            static const std::map<UncScale, std::string> names = {
                {UncScale::Down, "dn"},
                {UncScale::Central, "nom"},
                {UncScale::Up, "up"},
            };
            return names.at(scale);
        }

        static bool sourceApplies(UncSource source) {
            return source == UncSource::MuScale || source == UncSource::MuRes;
        }

        MuonScaReCorrProvider(const std::string& jsonFile, const std::string& jsonFileVXBS)
            : cset(CorrectionSet::from_file(jsonFile)), cset_vxbs(CorrectionSet::from_file(jsonFileVXBS)) {}

        const CorrectionSet& getCSet(bool useVXBS) const { return useVXBS ? *cset_vxbs : *cset; }

        LorentzVectorM getES(const float Muon_pt,
                             const float Muon_eta,
                             const float Muon_phi,
                             const float Muon_mass,
                             const int Muon_charge,
                             const unsigned char Muon_nTrackerLayers,
                             const bool is_data,
                             const int evtNumber,
                             const int lumiNumber,
                             UncSource source,
                             UncScale scale,
                             bool useVXBS = false) const {
            // Nominal, data and MC: the scale correction; MC only: then the smearing.
            const double pt_scaled = pt_scale(is_data, Muon_pt, Muon_eta, Muon_phi, Muon_charge, useVXBS);
            const double pt_nominal =
                is_data ? pt_scaled
                        : pt_resol(pt_scaled, Muon_eta, Muon_phi, Muon_nTrackerLayers, evtNumber, lumiNumber, useVXBS);

            // Variations (MC only) are taken around the nominal corrected muon, as in the MUO recipe:
            // the scale uncertainty shifts the fully corrected pT, the resolution uncertainty rescales
            // the smearing that was applied (k -> k +- k_unc) for the same random number. Varying the
            // uncorrected pT instead drops the nominal corrections from both Up and Down.
            double pt_out = pt_nominal;
            if (!is_data && sourceApplies(source) && scale != UncScale::Central) {
                const std::string& updn = getScaleStr(scale);
                if (source == UncSource::MuScale)
                    pt_out = pt_scale_var(pt_nominal, Muon_eta, Muon_phi, Muon_charge, updn, useVXBS);
                else
                    pt_out = pt_resol_var(pt_scaled, pt_nominal, Muon_eta, updn, useVXBS);
            }
            return LorentzVectorM(pt_out, Muon_eta, Muon_phi, Muon_mass);
        }
        RVecLV getES(const RVecI& id_selection,
                     const RVecF& Muon_pt,
                     const RVecF& Muon_eta,
                     const RVecF& Muon_phi,
                     const RVecF& Muon_mass,
                     const RVecI& Muon_charge,
                     const RVecUC& Muon_nTrackerLayers,
                     const bool is_data,
                     const int evtNumber,
                     const int lumiNumber,
                     UncSource source,
                     UncScale scale,
                     bool useVXBS = false) const {
            const size_t nMuons = Muon_pt.size();
            RVecLV out(nMuons);

            for (size_t i = 0; i < nMuons; ++i) {
                if (id_selection[i] <= 0) {
                    // id selection is using Muon_looseId at anaTuple, but mu1_pt at histTuple (h_mumu)
                    out[i] = LorentzVectorM(Muon_pt[i], Muon_eta[i], Muon_phi[i], Muon_mass[i]);
                } else {
                    out[i] = getES(Muon_pt[i],
                                   Muon_eta[i],
                                   Muon_phi[i],
                                   Muon_mass[i],
                                   Muon_charge[i],
                                   Muon_nTrackerLayers[i],
                                   is_data,
                                   evtNumber,
                                   lumiNumber,
                                   source,
                                   scale,
                                   useVXBS);
                }
            }

            return out;
        }

      private:
        std::unique_ptr<CorrectionSet> cset;
        std::unique_ptr<CorrectionSet> cset_vxbs;

      private:
        double get_rndm(double eta, double phi, float nL, int evtNumber, int lumiNumber, bool useVXBS = false) const {
            const auto& cs = getCSet(useVXBS);
            // obtain parameters from correctionlib
            double mean = cs.at("cb_params")->evaluate({abs(eta), nL, 0});
            double sigma = cs.at("cb_params")->evaluate({abs(eta), nL, 1});
            double n = cs.at("cb_params")->evaluate({abs(eta), nL, 2});
            double alpha = cs.at("cb_params")->evaluate({abs(eta), nL, 3});

            // instantiate CB and get random number following the CB
            analysis::CrystalBall cb(mean, sigma, alpha, n);
            double rndm = cs.at("RandomSmearing")->evaluate({(int)evtNumber, (int)lumiNumber, phi});
            return cb.invcdf(rndm);
        }

        double get_std(double pt, double eta, float nL, bool useVXBS = false) const {
            const auto& cs = getCSet(useVXBS);
            // obtain paramters from correctionlib
            double param_0 = cs.at("poly_params")->evaluate({abs(eta), nL, 0});
            double param_1 = cs.at("poly_params")->evaluate({abs(eta), nL, 1});
            double param_2 = cs.at("poly_params")->evaluate({abs(eta), nL, 2});

            // calculate value and return max(0, val)
            double sigma = param_0 + param_1 * pt + param_2 * pt * pt;
            if (sigma < 0)
                sigma = 0;
            return sigma;
        }

        double get_k(double eta, string var, bool useVXBS = false) const {
            const auto& cs = getCSet(useVXBS);
            // obtain parameters from correctionlib
            double k_data = cs.at("k_data")->evaluate({abs(eta), var});
            double k_mc = cs.at("k_mc")->evaluate({abs(eta), var});

            // calculate residual smearing factor
            // return 0 if smearing in MC already larger than in data
            double k = 0;
            if (k_mc < k_data)
                k = sqrt(k_data * k_data - k_mc * k_mc);
            return k;
        }

        double pt_resol(double pt,
                        double eta,
                        double phi,
                        float nL,
                        int evtNumber,
                        int lumiNumber,
                        bool useVXBS = false,
                        double low_pt_threshold = 20) const {
            // load correction values
            double rndm = (double)get_rndm(eta, phi, nL, evtNumber, lumiNumber, useVXBS);
            double std = (double)get_std(pt, eta, nL, useVXBS);
            double k = (double)get_k(eta, "nom", useVXBS);

            // calculate corrected value and return original value if a parameter is nan
            double ptc = pt * (1 + k * std * rndm);
            if (isnan(ptc))
                ptc = pt;
            if (ptc / pt > 2 || ptc / pt < 0.1 || ptc < 0 || pt < low_pt_threshold || pt > 200) {
                ptc = pt;
            }
            // For muons outside the validated pT range (including pT < low_pt_threshold),
            // or when the smeared pT is clearly unphysical, we return the original pT
            // to avoid applying resolution corrections where they are not defined.
            return ptc;
        }

        double pt_resol_var(double pt_woresol, double pt_wresol, double eta, string updn, bool useVXBS = false) const {
            const auto& cs = getCSet(useVXBS);
            double k = (double)get_k(eta, "nom", useVXBS);

            if (k == 0)
                return pt_wresol;

            double k_unc = cs.at("k_mc")->evaluate({abs(eta), "stat"});

            double std_x_rndm = (pt_wresol / pt_woresol - 1) / k;

            double pt_var = pt_wresol;

            if (updn == "up") {
                pt_var = pt_woresol * (1 + (k + k_unc) * std_x_rndm);
            } else if (updn == "dn") {
                pt_var = pt_woresol * (1 + (k - k_unc) * std_x_rndm);
            } else {
                cout << "ERROR: updn must be 'up' or 'dn'" << endl;
            }
            if (pt_var / pt_woresol > 2 || pt_var / pt_woresol < 0.1 || pt_var < 0) {
                pt_var = pt_woresol;
            }

            return pt_var;
        }

        double pt_scale(bool is_data,
                        double pt,
                        double eta,
                        double phi,
                        int charge,
                        bool useVXBS = false,
                        double low_pt_threshold = 20) const {
            const auto& cs = getCSet(useVXBS);
            // use right correction
            string dtmc = "mc";
            if (is_data)
                dtmc = "data";

            double a = cs.at("a_" + dtmc)->evaluate({eta, phi, "nom"});
            double m = cs.at("m_" + dtmc)->evaluate({eta, phi, "nom"});
            if (pt < low_pt_threshold)
                return pt;

            return 1. / (m / pt + charge * a);
        }

        double pt_scale_var(double pt, double eta, double phi, int charge, string updn, bool useVXBS = false) const {
            const auto& cs = getCSet(useVXBS);
            double stat_a = cs.at("a_mc")->evaluate({eta, phi, "stat"});
            double stat_m = cs.at("m_mc")->evaluate({eta, phi, "stat"});
            double stat_rho = cs.at("m_mc")->evaluate({eta, phi, "rho_stat"});

            double unc =
                pt * pt *
                sqrt(stat_m * stat_m / (pt * pt) + stat_a * stat_a + 2 * charge * stat_rho * stat_m / pt * stat_a);

            double pt_var = pt;

            if (updn == "up") {
                pt_var = pt + unc;
            } else if (updn == "dn") {
                pt_var = pt - unc;
            }

            return pt_var;
        }
    };
}  // namespace correction
