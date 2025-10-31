#pragma once
#include "FatJetSystematicCalculator.h"
#include "CondFormats/JetMETObjects/interface/FactorizedJetCorrectorCalculator.h"

#include <Math/GenVector/LorentzVector.h>
#include <Math/GenVector/PtEtaPhiM4D.h>
#include "Math/VectorUtil.h"
#include "TRandom3.h"
#include <cassert>

FatJetVariationsCalculator FatJetVariationsCalculator::create(
    const std::vector<std::string>& jecParams,
    const std::vector<std::pair<std::string, std::string>>& jesUncertainties,
    bool addHEM2018Issue,
    const std::string& ptResolution,
    const std::string& ptResolutionSF,
    bool splitJER,
    bool doGenMatch,
    float genMatch_maxDR,
    float genMatch_maxDPT,
    std::vector<double> jmsValues,
    std::vector<double> gmsValues,
    std::vector<double> jmrValues,
    std::vector<double> gmrValues,
    const std::string& puppiGenFormula,
    const std::array<double, 6>& puppi_reco_cen_params,
    const std::array<double, 6>& puppi_reco_for_params,
    const std::array<double, 6>& puppi_resol_cen_params,
    const std::array<double, 6>& puppi_resol_for_params) {
    FatJetVariationsCalculator inst{};
    configureBaseCalc(inst,
                      jecParams,
                      jesUncertainties,
                      ptResolution,
                      ptResolutionSF,
                      splitJER,
                      doGenMatch,
                      genMatch_maxDR,
                      genMatch_maxDPT);
    inst.setAddHEM2018Issue(addHEM2018Issue);
    if (jmsValues.size() == 3) {
        inst.setJMSValues(jmsValues[0], jmsValues[1], jmsValues[2]);
    } else if (jmsValues.size() == 1) {
        inst.setJMSValues(jmsValues[0]);
    }
    if (gmsValues.size() == 3) {
        inst.setGMSValues(gmsValues[0], gmsValues[1], gmsValues[2]);
    } else if (gmsValues.size() == 1) {
        inst.setGMSValues(gmsValues[0]);
    }
    if (jmrValues.size() == 3) {
        inst.setJMRValues(jmrValues[0], jmrValues[1], jmrValues[2]);
    } else if (jmrValues.size() == 1) {
        inst.setJMRValues(jmrValues[0]);
    }
    if (gmrValues.size() == 3) {
        inst.setGMRValues(gmrValues[0], gmrValues[1], gmrValues[2]);
    } else if (gmrValues.size() == 1) {
        inst.setGMRValues(gmrValues[0]);
    }
    if (!puppiGenFormula.empty()) {
        inst.setPuppiCorrections(puppiGenFormula,
                                 puppi_reco_cen_params,
                                 puppi_reco_for_params,
                                 puppi_resol_cen_params,
                                 puppi_resol_for_params);
    }
    return inst;
}

void FatJetVariationsCalculator::setPuppiCorrections(const std::string& genFormula,
                                                     const std::array<double, 6>& reco_cen_params,
                                                     const std::array<double, 6>& reco_for_params,
                                                     const std::array<double, 6>& resol_cen_params,
                                                     const std::array<double, 6>& resol_for_params) {
    m_puppiCorrGen = std::make_unique<reco::FormulaEvaluator>(genFormula);
    m_puppiPoly5 =
        std::make_unique<reco::FormulaEvaluator>("[0]+[1]*x+[2]*pow(x,2)+[3]*pow(x,3)+[4]*pow(x,4)+[5]*pow(x,5)");
    m_puppiCorrRecoParam_cen = reco_cen_params;
    m_puppiCorrRecoParam_for = reco_for_params;
    m_puppiResolParam_cen = resol_cen_params;
    m_puppiResolParam_for = resol_for_params;
}

