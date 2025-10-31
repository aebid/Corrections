import ROOT
import os


class LumiFilter:
    initialized = False

    def __init__(self, lumi_json_file):
        if not LumiFilter.initialized:
            lumi_filter_header = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "lumi.h"
            )
            ROOT.gInterpreter.Declare(f'#include "{lumi_filter_header}"')
            ROOT.gInterpreter.ProcessLine(
                f'LumiFilter::Initialize("{lumi_json_file}");'
            )
            LumiFilter.initialized = True

    def filter(self, df):
        return df.Filter("LumiFilter::getGlobal().Pass(run, luminosityBlock)")
