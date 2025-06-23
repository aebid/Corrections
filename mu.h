#pragma once

#include "correction.h"
#include "corrections.h"

namespace correction {

class MuCorrProvider : public CorrectionsBase<MuCorrProvider> {
public:
    enum class UncSource : int {
        Central = -1,
        NUM_GlobalMuons_DEN_genTracks = 0,
        NUM_HighPtID_DEN_genTracks = 1,
        NUM_HighPtID_DEN_TrackerMuons = 2,
        NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight = 3,
        NUM_LooseID_DEN_genTracks = 4,
        NUM_LooseID_DEN_TrackerMuons = 5,
        NUM_LooseRelIso_DEN_LooseID = 6,
        NUM_LooseRelIso_DEN_MediumID = 7,
        NUM_LooseRelIso_DEN_MediumPromptID = 8,
        NUM_LooseRelIso_DEN_TightIDandIPCut = 9,
        NUM_LooseRelTkIso_DEN_HighPtIDandIPCut = 10,
        NUM_LooseRelTkIso_DEN_TrkHighPtIDandIPCut = 11,
        NUM_MediumID_DEN_genTracks = 12,
        NUM_MediumID_DEN_TrackerMuons = 13,
        NUM_MediumPromptID_DEN_genTracks = 14,
        NUM_MediumPromptID_DEN_TrackerMuons = 15,
        NUM_Mu50_or_OldMu100_or_TkMu100_DEN_CutBasedIdGlobalHighPt_and_TkIsoLoose = 16,
        NUM_SoftID_DEN_genTracks = 17,
        NUM_SoftID_DEN_TrackerMuons = 18,
        NUM_TightID_DEN_genTracks = 19,
        NUM_TightID_DEN_TrackerMuons = 20,
        NUM_TightRelIso_DEN_MediumID = 21,
        NUM_TightRelIso_DEN_MediumPromptID = 22,
        NUM_TightRelIso_DEN_TightIDandIPCut = 23,
        NUM_TightRelTkIso_DEN_HighPtIDandIPCut = 24,
        NUM_TightRelTkIso_DEN_TrkHighPtIDandIPCut = 25,
        NUM_TrackerMuons_DEN_genTracks = 26,
        NUM_TrkHighPtID_DEN_genTracks = 27,
        NUM_TrkHighPtID_DEN_TrackerMuons = 28,
        NUM_IsoMu27_DEN_CutBasedIdTight_and_PFIsoTight = 29,
        NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight = 30,
        NUM_IsoMu24_DEN_CutBasedIdMedium_and_PFIsoMedium = 31,
        NUM_LoosePFIso_DEN_TightID = 32,
        NUM_LoosePFIso_DEN_MediumID = 33,

    };
    static const std::map<WorkingPointsMuonID, std::string>& getWPID()
    {
        static const std::map<WorkingPointsMuonID, std::string> names = {
            { WorkingPointsMuonID::HighPtID, "HighPtID"},
            { WorkingPointsMuonID::LooseID, "LooseID"},
            { WorkingPointsMuonID::MediumID, "MediumID"},
            { WorkingPointsMuonID::MediumPromptID, "MediumPromptID"},
            { WorkingPointsMuonID::SoftID, "SoftID"},
            { WorkingPointsMuonID::TightID, "TightID"},
            { WorkingPointsMuonID::TrkHighPtID, "TrkHighPtID"},
        };
        return names;
    };

    static const std::string& getScaleStr(UncScale scale)
    {
        static const std::map<UncScale, std::string> names = {
            { UncScale::Down, "systdown" },
            { UncScale::Central, "nominal" },
            { UncScale::Up, "systup" },
        };
        return names.at(scale);
    }

