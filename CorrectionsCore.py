import functools

from FLAF.Common.Utilities import *
from FLAF.RunKit.run_tools import ps_call

central = "Central"
up = "Up"
down = "Down"
nano = "nano"

pog_folder_names = {
    # BTV files are frozen to a dated version (as for JERC), never "latest": a new BTV release
    # changes the SFs silently. Check the version history (changes.md) before moving a date.
    "BTV": {
        "2016postVFP_UL": "Run2-2016postVFP-UL-NanoAODv9/2025-08-19",
        "2016preVFP_UL": "Run2-2016preVFP-UL-NanoAODv9/2025-08-19",
        "2017_UL": "Run2-2017-UL-NanoAODv9/2025-08-19",
        "2018_UL": "Run2-2018-UL-NanoAODv9/2025-08-19",
        "2022_Summer22": "Run3-22CDSep23-Summer22-NanoAODv12/2025-08-20",
        "2022_Summer22EE": "Run3-22EFGSep23-Summer22EE-NanoAODv12/2025-08-20",
        "2023_Summer23": "Run3-23CSep23-Summer23-NanoAODv12/2025-08-20",
        "2023_Summer23BPix": "Run3-23DSep23-Summer23BPix-NanoAODv12/2026-11-05",  # fixes the light-jet 20-30 GeV shape SF bin
        "2024_Summer24": "Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15/2026-10-20",
        "2025_Summer24": "Run3-25Prompt-Summer24-NanoAODv15/2026-10-14",
        "2025_Winter25": "",
        "2026_Summer24": "Run3-25Prompt-Summer24-NanoAODv15/2026-10-14",  # placeholder: no 2026 POG set yet
    },
    "JERC": {
        "2018_UL": "Run2-2018-UL-NanoAODv9",
        "2017_UL": "Run2-2017-UL-NanoAODv9",
        "2016preVFP_UL": "Run2-2016preVFP-UL-NanoAODv9",
        "2016postVFP_UL": "Run2-2016postVFP-UL-NanoAODv9",
        "JER": "JER-Smearing",
        "2022_Summer22": "Run3-22CDSep23-Summer22-NanoAODv12/2026-06-05",  #
        "2022_Prompt": "Run3-22Prompt-Winter22-NanoAODv12/2025-04-11",
        "2022_Summer22EE": "Run3-22EFGSep23-Summer22EE-NanoAODv12/2026-06-05",
        "2023_Summer23BPix": "Run3-23DSep23-Summer23BPix-NanoAODv12/2026-07-15",
        "2023_Summer23": "Run3-23CSep23-Summer23-NanoAODv12/2026-07-15",
        "2024_Winter24": "Run3-24Prompt-Winter24-NanoAODv14/2025-06-09",
        "2024_Summer24": "Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15/2026-06-05",  # https://cms-jerc.web.cern.ch/Recommendations/#2024
        "2025_Summer24": "Run3-25Prompt-Winter25-NanoAODv15/2026-06-05",  # TMP PATCH # --> Run3-25Prompt-Summer24-NanoAODv15 IS NOT AVAILABLE FOR JME but JME is the only one having Winter25 available. So by the time being we can have this tmp fix
        "2025_Winter25": "Run3-25Prompt-Winter25-NanoAODv15/2026-06-05",
        "2026_Summer24": "Run3-26Prompt-Summer24-NanoAODv15/2026-07-15",
    },
    "EGM": {
        "2016postVFP_UL": "Run2-2016postVFP-UL-NanoAODv15",
        # "2016postVFP_UL":"Run2-2016postVFP-UL-NanoAODv9",
        "2016preVFP_UL": "Run2-2016preVFP-UL-NanoAODv15",
        # "2016preVFP_UL":"Run2-2016preVFP-UL-NanoAODv9",
        "2017_UL": "Run2-2017-UL-NanoAODv15",
        # "2017_UL":"Run2-2017-UL-NanoAODv9",
        "2018_UL": "Run2-2018-UL-NanoAODv15",
        # "2018_UL":"Run2-2018-UL-NanoAODv9",
        "2022_Summer22": "Run3-22CDSep23-Summer22-NanoAODv12",
        "2022_Summer22EE": "Run3-22EFGSep23-Summer22EE-NanoAODv12",
        "2023_Summer23": "Run3-23CSep23-Summer23-NanoAODv12",
        "2023_Summer23BPix": "Run3-23DSep23-Summer23BPix-NanoAODv12",
        "2024_Summer24": "Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15",
        "2025_Summer24": "Run3-25Prompt-Summer24-NanoAODv15",
        "2025_Winter25": "",
        "2026_Summer24": "Run3-26Prompt-Summer24-NanoAODv15",  # no electron.json: electron.py reads the 2025 one
    },
    "LUM": {
        "2016postVFP_UL": "Run2-2016postVFP-UL-NanoAODv9",
        "2016preVFP_UL": "Run2-2016preVFP-UL-NanoAODv9",
        "2017_UL": "Run2-2017-UL-NanoAODv9",
        "2018_UL": "Run2-2018-UL-NanoAODv9",
        "2022_Summer22": "Run3-22CDSep23-Summer22-NanoAODv12",
        "2022_Summer22EE": "Run3-22EFGSep23-Summer22EE-NanoAODv12",
        "2023_Summer23": "Run3-23CSep23-Summer23-NanoAODv12",
        "2023_Summer23BPix": "Run3-23DSep23-Summer23BPix-NanoAODv12",
        "2024_Summer24": "Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15",
        "2025_Summer24": "Run3-25Prompt-Summer24-NanoAODv15",
        "2025_Winter25": "",
        "2026_Summer24": "Run3-25Prompt-Summer24-NanoAODv15",  # placeholder
    },
    "MUO": {
        "2016postVFP_UL": "Run2-2016postVFP-UL-NanoAODv9",
        "2016preVFP_UL": "Run2-2016preVFP-UL-NanoAODv9",
        "2017_UL": "Run2-2017-UL-NanoAODv9",
        "2018_UL": "Run2-2018-UL-NanoAODv9",
        "2022_Summer22": "Run3-22CDSep23-Summer22-NanoAODv12",
        "2022_Summer22EE": "Run3-22EFGSep23-Summer22EE-NanoAODv12",
        "2023_Summer23": "Run3-23CSep23-Summer23-NanoAODv12",
        "2023_Summer23BPix": "Run3-23DSep23-Summer23BPix-NanoAODv12",
        "2024_Summer24": "Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15",
        "2025_Summer24": "Run3-25Prompt-Summer24-NanoAODv15",
        "2025_Winter25": "",
        "2026_Summer24": "Run3-25Prompt-Summer24-NanoAODv15",  # placeholder
    },
    "TAU": {
        "2016postVFP_UL": "Run2-2016postVFP-UL-NanoAODv15",
        # "2016postVFP_UL":"Run2-2016postVFP-UL-NanoAODv9",
        "2016preVFP_UL": "Run2-2016preVFP-UL-NanoAODv15",
        # "2016preVFP_UL":"Run2-2016preVFP-UL-NanoAODv9",
        "2017_UL": "Run2-2017-UL-NanoAODv15",
        # "2017_UL":"Run2-2017-UL-NanoAODv9",
        "2018_UL": "Run2-2018-UL-NanoAODv15",
        # "2018_UL":"Run2-2018-UL-NanoAODv9",
        "2022_Summer22": "Run3-22CDSep23-Summer22-NanoAODv12",
        "2022_Summer22EE": "Run3-22EFGSep23-Summer22EE-NanoAODv12",
        "2023_Summer23": "Run3-23CSep23-Summer23-NanoAODv12",
        "2023_Summer23BPix": "Run3-23DSep23-Summer23BPix-NanoAODv12",
        "2024_Summer24": "Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15",
        "2025_Summer24": "Run3-25Prompt-Summer24-NanoAODv15",
        "2025_Winter25": "",
        "2026_Summer24": "Run3-25Prompt-Summer24-NanoAODv15",  # placeholder
    },
}

