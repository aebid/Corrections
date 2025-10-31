#pragma once

#include <set>
#include <map>

#include <boost/json/src.hpp>
#include "corrections.h"

class LumiFilter : public correction::CorrectionsBase<LumiFilter> {
  public:
    using RunType = unsigned int;
    using LumiType = unsigned int;
    using LumiRange = std::pair<LumiType, LumiType>;
    using LumiRangeList = std::vector<LumiRange>;
    using LumiMap = std::map<RunType, LumiRangeList>;

    static boost::json::value ParseFile(const std::string& jsonFile) {
        std::ifstream f(jsonFile);
        const std::string input((std::istreambuf_iterator<char>(f)), {});
        boost::json::error_code ec;
        const auto lumiJson = boost::json::parse(input, ec);
        if (ec)
            throw std::invalid_argument("LumiFilter: Invalid lumi json file = '" + jsonFile +
                                        "'. Error while parsing: " + ec.message());
        return lumiJson;
    }

    template <typename FieldType>
    FieldType Parse(const std::string& fieldStr, const std::string& fieldName) {
        std::istringstream ss(fieldStr);
        FieldType field;
        ss >> field;
        if (ss.fail())
            throw std::invalid_argument("LumiFilter: Invalid " + fieldName + " = '" + fieldStr + "'.");
        return field;
    }

    LumiFilter(const std::string& lumiJsonFile) {
        const auto lumiJson = ParseFile(lumiJsonFile);
        if (!lumiJson.is_object())
            throw std::invalid_argument("LumiFilter: Invalid lumi json file = '" + lumiJsonFile +
                                        "'. Root element is not an object.");
        for (const auto& [runStrRaw, lumiList] : lumiJson.as_object()) {
            const std::string runStr(runStrRaw.begin(), runStrRaw.end());
            const auto run = Parse<RunType>(runStr, "run");
            if (!lumiList.is_array())
                throw std::invalid_argument("LumiFilter: Invalid lumi json file = '" + lumiJsonFile +
                                            "'. Lumi list for run = " + runStr + " is not an array.");
            for (const auto& lumiRangeValue : lumiList.as_array()) {
                if (!lumiRangeValue.is_array())
                    throw std::invalid_argument("LumiFilter: Invalid lumi json file = '" + lumiJsonFile +
                                                "'. Lumi range for run = " + runStr + " is not an array.");
                const auto& lumiRangeArray = lumiRangeValue.as_array();
                if (lumiRangeArray.size() != 2)
                    throw std::invalid_argument("LumiFilter: Invalid lumi json file = '" + lumiJsonFile +
                                                "'. Lumi range for run = " + runStr + " has size != 2.");
                if (!lumiRangeArray[0].is_int64() || !lumiRangeArray[1].is_int64())
                    throw std::invalid_argument("LumiFilter: Invalid lumi json file = '" + lumiJsonFile +
                                                "'. Lumi range for run = " + runStr + " has non-integer elements.");
                LumiRange lumiRange;
                lumiRange.first = lumiRangeArray.at(0).as_int64();
                lumiRange.second = lumiRangeArray.at(1).as_int64();
                lumiMap_[run].push_back(lumiRange);
            }
        }
        for (auto& [run, lumiRangeList] : lumiMap_) {
            if (lumiRangeList.size() > 0) {
                std::sort(lumiRangeList.begin(), lumiRangeList.end());
                for (size_t n = 0; n < lumiRangeList.size() - 1; ++n) {
                    if (lumiRangeList[n + 1].first <= lumiRangeList[n].second) {
                        std::ostringstream os;
                        os << "LumiFilter: overlaping ranges for run = " << run << ". lumiRange1 = ["
                           << lumiRangeList[n].first << ", " << lumiRangeList[n].second << "]. lumiRange2 = ["
                           << lumiRangeList[n + 1].first << ", " << lumiRangeList[n + 1].second << "].";
                        throw std::invalid_argument(os.str());
                    }
                }
            }
        }
    }

    bool Pass(RunType run, LumiType luminosityBlock) const {
        const auto iter = lumiMap_.find(run);
        if (iter == lumiMap_.end())
            return false;
        for (const LumiRange& range : iter->second) {
            if (luminosityBlock < range.first)
                return false;
            if (luminosityBlock <= range.second)
                return true;
        }
        return false;
    }

  private:
    LumiMap lumiMap_;
};