     static bool sourceApplies(UncSource source, const float Muon_pfRelIso04_all, const bool Muon_TightId, const float muon_Pt, const float Muon_tkRelIso, const bool Muon_highPtId, const bool Muon_MediumId)
    {
        // RECO
        if(source == UncSource::NUM_TrackerMuons_DEN_genTracks) return true;
        // ID
        if(source == UncSource::NUM_MediumID_DEN_genTracks && Muon_MediumId ) return true;
        if(source == UncSource::NUM_MediumID_DEN_TrackerMuons && Muon_MediumId ) return true;
        if(source == UncSource::NUM_TightID_DEN_TrackerMuons && Muon_TightId ) return true;
        if(source == UncSource::NUM_TightID_DEN_genTracks && Muon_TightId ) return true;
        if(source == UncSource::NUM_HighPtID_DEN_TrackerMuons && Muon_highPtId ) return true;
        if(source == UncSource::NUM_HighPtID_DEN_genTracks && Muon_highPtId ) return true;

        // ISO
        bool tightIDandIP_condition = (Muon_TightId && Muon_pfRelIso04_all<0.15);
        bool highPtIDandIP_condition = (Muon_highPtId && Muon_tkRelIso < 0.15);
        // bool MediumIdandLoosePFIso_condition = (Muon_MediumId && Muon_pfRelIso04_all < 0.25);
        if(source == UncSource::NUM_LoosePFIso_DEN_MediumID && Muon_MediumId ) return true;
        if(source == UncSource::NUM_TightRelIso_DEN_TightIDandIPCut && tightIDandIP_condition ) return true;
        if(source == UncSource::NUM_TightRelTkIso_DEN_TrkHighPtIDandIPCut && highPtIDandIP_condition ) return true;
        // }

        // TRG
        if(source == UncSource::NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight&& muon_Pt > 26) return true;
        if(source == UncSource::NUM_IsoMu27_DEN_CutBasedIdTight_and_PFIsoTight&& muon_Pt > 29) return true;
        if(source == UncSource::NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight&& muon_Pt > 26) return true;
        return false;
    }

    // static bool sourceAppliesMedium(UncSource source, const float Muon_pfRelIso04_all, const float muon_Pt, const bool Muon_MediumId){
    //     bool MediumID_condition = (Muon_MediumId ); //Since there is not an ISO, should we remove this pfRelIso?
    //     bool looseIso_condition = (Muon_pfRelIso04_all<0.25);
    //     if(source == UncSource::NUM_MediumID_DEN_TrackerMuons && MediumID_condition ) return true;
    //     if(source == UncSource::NUM_LoosePFIso_DEN_MediumID && MediumID_condition ) return true;
    //     return false;

    // }