campaign_names = {
    "Run2_2016_HIPM": "2016preVFP_UL",
    "Run2_2016": "2016postVFP_UL",
    "Run2_2017": "2017_UL",
    "Run2_2018": "2018_UL",
    "Run3_2022": "2022_Summer22",
    "Run3_2022EE": "2022_Summer22EE",
    "Run3_2023": "2023_Summer23",
    "Run3_2023BPix": "2023_Summer23BPix",
    "Run3_2024": "2024_Summer24",  # 2024_Winter24
    "Run3_2025": "2025_Summer24",  # "2025_Winter25" is also a valid entry, but has files only only for JME
    "Run3_2026": "2026_Summer24",  # not every POG publishes 2026 sets yet: see pog_folder_names
}

campaign_years = {
    "2026_Summer24": "2026",
    "2025_Winter25": "2025",
    "2025_Summer24": "2025",
    "2024_Summer24": "2024",
    "2023_Summer23BPix": "2023",
    "2023_Summer23": "2023",
    "2022_Summer22EE": "2022",
    "2022_Summer22": "2022",
    "2018_UL": "2018",
    "2017_UL": "2017",
    "2016preVFP_UL": "2016",
    "2016postVFP_UL": "2016",
}


def findLibLocation(lib_name, first_guess=None):
    paths_to_check = []
    if first_guess is not None:
        paths_to_check.append(first_guess)
    other_paths = os.environ.get("LD_LIBRARY_PATH", "").split(":")
    paths_to_check.extend(other_paths)
    full_lib_name = f"lib{lib_name}.so"
    for path in paths_to_check:
        lib_path = os.path.join(path, full_lib_name)
        if os.path.exists(lib_path):
            return lib_path
    raise RuntimeError(f"Library {lib_name} not found.")


