#pragma once
#include "JMECalculatorBase.h"
#include "CondFormats/JetMETObjects/interface/FactorizedJetCorrectorCalculator.h"

#include <Math/GenVector/LorentzVector.h>
#include <Math/GenVector/PtEtaPhiM4D.h>
#include "Math/VectorUtil.h"
#include "TRandom3.h"
#include <cassert>

// #define BAMBOO_JME_DEBUG // uncomment to debug

#ifdef BAMBOO_JME_DEBUG
#define LogDebug_JME std::cout
#else
#define LogDebug_JME \
    if (false)       \
    std::cout
#endif

void JetMETVariationsCalculatorBase::setJEC(const std::vector<JetCorrectorParameters>& jecParams) {
    if (!jecParams.empty()) {
        m_jetCorrector =
            std::unique_ptr<FactorizedJetCorrectorCalculator>{new FactorizedJetCorrectorCalculator(jecParams)};
    }
}

namespace {

    double GetRandomNumber(int event, double jet_pt, double jet_eta, double jet_phi, double sigma) {
        std::normal_distribution<> d(0, sigma);

        // Initialize random generator with seed dependent on the jet for future reproducibility and sync
        size_t seed = event + size_t(jet_pt * 100) + size_t(std::abs(jet_eta) * 100) * 100 +
                      size_t(std::abs(jet_phi) * 100) * 10000;
        std::mt19937_64 random_generator_(seed);
        double randomNumber = d(random_generator_);
        //std::cout << "seed = " << seed << std::endl;
        //std::cout << "random number = " << randomNumber << std::endl;
        return randomNumber;
    }
    TRandom3& getTRandom3(uint32_t seed) {
        static thread_local TRandom3 rg{};
        rg.SetSeed(seed);
        return rg;
    }

    double jetESmearFactor(double pt, double eOrig, float genPt, float ptRes, float sfUncert, double rand) {
        double smear = 1.;
        if (genPt > 0.) {
            smear = 1. + (sfUncert - 1.) * (pt - genPt) / pt;
        } else if (sfUncert > 1.) {
            smear = 1. + rand * std::sqrt(sfUncert * sfUncert - 1.);
        }
        if (smear * eOrig < 1.e-2) {
            smear = 1.e-2 / eOrig;
        }
        //std::cout << " pt " << pt << " eOrig " << eOrig << " genPt " << genPt << " ptRes " << ptRes << " sfUncert "<< sfUncert << " rand " << rand << std::endl;
        return smear;
    }

    // because something goes wrong with linking ROOT::Math::VectorUtil::Phi_mpi_pi
    template <typename T>
    T phi_mpi_pi(T angle) {
        if (angle <= M_PI && angle > -M_PI) {
            return angle;
        }
        if (angle > 0) {
            const int n = static_cast<int>(.5 * (angle * M_1_PI + 1.));
            angle -= 2 * n * M_PI;
        } else {
            const int n = static_cast<int>(-.5 * (angle * M_1_PI - 1.));
            angle += 2 * n * M_PI;
        }
        return angle;
    }

    std::vector<float> fillVector(const std::vector<std::string>& names,
                                  const JME::JetParameters::value_type& jetParams) {
        static const std::unordered_map<std::string, JME::Binning> jmeBinningFromString = {
            {"JetEta", JME::Binning::JetEta},
            {"JetPt", JME::Binning::JetPt},
            // TODO JetPhi, JetEMF, LepPx, LepPy, LepPz
            {"JetE", JME::Binning::JetE}};
        std::vector<float> result;
        result.reserve(names.size());
        for (const auto& nm : names) {
            const auto it_key = jmeBinningFromString.find(nm);
            if (std::end(jmeBinningFromString) == it_key) {
                throw std::runtime_error{"Unknown binning variable: " + nm};
            } else {
                const auto it_par = jetParams.find(it_key->second);
                if (std::end(jetParams) == it_par) {
                    throw std::runtime_error{"Binning variable " + nm + " not found"};
                } else {
                    result.push_back(it_par->second);
                }
            }
        }
        return result;
    }

    float getUncertainty(const SimpleJetCorrectionUncertainty& uncert,
                         const JME::JetParameters::value_type& jetParams,
                         bool direction) {
        const auto vx = fillVector(uncert.parameters().definitions().binVar(), jetParams);
        const auto vy = fillVector(uncert.parameters().definitions().parVar(), jetParams);
        return uncert.uncertainty(vx, vy[0], direction);
    }