    MuCorrProvider(const std::string& fileName, const std::string& era) :
    corrections_(CorrectionSet::from_file(fileName))
    {
        /*
        Eventually we want to switch this interface with a map and a loop
        map < era -> set<string>
        dict = {
            era: [list of silly names]
        }

        for sillyname in dict[era]:
            muIDCorr[sillyname] = corrections_->at[sillyname]
        */


        if (era == "Run2_2016" || era == "Run2_2016_HIPM" || era == "Run2_2017" || era == "Run2_2018"){
            muIDCorrections["NUM_TrackerMuons_DEN_genTracks"]=corrections_->at("NUM_TrackerMuons_DEN_genTracks");
            muIDCorrections["NUM_TightID_DEN_TrackerMuons"]=corrections_->at("NUM_TightID_DEN_TrackerMuons");
            muIDCorrections["NUM_TightID_DEN_genTracks"]=corrections_->at("NUM_TightID_DEN_genTracks");
            muIDCorrections["NUM_HighPtID_DEN_TrackerMuons"]=corrections_->at("NUM_HighPtID_DEN_TrackerMuons");
            muIDCorrections["NUM_HighPtID_DEN_genTracks"]=corrections_->at("NUM_HighPtID_DEN_genTracks");
            muIDCorrections["NUM_TightRelIso_DEN_TightIDandIPCut"]=corrections_->at("NUM_TightRelIso_DEN_TightIDandIPCut");
            muIDCorrections["NUM_TightRelTkIso_DEN_TrkHighPtIDandIPCut"]=corrections_->at("NUM_TightRelTkIso_DEN_TrkHighPtIDandIPCut");
        }
        if (era=="Run2_2018"){

            muIDCorrections["NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight"] = corrections_->at("NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight");
        }
        if(era=="Run2_2017"){
            muIDCorrections["NUM_IsoMu27_DEN_CutBasedIdTight_and_PFIsoTight"] = corrections_->at("NUM_IsoMu27_DEN_CutBasedIdTight_and_PFIsoTight");
        }
        if ((era == "Run2_2016_HIPM") || (era == "Run2_2016")){
            muIDCorrections["NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight"] = corrections_->at("NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight");
        }
        if (era == "Run3_2022" || era == "Run3_2022EE" || era == "Run3_2023" || era == "Run3_2023BPix"){
            muIDCorrections["NUM_TightID_DEN_TrackerMuons"]=corrections_->at("NUM_TightID_DEN_TrackerMuons");
            muIDCorrections["NUM_LoosePFIso_DEN_TightID"]=corrections_->at("NUM_LoosePFIso_DEN_TightID");
            muIDCorrections["NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight"]=corrections_->at("NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight");

            muIDCorrections["NUM_MediumID_DEN_TrackerMuons"]=corrections_->at("NUM_MediumID_DEN_TrackerMuons");
            muIDCorrections["NUM_LoosePFIso_DEN_MediumID"]=corrections_->at("NUM_LoosePFIso_DEN_MediumID");
            muIDCorrections["NUM_IsoMu24_DEN_CutBasedIdMedium_and_PFIsoMedium"]=corrections_->at("NUM_IsoMu24_DEN_CutBasedIdMedium_and_PFIsoMedium");

        }
    }
    // float getMuonSFMedium(const LorentzVectorM & muon_p4, const float Muon_pfRelIso04_all, const bool Muon_MediumId, UncSource source, UncScale scale) const {
    //     const UncScale muID_scale = sourceAppliesMedium(source, Muon_pfRelIso04_all,  muon_p4.Pt(), Muon_MediumId) ? scale : UncScale::Central;
    //     const std::string& scale_str = getScaleStr(muID_scale);
    //     return source == UncSource::Central ? 1. : muIDCorrections.at(getUncSourceName(source))->evaluate({abs(muon_p4.Eta()),muon_p4.Pt(), scale_str}) ;
    // }

