// Custom MET scale factors derived with https://github.com/bfonta/inclusion
#ifndef ScaleFactorMET_h
#define ScaleFactorMET_h

#include <iostream>
#include <string>
#include <unordered_map>
#include <memory>
#include <utility>
#include <cassert>

#include "TROOT.h"
#include "TFile.h"
#include "TF1.h"

class ScaleFactorMET {
public:
  ScaleFactorMET(std::string,TF1* funcSF_, TF1* funcMC_,TF1* funcData_ );
  ~ScaleFactorMET();

  double getSF(double);
  double getSFError(double);
  float getMinThreshold();

  template <typename T>
  using uMap = std::unordered_map<std::string, T>;

private:
  TF1 *funcSF, *funcData, *funcMC;
  //std::unique_ptr<TF1> funcSF, funcMC, funcData;
  std::string mPeriod;
  std::array<std::string, 4> mPeriods = {{"2016preVFP", "2016postVFP", "2017", "2018"}};
  const uMap<std::pair<double, double>> mRange = {
	{"2016preVFP",  {150., 350.}},
	{"2016postVFP", {150., 350.}},
	{"2017",        {150., 350.}},
	{"2018",        {150., 350.}}
  };

  void mCheckPeriod();
  double mErrorQuadSumSquared(double, std::string);
  double mErrorRatio(double);
  double mImposeBounds(double);
};

#endif