    float deltaHEM2018Issue(float pt_nom, int jetId, float phi, float eta) {
        float delta = 1.;
        if (pt_nom > 15. && (jetId & 0x2) && phi > -1.57 && phi < -0.87) {
            if (eta > -2.5 && eta < -1.3) {
                delta = 0.8;
            } else if (eta <= -2.5 && eta > -3.) {
                delta = 0.65;
            }
        }
        return delta;
    }

    int jerSplitID(float pt, float eta) {
        const auto aEta = std::abs(eta);
        if (aEta < 1.93)
            return 0;
        else if (aEta < 2.5)
            return 1;
        else if (aEta < 3.)
            if (pt < 50.)
                return 2;
            else
                return 3;
        else if (pt < 50.)
            return 4;
        else
            return 5;
    }

    std::vector<JetCorrectorParameters> makeJCPList(const std::vector<std::string>& paths) {
        std::vector<JetCorrectorParameters> params;
        std::transform(std::begin(paths), std::end(paths), std::back_inserter(params), [](const std::string& path) {
            return JetCorrectorParameters{path};
        });
        return params;
    }

    template <typename CALC>
    void configureBaseCalc(CALC& calc,
                           const std::vector<std::string>& jecParams,
                           const std::vector<std::pair<std::string, std::string>>& jesUncertainties,
                           const std::string& ptResolution,
                           const std::string& ptResolutionSF,
                           bool splitJER,
                           bool doGenMatch,
                           float genMatch_maxDR,
                           float genMatch_maxDPT) {
        calc.setJEC(makeJCPList(jecParams));
        for (const auto& entry : jesUncertainties) {
            calc.addJESUncertainty(entry.first, JetCorrectorParameters{entry.second, entry.first});
        }
        if (!ptResolution.empty()) {
            calc.setSmearing(ptResolution, ptResolutionSF, splitJER, doGenMatch, genMatch_maxDR, genMatch_maxDPT);
        }
    }

    template <typename CALC>
    void configureMETCalc_common(CALC& calc,
                                 const std::vector<std::string>& jecParams,
                                 const std::vector<std::string>& jecParamsL1,
                                 float unclEnThreshold,
                                 const std::vector<std::pair<std::string, std::string>>& jesUncertainties,
                                 bool isT1SmearedMET,
                                 const std::string& ptResolution,
                                 const std::string& ptResolutionSF,
                                 bool splitJER,
                                 bool doGenMatch,
                                 float genMatch_maxDR,
                                 float genMatch_maxDPT) {
        configureBaseCalc(calc,
                          jecParams,
                          jesUncertainties,
                          ptResolution,
                          ptResolutionSF,
                          splitJER,
                          doGenMatch,
                          genMatch_maxDR,
                          genMatch_maxDPT);
        calc.setL1JEC(makeJCPList(jecParamsL1));
        calc.setUnclusteredEnergyTreshold(unclEnThreshold);
        if (isT1SmearedMET) {
            calc.setIsT1SmearedMET(isT1SmearedMET);
        }
    }
}  // namespace

// TODO with orig MET and jets (sumpx,sumpy): calc modif MET(sig), produce bigger results type

std::size_t JetMETVariationsCalculatorBase::findGenMatch(const double pt,
                                                         const float eta,
                                                         const float phi,
                                                         const ROOT::VecOps::RVec<float>& gen_pt,
                                                         const ROOT::VecOps::RVec<float>& gen_eta,
                                                         const ROOT::VecOps::RVec<float>& gen_phi,
                                                         const double resolution) const {
    auto dr2Min = std::numeric_limits<float>::max();
    std::size_t igBest{gen_pt.size()};
    LogDebug_JME << "(DRs: ";
    for (std::size_t ig{0}; ig != gen_pt.size(); ++ig) {
        const auto dphi = phi_mpi_pi(gen_phi[ig] - phi);
        const auto deta = (gen_eta[ig] - eta);
        const auto dr2 = dphi * dphi + deta * deta;
        LogDebug_JME << "dr2=" << dr2;
        if ((dr2 < dr2Min) && (dr2 < m_genMatch_dR2max)) {
            LogDebug_JME << "->dpt=" << std::abs(gen_pt[ig] - pt) << ",res=" << resolution;
            if (std::abs(gen_pt[ig] - pt) < m_genMatch_dPtmax * resolution) {
                LogDebug_JME << "->best:" << ig;
                dr2Min = dr2;
                igBest = ig;
            }
        }
        LogDebug_JME << ", ";
    }
    LogDebug_JME << ")";
    return igBest;
}