    float getMuonSF(const LorentzVectorM & muon_p4, const float Muon_pfRelIso04_all, const bool Muon_TightId, const float Muon_tkRelIso, const bool Muon_highPtId, const bool Muon_MediumId, UncSource source, UncScale scale) const {
        const UncScale muID_scale = sourceApplies(source, Muon_pfRelIso04_all, Muon_TightId, muon_p4.Pt(), Muon_tkRelIso, Muon_highPtId, Muon_MediumId) ? scale : UncScale::Central;
        const std::string& scale_str = getScaleStr(muID_scale);
        if (source == UncSource::NUM_TrackerMuons_DEN_genTracks) {
            //const std::string& reco_scale_str = scale==UncScale::Central ? "nominal" : scale_str;
            return (muon_p4.Pt() >= 10 && muon_p4.Pt() < 200)? muIDCorrections.at(getUncSourceName(source))->evaluate({abs(muon_p4.Eta()), 50., scale_str}) : 1.;
        }
        static const double pt_low = 15.0;
        const double muon_pt = std::max(pt_low, muon_p4.pt());
        const float corr_SF = muIDCorrections.at(getUncSourceName(source))->evaluate({ abs(muon_p4.Eta()), muon_pt, scale_str});
        return source == UncSource::Central ? 1. : corr_SF ;
    }
    //Check range, but if it is out of range it is still valid and return 1.
    //Read json for bounds, min/max to be within, use that value
    //If its out of range return a bool as well
private:
    static const std::map<float, std::set<std::pair<float, float>>>& getRecoSFMap()
        {
            static const std::map<float, std::set<std::pair<float, float>>> RecoSFMap = {
                {50., { std::pair<float,float>(1.6, 0.9943),std::pair<float,float>(2.4, 1.0)} },
                {100., { std::pair<float,float>(1.6, 0.9948), std::pair<float,float>(2.4, 0.993)} },
                {150., { std::pair<float,float>(1.6, 0.9950), std::pair<float,float>(2.4, 0.990)} },
                {200., { std::pair<float,float>(1.6, 0.994), std::pair<float,float>(2.4, 0.988)} },
                {300., { std::pair<float,float>(1.6, 0.9914), std::pair<float,float>(2.4, 0.981)} },
                {400., { std::pair<float,float>(1.6, 0.993), std::pair<float,float>(2.4, 0.983)} },
                {600., { std::pair<float,float>(1.6, 0.991), std::pair<float,float>(2.4, 0.978)} },
                {1500., { std::pair<float,float>(1.6, 1.0), std::pair<float,float>(2.4, 0.98)} },
            };
            return RecoSFMap;
        }
    static std::string& getUncSourceName(UncSource source) {
        static std::string k = "Central";
        if (source == UncSource::NUM_GlobalMuons_DEN_genTracks) k = "NUM_GlobalMuons_DEN_genTracks";
        if (source == UncSource::NUM_HighPtID_DEN_genTracks) k = "NUM_HighPtID_DEN_genTracks";
        if (source == UncSource::NUM_HighPtID_DEN_TrackerMuons) k = "NUM_HighPtID_DEN_TrackerMuons";
        if (source == UncSource::NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight) k = "NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight";
        if (source == UncSource::NUM_IsoMu24_DEN_CutBasedIdMedium_and_PFIsoMedium) k = "NUM_IsoMu24_DEN_CutBasedIdMedium_and_PFIsoMedium";
        if (source == UncSource::NUM_LooseID_DEN_genTracks) k = "NUM_LooseID_DEN_genTracks";
        if (source == UncSource::NUM_LooseID_DEN_TrackerMuons) k = "NUM_LooseID_DEN_TrackerMuons";
        if (source == UncSource::NUM_LooseRelIso_DEN_LooseID) k = "NUM_LooseRelIso_DEN_LooseID";
        if (source == UncSource::NUM_LooseRelIso_DEN_MediumID) k = "NUM_LooseRelIso_DEN_MediumID";
        if (source == UncSource::NUM_LooseRelIso_DEN_MediumPromptID) k = "NUM_LooseRelIso_DEN_MediumPromptID";
        if (source == UncSource::NUM_LooseRelIso_DEN_TightIDandIPCut) k = "NUM_LooseRelIso_DEN_TightIDandIPCut";
        if (source == UncSource::NUM_LooseRelTkIso_DEN_HighPtIDandIPCut) k = "NUM_LooseRelTkIso_DEN_HighPtIDandIPCut";
        if (source == UncSource::NUM_LooseRelTkIso_DEN_TrkHighPtIDandIPCut) k = "NUM_LooseRelTkIso_DEN_TrkHighPtIDandIPCut";
        if (source == UncSource::NUM_MediumID_DEN_genTracks) k = "NUM_MediumID_DEN_genTracks";
        if (source == UncSource::NUM_MediumID_DEN_TrackerMuons) k = "NUM_MediumID_DEN_TrackerMuons";
        if (source == UncSource::NUM_LoosePFIso_DEN_MediumID) k = "NUM_LoosePFIso_DEN_MediumID";
        if (source == UncSource::NUM_MediumPromptID_DEN_genTracks) k = "NUM_MediumPromptID_DEN_genTracks";
        if (source == UncSource::NUM_MediumPromptID_DEN_TrackerMuons) k = "NUM_MediumPromptID_DEN_TrackerMuons";
        if (source == UncSource::NUM_Mu50_or_OldMu100_or_TkMu100_DEN_CutBasedIdGlobalHighPt_and_TkIsoLoose) k = "NUM_Mu50_or_OldMu100_or_TkMu100_DEN_CutBasedIdGlobalHighPt_and_TkIsoLoose";
        if (source == UncSource::NUM_SoftID_DEN_genTracks) k = "NUM_SoftID_DEN_genTracks";
        if (source == UncSource::NUM_SoftID_DEN_TrackerMuons) k = "NUM_SoftID_DEN_TrackerMuons";
        if (source == UncSource::NUM_TightID_DEN_genTracks) k = "NUM_TightID_DEN_genTracks";
        if (source == UncSource::NUM_TightID_DEN_TrackerMuons) k = "NUM_TightID_DEN_TrackerMuons";
        if (source == UncSource::NUM_TightRelIso_DEN_MediumID) k = "NUM_TightRelIso_DEN_MediumID";
        if (source == UncSource::NUM_TightRelIso_DEN_MediumPromptID) k = "NUM_TightRelIso_DEN_MediumPromptID";
        if (source == UncSource::NUM_TightRelIso_DEN_TightIDandIPCut) k = "NUM_TightRelIso_DEN_TightIDandIPCut";
        if (source == UncSource::NUM_TightRelTkIso_DEN_HighPtIDandIPCut) k = "NUM_TightRelTkIso_DEN_HighPtIDandIPCut";
        if (source == UncSource::NUM_TightRelTkIso_DEN_TrkHighPtIDandIPCut) k = "NUM_TightRelTkIso_DEN_TrkHighPtIDandIPCut";
        if (source == UncSource::NUM_TrackerMuons_DEN_genTracks) k = "NUM_TrackerMuons_DEN_genTracks";
        if (source == UncSource::NUM_TrkHighPtID_DEN_genTracks) k = "NUM_TrkHighPtID_DEN_genTracks";
        if (source == UncSource::NUM_TrkHighPtID_DEN_TrackerMuons) k = "NUM_TrkHighPtID_DEN_TrackerMuons";
        if (source == UncSource::NUM_LoosePFIso_DEN_TightID) k = "NUM_LoosePFIso_DEN_TightID";
        return k;
    }
private:
    std::unique_ptr<CorrectionSet> corrections_;
    std::map<std::string, Correction::Ref> muIDCorrections;

};


class HighPtMuCorrProvider : public CorrectionsBase<HighPtMuCorrProvider> {
public:
    enum class UncSource : int {
        Central = -1,
        NUM_GlobalMuons_DEN_TrackerMuonProbes = 0,
        NUM_HighPtID_DEN_GlobalMuonProbes = 1,
        NUM_TrkHighPtID_DEN_GlobalMuonProbes = 2,
        NUM_probe_LooseRelTkIso_DEN_HighPtProbes = 3,
        NUM_probe_TightRelTkIso_DEN_HighPtProbes = 4,
        NUM_probe_LooseRelTkIso_DEN_TrkHighPtProbes = 5,
        NUM_probe_TightRelTkIso_DEN_TrkHighPtProbes = 6,
        NUM_TightID_DEN_GlobalMuonProbes = 7,
        NUM_MediumID_DEN_GlobalMuonProbes = 8,
        NUM_probe_LooseRelTkIso_DEN_MediumIDProbes = 9,
        NUM_probe_TightRelTkIso_DEN_MediumIDProbes = 10,
        NUM_HLT_DEN_TrkHighPtTightRelIsoProbes = 11,
        NUM_HLT_DEN_TrkHighPtLooseRelIsoProbes = 12,
        NUM_HLT_DEN_HighPtTightRelIsoProbes = 13,
        NUM_HLT_DEN_HighPtLooseRelIsoProbes = 14,
        NUM_HLT_DEN_MediumIDTightRelIsoProbes = 15,
        NUM_HLT_DEN_MediumIDLooseRelIsoProbes = 16
    };

