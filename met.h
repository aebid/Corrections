#pragma once

#include "corrections.h"

namespace correction {

    LorentzVectorM ShiftMet(const LorentzVectorM& met_p4,
                            const std::vector<RVecLV>& p4_original,
                            const std::vector<RVecLV>& p4_shifted,
                            bool debug) {
        if (debug) {
            std::string lvstring_met_original = LorentzVectorToString(met_p4, analysis::LVectorRepr::PxPyPtPhi);
            std::cout << "MET original = " << lvstring_met_original << std::endl;
        }
        LorentzVectorXYZ met_p4_shifted(met_p4);
        for (size_t collection_idx = 0; collection_idx < p4_original.size(); ++collection_idx) {
            for (size_t obj_idx = 0; obj_idx < p4_original.at(collection_idx).size(); ++obj_idx) {
                const auto delta_p4 =
                    p4_shifted.at(collection_idx).at(obj_idx) - p4_original.at(collection_idx).at(obj_idx);
                met_p4_shifted -= delta_p4;
                if (debug) {
                    std::string lvstring_original = LorentzVectorToString(p4_original.at(collection_idx).at(obj_idx),
                                                                          analysis::LVectorRepr::PxPyPtPhi);
                    std::string lvstring_shifted = LorentzVectorToString(p4_shifted.at(collection_idx).at(obj_idx),
                                                                         analysis::LVectorRepr::PxPyPtPhi);
                    std::string lvstring_met = LorentzVectorToString(met_p4, analysis::LVectorRepr::PxPyPtPhi);
                    std::string lvstring_met_shifted =
                        LorentzVectorToString(met_p4_shifted, analysis::LVectorRepr::PxPyPtPhi);
                    std::cout << " collection idx = " << collection_idx << " obj index = " << obj_idx
                              << " p4 original = " << lvstring_original << " p4 shifted = " << lvstring_shifted
                              << " delta p4 = " << delta_p4 << " met_p4 = " << lvstring_met << " met_p4 shifted "
                              << lvstring_met_shifted << std::endl;
                }
            }
        }
        if (debug) {
            std::string lvstring_met_shifted = LorentzVectorToString(met_p4_shifted, analysis::LVectorRepr::PxPyPtPhi);
            std::cout << "final MET shifted = " << lvstring_met_shifted << std::endl;
        }
        return LorentzVectorM(met_p4_shifted.pt(), 0., met_p4_shifted.phi(), 0.);
    }

}  // namespace correction