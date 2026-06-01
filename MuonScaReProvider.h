#pragma once

#include "correction.h"
#include "corrections.h"

#include <boost/math/special_functions/erf.hpp>

namespace correction {

    class MuonScaReCorrProvider : public CorrectionsBase<MuonScaReCorrProvider> {
      public:
        enum class UncSource : int {
            Central = -1,
            ScaRe = 0,
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
            if (source == UncSource::ScaRe)
                return true;
            return false;
        }

        MuonScaReCorrProvider(const std::string& jsonFile) : cset(CorrectionSet::from_file(jsonFile)) {}

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
                     UncScale scale) const {
                const UncScale mu_scale = sourceApplies(source) ? scale : UncScale::Central; 
                const std::string& scale_str = getScaleStr(mu_scale);
                const int isData = is_data ? 1 : 0;
                const double muon_pt_scaled = mu_scale == UncScale::Central ? pt_scale(is_data, Muon_pt, Muon_eta, Muon_phi, Muon_charge) : pt_scale_var(Muon_pt, Muon_eta, Muon_phi, Muon_charge, scale_str);
                double muon_pt_resol = muon_pt_scaled;
                if (!isData) {
                    muon_pt_resol = mu_scale == UncScale::Central ? pt_resol(muon_pt_scaled, Muon_eta, Muon_phi, Muon_nTrackerLayers, evtNumber, lumiNumber) : pt_resol_var(muon_pt_scaled, muon_pt_resol, Muon_eta, scale_str);

                }
                const LorentzVectorM muon_p4_ScaRe = LorentzVectorM(muon_pt_resol, Muon_eta, Muon_phi, Muon_mass);
                return muon_p4_ScaRe;
        }
        RVecLV getES(const RVecF& Muon_pt,
                const RVecF& Muon_eta,
                const RVecF& Muon_phi,
                const RVecF& Muon_mass,
                const RVecI   Muon_charge,
                const RVecUC& Muon_nTrackerLayers,
                const bool is_data,
                const int evtNumber,
                const int lumiNumber,
                UncSource source,
                UncScale scale) const
            {
                const size_t nMuons = Muon_pt.size();
                RVecLV out(nMuons);

                for (size_t i = 0; i < nMuons; ++i) {
                    out[i] = getES(
                        Muon_pt[i],
                        Muon_eta[i],
                        Muon_phi[i],
                        Muon_mass[i],
                        Muon_charge[i],
                        Muon_nTrackerLayers[i],
                        is_data,
                        evtNumber,
                        lumiNumber,
                        source,
                        scale
                    );
                }

                return out;
            }

      private:
        std::unique_ptr<CorrectionSet> cset;

      private:
        double get_rndm(double eta, double phi, float nL, int evtNumber, int lumiNumber) const {
            // obtain parameters from correctionlib
            double mean = cset->at("cb_params")->evaluate({abs(eta), nL, 0});
            double sigma = cset->at("cb_params")->evaluate({abs(eta), nL, 1});
            double n = cset->at("cb_params")->evaluate({abs(eta), nL, 2});
            double alpha = cset->at("cb_params")->evaluate({abs(eta), nL, 3});

            // instantiate CB and get random number following the CB
            analysis::CrystalBall cb(mean, sigma, alpha, n);
            double rndm = cset->at("RandomSmearing")->evaluate({(int)evtNumber, (int)lumiNumber, phi});
            return cb.invcdf(rndm);
        }

        double get_std(double pt, double eta, float nL) const {

            // obtain paramters from correctionlib
            double param_0 = cset->at("poly_params")->evaluate({abs(eta), nL, 0});
            double param_1 = cset->at("poly_params")->evaluate({abs(eta), nL, 1});
            double param_2 = cset->at("poly_params")->evaluate({abs(eta), nL, 2});

            // calculate value and return max(0, val)
            double sigma = param_0 + param_1 * pt + param_2 * pt*pt;
            if (sigma < 0) sigma = 0;
            return sigma;
        }

        double get_k(double eta, string var) const {

            // obtain parameters from correctionlib
            double k_data = cset->at("k_data")->evaluate({abs(eta), var});
            double k_mc = cset->at("k_mc")->evaluate({abs(eta), var});

            // calculate residual smearing factor
            // return 0 if smearing in MC already larger than in data
            double k = 0;
            if (k_mc < k_data) k = sqrt(k_data*k_data - k_mc*k_mc);
            return k;
        }



        double pt_resol(double pt, double eta, double phi, float nL, int evtNumber, int lumiNumber, double low_pt_threshold = 26) const {
            // load correction values
            double rndm = (double) get_rndm(eta, phi, nL, evtNumber, lumiNumber);
            double std = (double) get_std(pt, eta, nL);
            double k = (double) get_k(eta, "nom");

            // calculate corrected value and return original value if a parameter is nan
            double ptc = pt * ( 1 + k * std * rndm);
            if (isnan(ptc)) ptc = pt;
            if(ptc / pt > 2 || ptc / pt < 0.1 || ptc < 0 || pt < low_pt_threshold || pt > 200){
            ptc = pt;
            }
            // For muons outside the validated pT range (including pT < low_pt_threshold),
            // or when the smeared pT is clearly unphysical, we return the original pT
            // to avoid applying resolution corrections where they are not defined.
            return ptc;
        }

        double pt_resol_var(double pt_woresol, double pt_wresol, double eta, string updn) const {

            double k = (double) get_k(eta, "nom");

            if (k==0) return pt_wresol;

            double k_unc = cset->at("k_mc")->evaluate({abs(eta), "stat"});

            double std_x_rndm = (pt_wresol / pt_woresol - 1) / k;

            double pt_var = pt_wresol;

            if (updn=="up"){
                pt_var = pt_woresol * (1 + (k+k_unc) * std_x_rndm);
            }
            else if (updn=="dn"){
                pt_var = pt_woresol * (1 + (k-k_unc) * std_x_rndm);
            }
            else {
                cout << "ERROR: updn must be 'up' or 'dn'" << endl;
            }
            if(pt_var / pt_woresol > 2 || pt_var / pt_woresol < 0.1 || pt_var < 0){
                pt_var = pt_woresol;
            }

            return pt_var;
        }

        double pt_scale(bool is_data, double pt, double eta, double phi, int charge, double low_pt_threshold = 26) const {

            // use right correction
            string dtmc = "mc";
            if (is_data) dtmc = "data";

            double a = cset->at("a_"+dtmc)->evaluate({eta, phi, "nom"});
            double m = cset->at("m_"+dtmc)->evaluate({eta, phi, "nom"});
            if(pt < low_pt_threshold)
                return pt;

            return 1. / (m/pt + charge * a);
        }


        double pt_scale_var(double pt, double eta, double phi, int charge, string updn) const {

            double stat_a = cset->at("a_mc")->evaluate({eta, phi, "stat"});
            double stat_m = cset->at("m_mc")->evaluate({eta, phi, "stat"});
            double stat_rho = cset->at("m_mc")->evaluate({eta, phi, "rho_stat"});

            double unc = pt*pt*sqrt(stat_m*stat_m / (pt*pt) + stat_a*stat_a + 2*charge*stat_rho*stat_m/pt*stat_a);

            double pt_var = pt;

            if (updn=="up"){
                pt_var = pt + unc;
            }
            else if (updn=="dn"){
                pt_var = pt - unc;
            }

            return pt_var;
        }
    };
}  // namespace correction