    static const std::string& getScaleStr(UncScale scale)
    {
        static const std::map<UncScale, std::string> names = {
            { UncScale::Down, "systdown" },
            { UncScale::Central, "nominal" },
            { UncScale::Up, "systup" },
        };
        return names.at(scale);
    }

     static bool sourceApplies(UncSource source, const float Muon_pfRelIso04_all, const bool Muon_TightId, const float muon_Pt, const float Muon_tkRelIso, const bool Muon_highPtId,const bool Muon_MediumPtId)
    {
        // RECO
        if (source == UncSource::NUM_GlobalMuons_DEN_TrackerMuonProbes) return true;
        // ID
        if(source == UncSource::NUM_TightID_DEN_GlobalMuonProbes && Muon_TightId ) return true;
        if(source == UncSource::NUM_HighPtID_DEN_GlobalMuonProbes && Muon_highPtId ) return true;
        if(source == UncSource::NUM_MediumID_DEN_GlobalMuonProbes && Muon_MediumPtId ) return true;
        if(source == UncSource::NUM_HLT_DEN_MediumIDLooseRelIsoProbes && (Muon_MediumPtId && Muon_pfRelIso04_all < 0.25 ) ) return true;
        // ISO
        bool highPtID_condition = (Muon_highPtId && Muon_tkRelIso < 0.15);
        if (source == UncSource::NUM_probe_TightRelTkIso_DEN_HighPtProbes && highPtID_condition ) return true;
        if (source == UncSource::NUM_probe_LooseRelTkIso_DEN_MediumIDProbes && Muon_MediumPtId && Muon_tkRelIso < 0.25) return true;
        return false;
    }

