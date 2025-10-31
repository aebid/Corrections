#ifndef CMSJMECalculators_JMESystematicsCalculators_H
#define CMSJMECalculators_JMESystematicsCalculators_H

#include <map>
#include <ROOT/RVec.hxx>
#include "JetMETCorrections/Modules/interface/JetResolution.h"
#include "CondFormats/JetMETObjects/interface/JetCorrectorParameters.h"
#include "CondFormats/JetMETObjects/interface/SimpleJetCorrectionUncertainty.h"
#include "CondFormats/JetMETObjects/interface/FactorizedJetCorrectorCalculator.h"
#include "CommonTools/Utils/interface/FormulaEvaluator.h"

class TRandom3;

namespace rdfhelpers {

    class ModifiedPtMCollection {  // map of variation collections
      public:
        using compv_t = ROOT::VecOps::RVec<float>;

        ModifiedPtMCollection() = default;
        ModifiedPtMCollection(std::size_t n, const compv_t& pt, const compv_t& mass) : m_pt(n, pt), m_mass(n, mass) {}

        std::size_t size() const { return m_pt.size(); }

        const compv_t& pt(std::size_t i) const { return m_pt[i]; }
        const compv_t& mass(std::size_t i) const { return m_mass[i]; }

        void set(std::size_t i, const compv_t& pt, const compv_t& mass) {
            m_pt[i] = pt;
            m_mass[i] = mass;
        }
        void set(std::size_t i, compv_t&& pt, compv_t&& mass) {
            m_pt[i] = std::move(pt);
            m_mass[i] = std::move(mass);
        }

      private:
        std::vector<compv_t> m_pt;
        std::vector<compv_t> m_mass;
    };

    class ModifiedPtMMsdCollection {  // for fat jets
      public:
        using compv_t = ROOT::VecOps::RVec<float>;

        ModifiedPtMMsdCollection() = default;
        ModifiedPtMMsdCollection(
            std::size_t nPt, const compv_t& pt, const std::size_t nM, const compv_t& mass, const compv_t& msd)
            : m_pt(nPt, pt), m_mass(nM, mass), m_msd(nM, msd) {}

        std::size_t size() const { return m_pt.size(); }
        std::size_t sizeM() const { return m_mass.size(); }

        const compv_t& pt(std::size_t i) const { return m_pt[i]; }
        const compv_t& mass(std::size_t i) const { return m_mass[i]; }
        const compv_t& msoftdrop(std::size_t i) const { return m_msd[i]; }

        void set(std::size_t i, const compv_t& pt, const compv_t& mass, const compv_t& msd) {
            m_pt[i] = pt;
            m_mass[i] = mass;
            m_msd[i] = msd;
        }
        void setM(std::size_t i, const compv_t& mass, const compv_t& msd) {
            m_mass[i] = mass;
            m_msd[i] = msd;
        }
        void set(std::size_t i, compv_t&& pt, compv_t&& mass, compv_t&& msd) {
            m_pt[i] = std::move(pt);
            m_mass[i] = std::move(mass);
            m_msd[i] = std::move(msd);
        }
        void setM(std::size_t i, compv_t&& mass, compv_t&& msd) {
            m_mass[i] = std::move(mass);
            m_msd[i] = std::move(msd);
        }

      private:
        std::vector<compv_t> m_pt;
        std::vector<compv_t> m_mass;
        std::vector<compv_t> m_msd;
    };

    class ModifiedMET {
      public:
        using compv_t = ROOT::VecOps::RVec<double>;

        ModifiedMET() = default;
        // initialize with the nominal value for all variations
        ModifiedMET(std::size_t n, double px_nom, double py_nom) : m_px(n, px_nom), m_py(n, py_nom) {}

        std::size_t size() const { return m_px.size(); }
        const compv_t& px() const { return m_px; }
        const compv_t& py() const { return m_py; }
        double px(std::size_t i) const { return m_px[i]; }
        double py(std::size_t i) const { return m_py[i]; }
        double pt(std::size_t i) const { return std::sqrt(m_px[i] * m_px[i] + m_py[i] * m_py[i]); }
        double phi(std::size_t i) const { return std::atan2(m_py[i], m_px[i]); }

        void setXY(std::size_t i, double dpx, double dpy) {
            m_px[i] = dpx;
            m_py[i] = dpy;
        }
        void addR_proj(std::size_t i, double cosphi, double sinphi, double dp) {
            m_px[i] += dp * cosphi;
            m_py[i] += dp * sinphi;
        }

      private:
        compv_t m_px;
        compv_t m_py;
    };
}  // namespace rdfhelpers

class JetMETVariationsCalculatorBase {
  public:
    using p4compv_t = ROOT::VecOps::RVec<float>;

    JetMETVariationsCalculatorBase() = default;

    // set up smearing (and JER systematics)
    void setSmearing(const std::string& ptResolution,
                     const std::string& ptResolutionSF,
                     bool splitJER,
                     bool doGenMatch,
                     float genMatch_maxDR = -1.,
                     float genMatch_maxDPT = -1.) {
        m_doSmearing = true;
        m_jetPtRes = JME::JetResolution(ptResolution);
        m_jetEResSF = JME::JetResolutionScaleFactor(ptResolutionSF);
        m_splitJER = splitJER;
        m_smearDoGenMatch = doGenMatch;
        m_genMatch_dR2max = genMatch_maxDR * genMatch_maxDR;
        m_genMatch_dPtmax = genMatch_maxDPT;
    }

    void setJEC(const std::vector<JetCorrectorParameters>& jecParams);
    void setAddHEM2018Issue(bool enable) { m_addHEM2018Issue = enable; }

    void addJESUncertainty(const std::string& name, const JetCorrectorParameters& params) {
        m_jesUncSources.emplace(std::piecewise_construct, std::forward_as_tuple(name), std::forward_as_tuple(params));
    }

  protected:
    std::size_t findGenMatch(const double pt,
                             const float eta,
                             const float phi,
                             const ROOT::VecOps::RVec<float>& gen_pt,
                             const ROOT::VecOps::RVec<float>& gen_eta,
                             const ROOT::VecOps::RVec<float>& gen_phi,
                             const double resolution) const;

    // config options
    bool m_doSmearing{false}, m_smearDoGenMatch;       // default: yes, yes
    bool m_addHEM2018Issue{false}, m_splitJER{false};  // default: no, no
    float m_genMatch_dR2max, m_genMatch_dPtmax;        // default: R/2 (0.2) and 3
    // parameters and helpers
    JME::JetResolution m_jetPtRes;
    JME::JetResolutionScaleFactor m_jetEResSF;
    std::unique_ptr<FactorizedJetCorrectorCalculator> m_jetCorrector;
    std::unordered_map<std::string, SimpleJetCorrectionUncertainty> m_jesUncSources;
};
#endif  // CMSJMECalculators_JMESystematicsCalculators_H