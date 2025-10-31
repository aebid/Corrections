#pragma once
#include "JMECalculatorBase.h"

class JetVariationsCalculator : public JetMETVariationsCalculatorBase {
  public:
    using result_t = rdfhelpers::ModifiedPtMCollection;

    JetVariationsCalculator() = default;

    static JetVariationsCalculator create(const std::vector<std::string>& jecParams,
                                          const std::vector<std::pair<std::string, std::string>>& jesUncertainties,
                                          bool addHEM2018Issue,
                                          const std::string& ptResolution,
                                          const std::string& ptResolutionSF,
                                          bool splitJER,
                                          bool doGenMatch,
                                          float genMatch_maxDR,
                                          float genMatch_maxDPT);

    std::vector<std::string> available(const std::string& attr = {}) const;
    // interface for NanoAOD

    ROOT::VecOps::RVec<float> getResolution(const p4compv_t& jet_pt, const p4compv_t& jet_eta, const float rho) const;

    result_t produce(const p4compv_t& jet_pt,
                     const p4compv_t& jet_eta,
                     const p4compv_t& jet_phi,
                     const p4compv_t& jet_mass,
                     const p4compv_t& jet_rawcorr,
                     const p4compv_t& jet_area,
                     const ROOT::VecOps::RVec<int>& jet_jetId,
                     const float rho,
                     // MC-only
                     const ROOT::VecOps::RVec<int>& jet_partonFlavour,
                     const std::uint32_t seed,
                     const p4compv_t& genjet_pt,
                     const p4compv_t& genjet_eta,
                     const p4compv_t& genjet_phi,
                     const p4compv_t& genjet_mass,
                     int event) const;
};