@functools.cache
def loadCorrectionLib():
    """Load correctionlib into ROOT and add its include path, once per process."""
    returncode, output, err = ps_call(
        ["correction", "config", "--cflags", "--ldflags"],
        catch_stdout=True,
        decode=True,
        verbose=0,
    )
    params = output.split(" ")
    lib_path = None
    for param in params:
        if param.startswith("-I"):
            ROOT.gInterpreter.AddIncludePath(param[2:].strip())
        elif param.startswith("-L"):
            lib_path = param[2:].strip()
        elif param.startswith("-l"):
            lib_name = param[2:].strip()
    ROOT.gSystem.Load(findLibLocation(lib_name, lib_path))


@functools.cache
def declareHeader(path):
    """Include a provider header into ROOT's interpreter, once per path and process: the C++
    classes are compiled once, and every era gets its own objects of them (CppProvider).
    """
    loadCorrectionLib()
    if not ROOT.gInterpreter.Declare(f'#include "{path}"'):
        raise RuntimeError(f"Unable to declare {path}.")


def declareProviderHeader(name):
    """declareHeader for a header of this package, by file name."""
    declareHeader(os.path.join(os.path.dirname(os.path.abspath(__file__)), name))


class CppProvider:
    """One C++ correction provider object, created and owned by this Python object.

    `ref` is a C++ expression for the object, to be used in the strings given to RDataFrame
    (`f"{provider.ref}->getWeight(...)"`). It holds the object's address, so this Python
    object has to outlive every dataframe built with it; the Corrections instance that owns
    the provider is kept on the DataFrameWrapper for that reason. `ref` is const: a JIT
    string that calls a non-const method fails when it is compiled.

    The constructor arguments are Python values, or with `cpp_args` a C++ argument list for
    the arguments that are C++ expressions (maps, vectors of enums).
    """

    def __init__(self, cpp_class, *args, cpp_args=None):
        self.cpp_class = cpp_class
        cls = functools.reduce(getattr, cpp_class.split("::"), ROOT)
        try:
            if cpp_args is None:
                self.obj = cls(*args)
            else:
                if args:
                    raise ValueError("either Python arguments or cpp_args, not both")
                address = ROOT.gInterpreter.ProcessLine(
                    f"new ::{cpp_class}({cpp_args});"
                )
                if not address:
                    raise RuntimeError("the constructor failed (see the error above)")
                self.obj = ROOT.BindObject(address, cls)
                self.obj.__python_owns__ = True
        except Exception as e:
            arguments = cpp_args if cpp_args is not None else args
            raise RuntimeError(
                f"Unable to construct {cpp_class} with arguments {arguments}: {e}"
            ) from e
        self.ref = (
            f"reinterpret_cast<const ::{cpp_class}*>({hex(ROOT.addressof(self.obj))})"
        )