    HighPtMuCorrProvider(const std::string& fileName) :
    corrections_(CorrectionSet::from_file(fileName))
    {
        highPtmuCorrections["NUM_GlobalMuons_DEN_TrackerMuonProbes"]=corrections_->at("NUM_GlobalMuons_DEN_TrackerMuonProbes");
        highPtmuCorrections["NUM_TightID_DEN_GlobalMuonProbes"]=corrections_->at("NUM_TightID_DEN_GlobalMuonProbes");
        highPtmuCorrections["NUM_HighPtID_DEN_GlobalMuonProbes"]=corrections_->at("NUM_HighPtID_DEN_GlobalMuonProbes");
        highPtmuCorrections["NUM_MediumID_DEN_GlobalMuonProbes"]=corrections_->at("NUM_MediumID_DEN_GlobalMuonProbes");
        highPtmuCorrections["NUM_HLT_DEN_MediumIDLooseRelIsoProbes"]=corrections_->at("NUM_HLT_DEN_MediumIDLooseRelIsoProbes");
        highPtmuCorrections["NUM_probe_TightRelTkIso_DEN_HighPtProbes"]=corrections_->at("NUM_probe_TightRelTkIso_DEN_HighPtProbes");
        highPtmuCorrections["NUM_probe_LooseRelTkIso_DEN_MediumIDProbes"]=corrections_->at("NUM_probe_LooseRelTkIso_DEN_MediumIDProbes");

    }

