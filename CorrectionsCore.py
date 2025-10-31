from FLAF.Common.Utilities import *

central = "Central"
up = "Up"
down = "Down"
nano = "nano"

period_names = {
    "Run2_2016_HIPM": "2016preVFP_UL",
    "Run2_2016": "2016postVFP_UL",
    "Run2_2017": "2017_UL",
    "Run2_2018": "2018_UL",
    "Run3_2022": "2022_Summer22",
    "Run3_2022EE": "2022_Summer22EE",
    "Run3_2023": "2023_Summer23",
    "Run3_2023BPix": "2023_Summer23BPix",
}

periods = {
    "2023_Summer23BPix": "2023",
    "2023_Summer23": "2023",
    "2022_Summer22EE": "2022",
    "2022_Summer22": "2022",
    "2018_UL": "2018",
    "2017_UL": "2017",
    "2016preVFP_UL": "2016",
    "2016postVFP_UL": "2016",
}


def getScales(source=None):
    if source is None:
        return [central, up, down]
    if source == central:
        return [central]
    return [up, down]


def getSystName(source, scale):
    if source == central:
        if scale == central:
            return central
    else:
        if scale in [up, down]:
            return source + scale
    raise RuntimeError(
        f"getSystName: inconsistent source:scale combination = {source}:{scale}"
    )


def updateSourceDict(source_dict, source, obj):
    if source not in source_dict:
        source_dict[source] = []
    if obj in source_dict[source]:
        raise RuntimeError(f"addUncSource: duplicated {source} definition for {obj}")
    source_dict[source].append(obj)


def createWPChannelMap(map_wp_python):
    ch_list = []
    for ch, ch_data in map_wp_python.items():
        wp_list = []
        for k in ["e", "mu", "jet"]:
            wp_class = globals()[f"WorkingPointsTauVS{k}"]
            wp_name = ch_data[f"VS{k}"]
            wp_value = getattr(wp_class, wp_name).value
            wp_entry = f'{{ "{wp_name}", {wp_value} }} '
            wp_list.append(wp_entry)
        wp_str = ", ".join(wp_list)
        ch_str = f"{{ Channel::{ch}, {{ {wp_str} }} }}"
        ch_list.append(ch_str)
    map_str = "::correction::TauCorrProvider::wpsMapType({" + ", ".join(ch_list) + "})"
    return map_str


def createTauSFTypeMap(map_sf_python):
    map_sf_cpp = "std::map<Channel, std::string>({"
    for ch, ch_data in map_sf_python.items():
        map_sf_cpp += f'{{ Channel::{ch}, "{ch_data}" }}, '
    map_sf_cpp += "})"
    return map_sf_cpp