# Sources whose variations are an indexed family rather than Up/Down -- PDF members, for
# instance. The scales are strings so they survive the anaCache JSON round trip unchanged.
_source_scales = {}


def registerSourceScales(source, scales):
    _source_scales[source] = [str(scale) for scale in scales]


def getScales(source=None):
    if source is None:
        return [central, up, down]
    if source == central:
        return [central]
    if source in _source_scales:
        return list(_source_scales[source])
    return [up, down]


def getSystName(source, scale):
    if source == central:
        if scale == central:
            return central
    elif source in _source_scales:
        if str(scale) in _source_scales[source]:
            return f"{source}{scale}"
    else:
        if scale in [up, down]:
            return source + scale
    raise RuntimeError(
        f"getSystName: inconsistent source:scale combination = {source}:{scale}"
    )


class ShapeWeightRegistry:
    """Which weight branches multiply into each (source, scale) variation.

    The normalisation weight is built once per variation, both as the numerator in
    Corrections.getNormalisationCorrections and as the anaCache denominator in
    FLAF/AnaProd/anaTupleProducer.py. Both need the same answer to the same question:
    for variation (source, scale), which weight branches multiply together?

    The answer is not "the branches of the producer that owns this source". A variation
    of one producer must still carry every *other* producer's central branch, or the
    ratio weight_base_<var> / weight_base_Central retains a spurious factor of one over
    that other producer's central weight. With pileup as the only non-central source
    that never showed up, because the only non-central keys belonged to pileup itself.

    Producers register the sources they own plus a (source, scale) -> branch-name
    callable, and this class does the cross product. Registration happens at every stage
    of a shape weight, so a branch written at AnaTuple can be named again at AnaTupleMerge
    without being recomputed.
    """

    def __init__(self):
        self._producers = []  # [(name, owned_sources, branch_fn)]

    def register(self, name, sources, branch_fn):
        if any(name == registered for registered, _, _ in self._producers):
            raise RuntimeError(f"ShapeWeightRegistry: duplicate producer '{name}'")
        self._producers.append((name, list(sources), branch_fn))

    @property
    def sources(self):
        sources = [central]
        for _, owned, _ in self._producers:
            sources.extend(owned)
        return sources

    def branches(self, source, scale):
        """Varied branch from the producer owning `source`, central from the rest."""
        return [
            (
                branch_fn(source, scale)
                if source in owned
                else branch_fn(central, central)
            )
            for _, owned, branch_fn in self._producers
        ]

    def asDict(self):
        return {
            (source, scale): self.branches(source, scale)
            for source in self.sources
            for scale in getScales(source)
        }


def splitSystName(syst_name):
    if syst_name == central:
        return (central, central)
    for suffix in [up, down]:
        if syst_name.endswith(suffix):
            source = syst_name[: -len(suffix)]
            scale = suffix
            return (source, scale)
    for source, scales in _source_scales.items():
        if syst_name.startswith(source) and syst_name[len(source) :] in scales:
            return (source, syst_name[len(source) :])
    raise RuntimeError(f"splitSystName: cannot split syst_name = {syst_name}")


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


def getLegTypeString(df, leg_type_column):
    column_type = df.GetColumnType(leg_type_column)
    if column_type in ["Int_t", "int"]:
        return f"static_cast<Leg>({leg_type_column})"
    elif column_type == "Leg":
        return leg_type_column
    else:
        raise RuntimeError(
            f"getLegTypeString: unsupported column type {column_type} for {leg_type_column}"
        )


def getChannelIdString(df, channel_id_column):
    column_type = df.GetColumnType(channel_id_column)
    if column_type in ["Int_t", "int"]:
        return f"static_cast<Channel>({channel_id_column})"
    elif column_type == "Channel":
        return channel_id_column
    else:
        raise RuntimeError(
            f"getChannelIdString: unsupported column type {column_type} for {channel_id_column}"
        )