    float getHighPtMuonSF(const LorentzVectorM & muon_p4, const float Muon_pfRelIso04_all, const bool Muon_TightId, const float Muon_tkRelIso, const bool Muon_highPtId, const bool Muon_MediumPtId, UncSource source, UncScale scale) const {

        const UncScale muID_scale = sourceApplies(source, Muon_pfRelIso04_all, Muon_TightId, muon_p4.Pt(), Muon_tkRelIso, Muon_highPtId, Muon_MediumPtId) ? scale : UncScale::Central;
        const std::string& scale_str = getScaleStr(muID_scale);
        const auto mu_p = std::hypot(muon_p4.Px(),muon_p4.Py(),muon_p4.Pz());
        if (source == UncSource::NUM_GlobalMuons_DEN_TrackerMuonProbes) {
            return (muon_p4.Pt()>=200)? highPtmuCorrections.at(getUncSourceName(source))->evaluate({abs(muon_p4.Eta()), mu_p, scale_str}) : 1. ;
        }
        static const double pt_low = 50.0;
        const double muon_pt = std::max(pt_low, muon_p4.pt());
        const float corr_SF = highPtmuCorrections.at(getUncSourceName(source))->evaluate({abs(muon_p4.Eta()), muon_pt, scale_str});
        return source == UncSource::Central ? 1. : corr_SF ;
    }

private:

    static std::string& getUncSourceName(UncSource source) {
        static std::string sourcename = "Central";
        if (source == UncSource::NUM_GlobalMuons_DEN_TrackerMuonProbes) sourcename =  "NUM_GlobalMuons_DEN_TrackerMuonProbes";
        if (source == UncSource::NUM_HighPtID_DEN_GlobalMuonProbes) sourcename =  "NUM_HighPtID_DEN_GlobalMuonProbes";
        if (source == UncSource::NUM_TrkHighPtID_DEN_GlobalMuonProbes) sourcename =  "NUM_TrkHighPtID_DEN_GlobalMuonProbes";
        if (source == UncSource::NUM_probe_LooseRelTkIso_DEN_HighPtProbes) sourcename =  "NUM_probe_LooseRelTkIso_DEN_HighPtProbes";
        if (source == UncSource::NUM_probe_TightRelTkIso_DEN_HighPtProbes) sourcename =  "NUM_probe_TightRelTkIso_DEN_HighPtProbes";
        if (source == UncSource::NUM_probe_LooseRelTkIso_DEN_TrkHighPtProbes) sourcename =  "NUM_probe_LooseRelTkIso_DEN_TrkHighPtProbes";
        if (source == UncSource::NUM_probe_TightRelTkIso_DEN_TrkHighPtProbes) sourcename =  "NUM_probe_TightRelTkIso_DEN_TrkHighPtProbes";
        if (source == UncSource::NUM_TightID_DEN_GlobalMuonProbes) sourcename =  "NUM_TightID_DEN_GlobalMuonProbes";
        if (source == UncSource::NUM_MediumID_DEN_GlobalMuonProbes) sourcename =  "NUM_MediumID_DEN_GlobalMuonProbes";
        if (source == UncSource::NUM_probe_LooseRelTkIso_DEN_MediumIDProbes) sourcename =  "NUM_probe_LooseRelTkIso_DEN_MediumIDProbes";
        if (source == UncSource::NUM_probe_TightRelTkIso_DEN_MediumIDProbes) sourcename =  "NUM_probe_TightRelTkIso_DEN_MediumIDProbes";
        if (source == UncSource::NUM_HLT_DEN_TrkHighPtTightRelIsoProbes) sourcename =  "NUM_HLT_DEN_TrkHighPtTightRelIsoProbes";
        if (source == UncSource::NUM_HLT_DEN_TrkHighPtLooseRelIsoProbes) sourcename =  "NUM_HLT_DEN_TrkHighPtLooseRelIsoProbes";
        if (source == UncSource::NUM_HLT_DEN_HighPtTightRelIsoProbes) sourcename =  "NUM_HLT_DEN_HighPtTightRelIsoProbes";
        if (source == UncSource::NUM_HLT_DEN_HighPtLooseRelIsoProbes) sourcename =  "NUM_HLT_DEN_HighPtLooseRelIsoProbes";
        if (source == UncSource::NUM_HLT_DEN_MediumIDTightRelIsoProbes) sourcename =  "NUM_HLT_DEN_MediumIDTightRelIsoProbes";
        if (source == UncSource::NUM_HLT_DEN_MediumIDLooseRelIsoProbes) sourcename =  "NUM_HLT_DEN_MediumIDLooseRelIsoProbes";
        return sourcename;
    }
private:
    std::unique_ptr<CorrectionSet> corrections_;
    std::map<std::string, Correction::Ref> highPtmuCorrections;

};



class LowPtMuCorrProvider : public CorrectionsBase<LowPtMuCorrProvider> {
public:
    enum class UncSource : int {
        Central = -1,
        NUM_LooseID_DEN_TrackerMuons = 0,
        NUM_MediumID_DEN_TrackerMuons = 1,
        NUM_SoftID_DEN_TrackerMuons = 2,
        NUM_TightID_DEN_TrackerMuons = 3
    };

