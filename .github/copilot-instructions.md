# Copilot Instructions for Corrections Repository

## Repository Overview

This repository provides Monte Carlo (MC) corrections for CMS (Compact Muon Solenoid) physics analyses. It is a submodule of the [FLAF](https://github.com/cms-flaf/FLAF) framework. The codebase provides scale factors, energy corrections, and systematic uncertainties for various physics objects (jets, taus, electrons, muons, MET, b-tagging, etc.) across Run 2 and Run 3 LHC data-taking periods.

**Languages**: Python (~60%), C++ (~40%)
**Dependencies**: ROOT (PyROOT), correctionlib, CVMFS (for JSON POG files), FLAF framework
**Size**: ~8,800 lines of code (excluding data files)

## Project Structure

```
Corrections/
├── Corrections.py          # Main entry point - initializes all correction modules
├── CorrectionsCore.py      # Core utilities: period names, scale handling, helper functions
├── corrections.h           # Core C++ header with common types and CorrectionsBase template
├── tau.{py,h}              # Tau ID/ES scale factors (DeepTau)
├── jet.{py,h}              # Jet energy corrections (JEC/JER)
├── fatjet.{py,h}           # Fat jet (AK8) corrections
├── electron.{py,h}         # Electron ID and energy scale
├── mu.{py,h}               # Muon ID/isolation scale factors
├── btag.{py,h}             # B-tagging scale factors
├── btagShape.h             # B-tag shape corrections
├── pu.{py,h}               # Pileup reweighting
├── met.{py,h}              # MET corrections and propagation
├── triggers.{py,h}         # Run 2 trigger scale factors
├── triggersRun3.{py,h}     # Run 3 trigger scale factors
├── puJetID.{py,h}          # Pileup jet ID
├── Vpt.{py,h}              # V boson pT corrections
├── lumi.{py,h}             # Luminosity handling
├── JetVetoMap.{py,h}       # Jet veto maps
├── MuonScaRe*.{py,h}       # Muon scale/resolution corrections
├── JME*.{cc,h}             # Jet/MET systematics calculators
├── SF_Met.{cc,h}           # MET scale factor utilities
├── FatJetSystematicCalculator.{cc,h}  # Fat jet systematic calculations
├── data/                   # Correction data files (JSON, ROOT)
│   ├── BTV/                # B-tagging efficiencies
│   ├── EGM/                # Electron/gamma corrections
│   ├── MUO/                # Muon corrections
│   ├── TAU/                # Tau corrections
│   ├── TRG/                # Trigger scale factors
│   ├── EWK_Corr_Vpt/       # Electroweak V pT corrections
│   └── golden_json/        # Certified luminosity JSONs
├── .clang-format           # C++ formatting configuration (Google style base)
├── .editorconfig           # Editor settings (4 spaces, UTF-8, trim trailing whitespace)
└── .github/workflows/      # CI workflows
```

## Code Formatting and Validation

### Required: Run formatting checks before committing

**Always run these commands on changed files before committing:**

```bash
# Python files - format with black (auto-formats)
black file1.py file2.py

# Check Python formatting without modifying
black --check --diff file.py

# C++ files - format with clang-format (auto-formats in place)
clang-format -i file.h file.cc

# Check C++ formatting without modifying
clang-format --dry-run --Werror file.h file.cc
```

### CI Validation (runs on pull requests to main)

The `formatting-check.yaml` workflow checks:
1. Python files with `black --check`
2. C++ files (`.cpp`, `.h`, `.hpp`, `.cc`) with `clang-format --dry-run --Werror`

Only changed files in the PR are checked.

## Code Patterns

### Python Module Pattern

Each correction type follows this pattern:
```python
import os
import ROOT
from .CorrectionsCore import *  # Imports: central, up, down, period_names, etc.

class XCorrProducer:
    jsonPath = "/cvmfs/.../path.json.gz"  # CVMFS path for corrections
    initialized = False  # Class-level singleton tracking

    def __init__(self, period, ...):
        if not XCorrProducer.initialized:
            headers_dir = os.path.dirname(os.path.abspath(__file__))
            header_path = os.path.join(headers_dir, "x.h")
            ROOT.gInterpreter.Declare(f'#include "{header_path}"')
            ROOT.gInterpreter.ProcessLine(f'::correction::XCorrProvider::Initialize(...)')
            XCorrProducer.initialized = True
```

### C++ Provider Pattern

Each C++ correction provider inherits from `CorrectionsBase`:
```cpp
#include "correction.h"  // correctionlib
#include "corrections.h"  // CorrectionsBase template

namespace correction {
    class XCorrProvider : public CorrectionsBase<XCorrProvider> {
    public:
        enum class UncSource : int { Central = -1, ... };

        XCorrProvider(const std::string& jsonFile, ...) :
            corrections_(CorrectionSet::from_file(jsonFile)),
            ... {}

        // Methods called via ROOT JIT compilation
        double getSF(...) const;
    };
}
```

### Key Constants (from CorrectionsCore.py)

```python
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
```

## Dependencies

- **FLAF Framework**: This repository is a submodule of FLAF. Imports like `from FLAF.Common.Utilities import *` require the parent framework.
- **ROOT/PyROOT**: Used for JIT compilation of C++ code and data analysis.
- **correctionlib**: JSON-based correction library (`correction.h`).
- **CVMFS**: Corrections JSON files are served from `/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/`.

## Testing Notes

- This repository has no standalone test suite. Testing is done within the FLAF framework context.
- The `/test` directory is gitignored.
- Validation relies on formatting checks and integration with the parent framework.

## Important Considerations

1. **Period-specific logic**: Many classes have period-dependent behavior (Run2 vs Run3, year-specific corrections). Check existing period handling patterns.

2. **Singleton initialization**: Each `*CorrProducer` class uses a class-level `initialized` flag. Ensure new classes follow this pattern.

3. **Scale factor naming**: Follow the `{source}{scale}` naming convention (e.g., `TauES_DM0Up`, `btagSFbc_uncorrelatedDown`).

4. **File paths**: CVMFS paths are formatted with period names. Environment variable `ANALYSIS_PATH` is used for local file resolution.

5. **Data files**: Large correction files are in `data/`. When adding new corrections, follow existing directory structure.

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| Black formatting fails | Line length, trailing whitespace | Run `black file.py` |
| clang-format fails | C++ style violations | Run `clang-format -i file.h` |
| Import errors (FLAF) | Missing parent framework | Code runs within FLAF context only |
| CVMFS path not found | Missing corrections | Check if period is supported |

Trust these instructions. Only perform additional searches if information here is incomplete or found to be incorrect.