FatJetVariationsCalculator::result_t FatJetVariationsCalculator::produce(const p4compv_t& jet_pt,
                                                                         const p4compv_t& jet_eta,
                                                                         const p4compv_t& jet_phi,
                                                                         const p4compv_t& jet_mass,
                                                                         const p4compv_t& jet_rawcorr,
                                                                         const p4compv_t& jet_area,
                                                                         const p4compv_t& jet_msoftdrop,
                                                                         const ROOT::VecOps::RVec<int>& jet_subJetIdx1,
                                                                         const ROOT::VecOps::RVec<int>& jet_subJetIdx2,
                                                                         const p4compv_t& subjet_pt,
                                                                         const p4compv_t& subjet_eta,
                                                                         const p4compv_t& subjet_phi,
                                                                         const p4compv_t& subjet_mass,
                                                                         const ROOT::VecOps::RVec<int>& jet_jetId,
                                                                         const float rho,
                                                                         const std::uint32_t seed,
                                                                         const p4compv_t& genjet_pt,
                                                                         const p4compv_t& genjet_eta,
                                                                         const p4compv_t& genjet_phi,
                                                                         const p4compv_t& genjet_mass,
                                                                         const p4compv_t& gensubjet_pt,
                                                                         const p4compv_t& gensubjet_eta,
                                                                         const p4compv_t& gensubjet_phi,
                                                                         const p4compv_t& gensubjet_mass,
                                                                         int event) const {
    const auto nVariations = 1 + (m_doSmearing ? 2 * (m_splitJER ? 6 : 1) : 0) + 2 * m_jesUncSources.size() +
                             (m_addHEM2018Issue ? 2 : 0);  // 1(nom)+2(JER)+2*len(JES)[+2(HEM)]
    const bool doJMSVars = m_jmsVals[1] != 1.;
    const auto nVariationsM =
        nVariations + (m_doSmearing ? 2 : 0) + (doJMSVars ? 2 : 0);  // 2(JMR)+2(JMS), both optional
    const auto nJets = jet_pt.size();
    LogDebug_JME << "JME:: hello from FatJetVariations produce. Got " << nJets << " jets" << std::endl;
    LogDebug_JME << "JME:: variations for PT: " << nVariations << " and for M, Msd: " << nVariationsM << std::endl;
    result_t out{nVariations, jet_pt, nVariationsM, jet_mass, jet_msoftdrop};

    ROOT::VecOps::RVec<double> pt_nom{jet_pt}, mass_raw{jet_mass};
    if (m_jetCorrector) {
        LogDebug_JME << "JME:: reapplying JEC" << std::endl;
        FactorizedJetCorrectorCalculator::VariableValues vals;
        for (std::size_t i{0}; i != nJets; ++i) {
            vals.setJetEta(jet_eta[i]);
            vals.setJetPt(jet_pt[i] * (1. - jet_rawcorr[i]));
            vals.setJetA(jet_area[i]);
            vals.setRho(rho);
            const auto corr = m_jetCorrector->getCorrection(vals);
            if (corr > 0.) {
                const double newc = (1. - jet_rawcorr[i]) * corr;
                pt_nom[i] *= newc;
                mass_raw[i] *= newc;
            }
        }
#ifdef BAMBOO_JME_DEBUG
        LogDebug_JME << "JME:: with reapplied JEC: ";
        for (std::size_t i{0}; i != nJets; ++i) {
            LogDebug_JME << "(PT=" << pt_nom[i] << ", ETA=" << jet_eta[i] << ", PHI=" << jet_phi[i]
                         << ", M=" << mass_raw[i] << ") ";
        }
        LogDebug_JME << std::endl;
#endif
    } else {
        LogDebug_JME << "JME:: Not reapplying JEC" << std::endl;
    }
    // calculate groomed P4 (and mass)
    using LVectorM = ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double>>;
    //std::cout << "0 " << std::endl;
    auto jet_groomedP4 = std::vector<LVectorM>{nJets};
    //std::cout << "1 " << std::endl;
    ROOT::VecOps::RVec<double> msd_nom(nJets, 0.);  // ?
    //std::cout << "2 " << std::endl;
    for (std::size_t j{0}; j != nJets; ++j) {
        //std::cout << "3 " << j << std::endl;
        //std::cout << jet_subJetIdx1[j] << std::endl;
        //std::cout << jet_subJetIdx2[j] << std::endl;
        if (jet_subJetIdx1[j] >= 0 && jet_subJetIdx2[j] >= 0) {
            jet_groomedP4[j] = (LVectorM(subjet_pt[jet_subJetIdx1[j]],
                                         subjet_eta[jet_subJetIdx1[j]],
                                         subjet_phi[jet_subJetIdx1[j]],
                                         subjet_mass[jet_subJetIdx1[j]]) +
                                LVectorM(subjet_pt[jet_subJetIdx2[j]],
                                         subjet_eta[jet_subJetIdx2[j]],
                                         subjet_phi[jet_subJetIdx2[j]],
                                         subjet_mass[jet_subJetIdx2[j]]));
            //std::cout << jet_groomedP4[j] << std::endl;
            // PUPPI SD mass correction https://github.com/cms-jet/PuppiSoftdropMassCorr/
            // WHich formula?? for creating m_puppiCorrGen
            if (m_puppiCorrGen->numberOfVariables()) {
                const auto puppisd_corr =
                    (m_puppiCorrGen->evaluate(std::array<double, 1>{{pt_nom[j]}}, std::array<double, 0>{{}}) *
                     m_puppiPoly5->evaluate(
                         std::array<double, 1>{{pt_nom[j]}},
                         (std::abs(jet_eta[j]) <= 1.3 ? m_puppiCorrRecoParam_cen : m_puppiCorrRecoParam_for)));
                LogDebug_JME << "JME:: PUPPI gen mass correction: " << puppisd_corr << std::endl;
                jet_groomedP4[j].SetM(puppisd_corr * jet_groomedP4[j].M());
            }
            msd_nom[j] = jet_groomedP4[j].M();
            if (msd_nom[j] < 0.0) {
                msd_nom[j] *= -1.;
            }
        }
    }
#ifdef BAMBOO_JME_DEBUG
    LogDebug_JME << "JME:: Groomed momenta: ";
    for (std::size_t i{0}; i != nJets; ++i) {
        const auto& p4_g = jet_groomedP4[i];
        LogDebug_JME << "(PT=" << p4_g.Pt() << ", ETA=" << p4_g.Eta() << ", PHI=" << p4_g.Phi() << ", M=" << msd_nom[i]
                     << ") ";
    }
    LogDebug_JME << std::endl;
#endif
    // apply nominal JMS (JMS variations by storing (up|down)/nom)
    auto mass_nom = mass_raw * m_jmsVals[0];
    msd_nom *= m_gmsVals[0];
    std::size_t iVar = 1;  // after nominal
    // smearing and JER
    if (m_doSmearing) {
        p4compv_t pt_jerUp{pt_nom}, pt_jerDown{pt_nom};
        p4compv_t mass_jerUp{mass_nom}, mass_jerDown{mass_nom}, mass_jmrUp{mass_nom}, mass_jmrDown{mass_nom};
        p4compv_t msd_jerUp{msd_nom}, msd_jerDown{msd_nom}, msd_jmrUp{msd_nom}, msd_jmrDown{msd_nom};
        LogDebug_JME << "JME:: Smearing (seed=" << seed << ")" << std::endl;
        auto& rg = getTRandom3(seed);
        for (std::size_t i{0}; i != nJets; ++i) {
            double jer_nom{1.}, jer_up{1.}, jer_down{1.}, jmr_nom{1.}, jmr_up{1.}, jmr_down{1.}, gmr_nom{1.},
                gmr_up{1.}, gmr_down{1.};
            if (pt_nom[i] > 0. || mass_raw[i] > 0.) {
                const auto eOrig = ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double>>(
                                       pt_nom[i], jet_phi[i], jet_eta[i], mass_raw[i])
                                       .E();
                JME::JetParameters jPar{
                    {JME::Binning::JetPt, pt_nom[i]}, {JME::Binning::JetEta, jet_eta[i]}, {JME::Binning::Rho, rho}};
                const auto ptRes = m_jetPtRes.getResolution(jPar);
                LogDebug_JME << "JME:: JetParameters: pt=" << pt_nom[i] << ", eta=" << jet_eta[i] << ", rho=" << rho
                             << "; ptRes=" << ptRes << std::endl;
                LogDebug_JME << "JME:: ";
                float genPt{-1}, genM{-1.};
                if (m_smearDoGenMatch) {
                    const auto iGen = findGenMatch(
                        pt_nom[i], jet_eta[i], jet_phi[i], genjet_pt, genjet_eta, genjet_phi, ptRes * pt_nom[i]);
                    if (iGen != genjet_pt.size()) {
                        genPt = genjet_pt[iGen];
                        genM = genjet_mass[iGen];
                        LogDebug_JME << "genPt=" << genPt << " genM=" << genM << " ";
                    }
                }
                if (pt_nom[i] > 0.) {
                    //const auto rand = ( genPt < 0. ) ? rg.Gaus(0, ptRes) : -1.;
                    const auto rand =
                        (genPt < 0.) ? GetRandomNumber(event, pt_nom[i], jet_eta[i], jet_phi[i], ptRes) : -1.;
                    LogDebug_JME << "jet_pt_resolution: " << ptRes << ", rand: " << rand << std::endl;
                    LogDebug_JME << "jet_pt_resolution: " << ptRes << ", rand: " << rand << std::endl;
                    jer_nom = jetESmearFactor(
                        pt_nom[i], eOrig, genPt, ptRes, m_jetEResSF.getScaleFactor(jPar, Variation::NOMINAL), rand);
                    jer_down = jetESmearFactor(
                        pt_nom[i], eOrig, genPt, ptRes, m_jetEResSF.getScaleFactor(jPar, Variation::DOWN), rand);
                    jer_up = jetESmearFactor(
                        pt_nom[i], eOrig, genPt, ptRes, m_jetEResSF.getScaleFactor(jPar, Variation::UP), rand);
                }
                // LogDebug_JME << "  scalefactors are NOMINAL=" << m_jetEResSF.getScaleFactor(jPar, Variation::NOMINAL) << ", DOWN=" << m_jetEResSF.getScaleFactor(jPar, Variation::DOWN) << ", UP=" << m_jetEResSF.getScaleFactor(jPar, Variation::UP) << std::endl;
                // LogDebug_JME << "  smearfactors are NOMINAL=" << jer_nom[i] << ", DOWN=" << jer_down[i] << ", UP=" << jer_up[i] << std::endl;
                // JMR
                if (mass_raw[i] > 0.) {
                    if (genM != -1.) {
                        LogDebug_JME << "JME:: JMR with genM=" << genM << " and raw " << mass_raw[i];
                        const auto dMoM = 1. - (genM / mass_raw[i]);
                        jmr_nom = 1. + (m_jmrVals[0] - 1.) * dMoM;
                        jmr_up = 1. + (m_jmrVals[1] - 1.) * dMoM;
                        jmr_down = 1. + (m_jmrVals[2] - 1.) * dMoM;
                    } else {
                        const auto mRes = m_puppiPoly5->evaluate(
                            std::array<double, 1>{{pt_nom[i]}},
                            (std::abs(jet_eta[i]) <= 1.3 ? m_puppiResolParam_cen : m_puppiResolParam_for));
                        LogDebug_JME << "JME:: JMR parametric with resolution " << mRes;

                        const auto rand = rg.Gaus(0, mRes);
                        jmr_nom = (m_jmrVals[0] <= 1. ? 1. : rand * std::sqrt(m_jmrVals[0] * m_jmrVals[0] - 1));
                        jmr_up = (m_jmrVals[1] <= 1. ? 1. : rand * std::sqrt(m_jmrVals[1] * m_jmrVals[1] - 1));
                        jmr_down = (m_jmrVals[2] <= 1. ? 1. : rand * std::sqrt(m_jmrVals[2] * m_jmrVals[2] - 1));
                    }
                    if (jmr_nom * mass_raw[i] < 1.e-2) {
                        jmr_nom = 1.e-2;
                    }
                    if (jmr_up * mass_raw[i] < 1.e-2) {
                        jmr_up = 1.e-2;
                    }
                    if (jmr_down * mass_raw[i] < 1.e-2) {
                        jmr_down = 1.e-2;
                    }
                }
                LogDebug_JME << "  mass smearfactors are NOMINAL=" << jmr_nom << ", DOWN=" << jmr_down
                             << ", UP=" << jmr_up << std::endl;
            }
            if (msd_nom[i] > 0.) {  // JMR for groomed
                // genGroomedJet
                int igsj1{-1}, igsj2{-1};
                for (int ig{0}; ig != int(gensubjet_eta.size()); ++ig) {
                    const auto dphi = phi_mpi_pi(gensubjet_phi[ig] - jet_groomedP4[i].Phi());
                    const auto deta = (gensubjet_eta[ig] - jet_groomedP4[i].Eta());
                    const auto dr2 = dphi * dphi + deta * deta;
                    if (dr2 < 0.64) {  // dR < 0.8
                        if (igsj1 == -1) {
                            igsj1 = ig;
                        } else {
                            igsj2 = ig;
                            break;  // only need the first two
                        }
                    }
                }
                if (igsj2 != -1) {
                    LogDebug_JME << "JME:: Matched gen-level subjets " << igsj1 << "," << igsj2 << std::endl;
                    const auto genM =
                        (LVectorM{
                             gensubjet_pt[igsj1], gensubjet_eta[igsj1], gensubjet_phi[igsj1], gensubjet_mass[igsj1]} +
                         LVectorM{
                             gensubjet_pt[igsj2], gensubjet_eta[igsj2], gensubjet_phi[igsj2], gensubjet_mass[igsj2]})
                            .M();
                    const auto dMoM = 1. - (genM / jet_groomedP4[i].M());  // raw
                    gmr_nom = 1. + (m_gmrVals[0] - 1.) * dMoM;
                    gmr_up = 1. + (m_gmrVals[1] - 1.) * dMoM;
                    gmr_down = 1. + (m_gmrVals[2] - 1.) * dMoM;
                } else {
                    const auto mRes = m_puppiPoly5->evaluate(
                        std::array<double, 1>{{jet_groomedP4[i].Pt()}},
                        (std::abs(jet_eta[i]) <= 1.3 ? m_puppiResolParam_cen : m_puppiResolParam_for));
                    const auto rand = rg.Gaus(0, mRes);
                    gmr_nom = (m_gmrVals[0] <= 1. ? 1. : rand * std::sqrt(m_gmrVals[0] * m_gmrVals[0] - 1));
                    gmr_up = (m_gmrVals[1] <= 1. ? 1. : rand * std::sqrt(m_gmrVals[1] * m_gmrVals[1] - 1));
                    gmr_down = (m_gmrVals[2] <= 1. ? 1. : rand * std::sqrt(m_gmrVals[2] * m_gmrVals[2] - 1));
                }
                if (gmr_nom * msd_nom[i] < 1.e-2) {
                    gmr_nom = 1.e-2;
                }
                if (gmr_up * msd_nom[i] < 1.e-2) {
                    gmr_up = 1.e-2;
                }
                if (gmr_down * msd_nom[i] < 1.e-2) {
                    gmr_down = 1.e-2;
                }
            }
            LogDebug_JME << "  groomed mass smearfactors are NOMINAL=" << gmr_nom << ", DOWN=" << gmr_down
                         << ", UP=" << gmr_up << std::endl;
            // fill variation arrays
            pt_jerDown[i] *= jer_down;
            pt_jerUp[i] *= jer_up;
            mass_jerUp[i] *= jer_up * jmr_nom;
            mass_jerDown[i] *= jer_down * jmr_nom;
            mass_jmrUp[i] *= jer_nom * jmr_up;
            mass_jmrDown[i] *= jer_nom * jmr_down;
            msd_jerUp[i] *= jer_up * gmr_nom;
            msd_jerDown[i] *= jer_down * gmr_nom;
            msd_jmrUp[i] *= jer_nom * gmr_up;
            msd_jmrDown[i] *= jer_nom * gmr_down;
            // finally apply JER and JMR to nominal
            pt_nom[i] *= jer_nom;
            mass_nom[i] *= jer_nom * jmr_nom;
            msd_nom[i] *= jer_nom * gmr_nom;
        }
        if (m_splitJER) {
            ROOT::VecOps::RVec<int> jerBin(pt_nom.size(), -1);
            for (std::size_t j{0}; j != nJets; ++j) {
                jerBin[j] = jerSplitID(pt_nom[j], jet_eta[j]);
            }
            for (int i{0}; i != 6; ++i) {
                p4compv_t pt_jeriUp{pt_nom}, mass_jeriUp{mass_nom}, msd_jeriUp{msd_nom};
                p4compv_t pt_jeriDown{pt_nom}, mass_jeriDown{mass_nom}, msd_jeriDown{msd_nom};
                for (std::size_t j{0}; j != nJets; ++j) {
                    if (jerBin[j] == i) {
                        pt_jeriUp[j] = pt_jerUp[j];
                        pt_jeriDown[j] = pt_jerDown[j];
                        mass_jeriUp[j] = mass_jerUp[j];
                        mass_jeriDown[j] = mass_jerDown[j];
                        msd_jeriUp[j] = msd_jerUp[j];
                        msd_jeriDown[j] = msd_jerDown[j];
                    }
                }
                out.set(iVar++, std::move(pt_jeriUp), std::move(mass_jeriUp), std::move(msd_jeriUp));
                out.set(iVar++, std::move(pt_jeriDown), std::move(mass_jeriDown), std::move(msd_jeriDown));
            }
        } else {
            out.set(iVar++, std::move(pt_jerUp), std::move(mass_jerUp), std::move(msd_jerUp));
            out.set(iVar++, std::move(pt_jerDown), std::move(mass_jerDown), std::move(msd_jerDown));
        }
        out.setM(nVariationsM - 2, std::move(mass_jmrUp), std::move(msd_jmrUp));
        out.setM(nVariationsM - 1, std::move(mass_jmrDown), std::move(msd_jmrDown));
        LogDebug_JME << "JME:: Done with smearing" << std::endl;
    } else {
        LogDebug_JME << "JME:: No smearing" << std::endl;
    }
    out.set(0, pt_nom, mass_nom, msd_nom);
    if (doJMSVars) {  // mass_nom has nominal JMS, jmsVals/gmsVals are divided by that
        out.setM(nVariations, mass_nom * m_jmsVals[1], msd_nom * m_gmsVals[1]);      // UP
        out.setM(nVariations + 1, mass_nom * m_jmsVals[2], msd_nom * m_gmsVals[2]);  // DOWN
    }

    // HEM issue 2018, see https://hypernews.cern.ch/HyperNews/CMS/get/JetMET/2000.html
    if (m_addHEM2018Issue) {
        p4compv_t pt_down(pt_nom.size(), 0.), mass_down(mass_nom.size(), 0.), msd_down(msd_nom.size(), 0.);
        for (std::size_t j{0}; j != nJets; ++j) {
            const auto delta = deltaHEM2018Issue(pt_nom[j], jet_jetId[j], jet_phi[j], jet_eta[j]);
            pt_down[j] = pt_nom[j] * delta;
            mass_down[j] = mass_nom[j] * delta;
            msd_down[j] = msd_nom[j] * delta;
        }
        out.set(iVar++, pt_nom, mass_nom, msd_nom);
        out.set(iVar++, std::move(pt_down), std::move(mass_down), std::move(msd_down));
    }
    // JES uncertainties
    for (auto& jesUnc : m_jesUncSources) {
        LogDebug_JME << "JME:: evaluating JES uncertainty: " << jesUnc.first << std::endl;
        p4compv_t pt_jesDown(pt_nom.size(), 0.), mass_jesDown(mass_nom.size(), 0.), msd_jesDown(msd_nom.size(), 0.);
        p4compv_t pt_jesUp(pt_nom.size(), 0.), mass_jesUp(mass_nom.size(), 0.), msd_jesUp(msd_nom.size(), 0.);
        for (std::size_t i{0}; i != nJets; ++i) {
            const auto delta = getUncertainty(
                jesUnc.second, {{JME::Binning::JetPt, pt_nom[i]}, {JME::Binning::JetEta, jet_eta[i]}}, true);
            pt_jesDown[i] = pt_nom[i] * (1. - delta);
            mass_jesDown[i] = mass_nom[i] * (1. - delta);
            msd_jesDown[i] = msd_nom[i] * (1. - delta);
            pt_jesUp[i] = pt_nom[i] * (1. + delta);
            mass_jesUp[i] = mass_nom[i] * (1. + delta);
            msd_jesUp[i] = msd_nom[i] * (1. + delta);
        }
        out.set(iVar++, std::move(pt_jesUp), std::move(mass_jesUp), std::move(msd_jesUp));
        out.set(iVar++, std::move(pt_jesDown), std::move(mass_jesDown), std::move(msd_jesDown));
    }

#ifdef BAMBOO_JME_DEBUG
    assert(iVar == out.size());
    LogDebug_JME << "JME:: returning " << out.size() << " modified jet collections" << std::endl;
    const auto varNames = available("mass");
    assert(varNames.size() == nVariationsM);
    for (std::size_t i{0}; i != nVariations; ++i) {
        LogDebug_JME << "JME:: Jet_" << varNames[i] << ": ";
        for (std::size_t j{0}; j != nJets; ++j) {
            LogDebug_JME << "(PT=" << out.pt(i)[j] << ", ETA=" << jet_eta[j] << ", PHI=" << jet_phi[j]
                         << ", M=" << out.mass(i)[j] << ", Msd=" << out.msoftdrop(i)[j] << ") ";
        }
        LogDebug_JME << std::endl;
    }
    for (std::size_t i{nVariations}; i != nVariationsM; ++i) {
        LogDebug_JME << "JME:: Jet_" << varNames[i] << ": ";
        for (std::size_t j{0}; j != nJets; ++j) {
            LogDebug_JME << "(PT=" << out.pt(0)[j] << ", ETA=" << jet_eta[j] << ", PHI=" << jet_phi[j]
                         << ", M=" << out.mass(i)[j] << ", Msd=" << out.msoftdrop(i)[j] << ") ";
        }
        LogDebug_JME << std::endl;
    }
#endif
    return out;
}
ROOT::VecOps::RVec<float> FatJetVariationsCalculator::getResolution(const p4compv_t& jet_pt,
                                                                    const p4compv_t& jet_eta,
                                                                    const float rho) const {
    const auto nJets = jet_pt.size();
    ROOT::VecOps::RVec<float> res(nJets, 0.);
    for (std::size_t i{0}; i != nJets; ++i) {
        if (jet_pt[i] > 0.) {
            JME::JetParameters jPar{
                {JME::Binning::JetPt, jet_pt[i]}, {JME::Binning::JetEta, jet_eta[i]}, {JME::Binning::Rho, rho}};
            res.at(i) = m_jetPtRes.getResolution(jPar);
        }
    }
    return res;
}
std::vector<std::string> FatJetVariationsCalculator::available(const std::string& attr) const {
    std::vector<std::string> products = {"nominal"};
    if (m_doSmearing) {
        if (m_splitJER) {
            for (int i = 0; i != 6; ++i) {
                products.emplace_back("jer" + std::to_string(i) + "up");
                products.emplace_back("jer" + std::to_string(i) + "down");
            }
        } else {
            products.emplace_back("jerup");
            products.emplace_back("jerdown");
        }
    }
    if (m_addHEM2018Issue) {
        products.emplace_back("jesHEMIssueup");
        products.emplace_back("jesHEMIssuedown");
    }
    for (const auto& src : m_jesUncSources) {
        products.emplace_back("jes" + src.first + "up");
        products.emplace_back("jes" + src.first + "down");
    }
    if (attr == "mass" || attr == "msoftdrop") {
        if (m_jmsVals[1] != 1.) {
            products.emplace_back("jmsup");
            products.emplace_back("jmsdown");
        }
        if (m_doSmearing) {
            products.emplace_back("jmrup");
            products.emplace_back("jmrdown");
        }
    }
    return products;
}