    static const std::string& getScaleStr(UncScale scale)
    {
        static const std::map<UncScale, std::string> names = {
            { UncScale::Down, "systdown" },
            { UncScale::Central, "nominal" },
            { UncScale::Up, "systup" },
        };
        return names.at(scale);
    }

    //We can probably remove this highPtId bool, or maybe we will have to invent a lowPtId
    static bool sourceApplies(UncSource source, const float Muon_pfRelIso04_all, const bool Muon_TightId, const float muon_Pt, const float Muon_tkRelIso, const bool Muon_highPtId, const bool Muon_MediumId)
    {
        // ID
        bool tightID_condition = (Muon_TightId && Muon_pfRelIso04_all<0.15); //Since there is not an ISO, should we remove this pfRelIso?
        if(source == UncSource::NUM_TightID_DEN_TrackerMuons && tightID_condition ) return true;
        if(source == UncSource::NUM_MediumID_DEN_TrackerMuons && Muon_MediumId ) return true;
        return false;
    }

    LowPtMuCorrProvider(const std::string& fileName) :
    corrections_(CorrectionSet::from_file(fileName))
    {
        lowPtmuCorrections["NUM_TightID_DEN_TrackerMuons"]=corrections_->at("NUM_TightID_DEN_TrackerMuons");
        lowPtmuCorrections["NUM_MediumID_DEN_TrackerMuons"]=corrections_->at("NUM_MediumID_DEN_TrackerMuons");

    }
    float getLowPtMuonSF(const LorentzVectorM & muon_p4, const float Muon_pfRelIso04_all, const bool Muon_TightId, const float Muon_tkRelIso, const bool Muon_highPtId, const bool Muon_MediumId, UncSource source, UncScale scale) const {
        const UncScale muID_scale = sourceApplies(source, Muon_pfRelIso04_all, Muon_TightId, muon_p4.Pt(), Muon_tkRelIso, Muon_highPtId, Muon_MediumId) ? scale : UncScale::Central;
        const std::string& scale_str = getScaleStr(muID_scale);
        return source == UncSource::Central ? 1. : lowPtmuCorrections.at(getUncSourceName(source))->evaluate({abs(muon_p4.Eta()),muon_p4.Pt(), scale_str}) ;
    }




private:

    static std::string& getUncSourceName(UncSource source) {
        static std::string sourcename = "Central";
        if (source == UncSource::NUM_LooseID_DEN_TrackerMuons) sourcename =  "NUM_LooseID_DEN_TrackerMuons";
        if (source == UncSource::NUM_MediumID_DEN_TrackerMuons) sourcename =  "NUM_MediumID_DEN_TrackerMuons";
        if (source == UncSource::NUM_SoftID_DEN_TrackerMuons) sourcename =  "NUM_SoftID_DEN_TrackerMuons";
        if (source == UncSource::NUM_TightID_DEN_TrackerMuons) sourcename =  "NUM_TightID_DEN_TrackerMuons";
        return sourcename;
    }
private:
    std::unique_ptr<CorrectionSet> corrections_;
    std::map<std::string, Correction::Ref> lowPtmuCorrections;

};


} // namespace correction

