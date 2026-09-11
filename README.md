# Dependence Without Predictability in Forecasting Seven African Great Lakes from Fused Satellite Altimetry

Code and supporting materials for an MSc Data Science extended research project
(University of Manchester, 2026).

The project builds a continuous, datum-consistent monthly water-level record for seven lakes of
the East African Rift from three satellite radar altimetry repositories, recovers a directed
dependence network between them using Convergent Cross Mapping (CCM), and tests whether that
network carries transferable forecasting information against calibrated null controls.

This repository is the reproducibility package for that report. It contains every notebook,
module and reference output needed to regenerate the reported results, and nothing that does not
serve that purpose.

---

## Layout

The repository root is the project directory. Notebooks read their inputs with paths relative
to it — `Grealm Data/…`, `Code Outputs/…`, `Climate Indices/…` — so they run from here, with the
imported modules beside them. They are deliberately not split into `src/` and `notebooks/`
subfolders: moving them would change their working directory and break every one of those
relative paths. The numbering carries the run order.

```
00_collate_victoria_tanganyika.ipynb   …   22_study_area_map.ipynb
ccm_core.py            imported by stage 10
gnarx_core.py          imported by stage 16
forecast_gnarx.py      imported by stage 16

validate_ccm.ipynb     estimator validation, outside the run order
validate_gnarx.ipynb   estimator validation, outside the run order

Grealm Data/           not redistributed — download here
Copernicus Data/       not redistributed — download here
DAHITI Data/           not redistributed — download here
Climate Indices/       committed: dmi.csv, nino34.csv
Code Outputs/          committed: every table and figure cited in the report,
                       organised by stage, including the four derived .xlsx products

docs/                  technical appendix, pipeline schematic, data instructions
environment.yml        the conda environment as used
verify_outputs.py      compares a reproduction against the committed outputs
```

The run order groups into five bands:

| Stages | What happens |
|---|---|
| `00`–`05` | Record construction — collation, bias-aligned fusion, gap interpolation, ERA5 download and per-lake climate extraction |
| `06`–`09` | Exploratory analysis — STL, stationarity, trends, PCA, and the climate stock-versus-flux contrast |
| `10` | Dependence — the CCM network, four preprocessing variants, 200 surrogates |
| `11`–`19` | Forecasting — univariate baselines, VAR/VARX, SARIMAX, the graph neural network, GNAR/GNARX, and both calibrated nulls |
| `20`–`22` | Reported output — scale-free metrics, the report figures, the study area map |


`Code Outputs/` holds the authors' own results, organised by stage. It is mostly a reference, but
not purely: four derived products live inside it and later stages read them from there —
`Lake Level Outputs/African_Great_Lakes_Water_Levels.xlsx`,
`Fusion Outputs/Unified_BiasAligned_Levels.xlsx`,
`Gap Interpolation Outputs/Unified_Interpolated_Levels.xlsx` and
`Climate Data Extraction Outputs/Lake_Climate_Monthly.xlsx`. That is why it is committed rather
than generated.

---

## Reproducing the analysis

### 1. Environment

Python 3.13.9, managed with conda:

```bash
git clone https://github.com/SharpRS03/UoM-ERP-BM-10909914.git
cd UoM-ERP-BM-10909914
conda env create -f environment.yml
conda activate aglakes
```

`requirements.txt` carries equivalent pip pins if conda is unavailable. The neural network ran on a CPU-only
OpenBLAS build of PyTorch 2.10.0 on Apple Silicon — no CUDA, no Metal. Linear algebra backend and
thread count both affect floating-point summation order, so a different build will move those
results even with identical seeds. Stage 16 pins all BLAS thread counts to 1 for the same reason;
leave that pinning in place.

Exact versions, hardware: `docs/TECHNICAL_APPENDIX.pdf` §4.

### 2. Data

The raw altimetry and reanalysis inputs are public but are **not redistributed here**.
`docs/DATA.md` gives the source of each product, the exact ERA5 request, and the folder names the
notebooks expect.

Four derived products **are** committed, all inside `Code Outputs/`. A reproducer can regenerate
them from the raw downloads or start from the committed copies — the second route is recommended
for a first pass, because the altimetry archives are periodically reprocessed and the ERA5 daily
product is recomputed on every retrieval, so a download made today may not be byte-identical to
the one used here.

### 3. Run order

Run the notebooks in numerical order, in Jupyter or non-interactively:

```bash
for nb in [0-9][0-9]_*.ipynb; do
  jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

To skip the record construction and go straight to the modelling, start at `06_eda.ipynb` —
everything from there reads the committed products inside `Code Outputs/`.

Stage 20 must run after every forecasting stage and before the figures: it is the post-processor
that adds the nRMSE and MASE columns, and every scale-free number in the report comes from it. It
skips any metrics file it cannot find rather than failing, so an out-of-order run fails quietly.

Full stage table with inputs, parameters and runtimes: `docs/TECHNICAL_APPENDIX.pdf` §5.

### 4. Verifying the reproduction

Because the committed outputs sit in the working tree, git itself is the first check. After a run:

```bash
git status --short "Code Outputs"     # any file listed did not reproduce byte-for-byte
```

A few diagnostic figures and duplicate metrics files that no reported result uses are listed in
`.gitignore`, so a correct run reports a clean status rather than a list of untracked extras.

For a numeric comparison with a tolerance, clone a second, pristine copy and diff against it:

```bash
git clone https://github.com/SharpRS03/<REPO>.git reference
python verify_outputs.py reference/"Code Outputs" "Code Outputs"
```

---

## Seven things a reproducer needs to know before starting

**Three different graphs appear in this project, and the one the report describes is not the one
the models use.** The 19-edge robust core in `Code Outputs/CCM Outputs/CCM_12_robust_core.csv` is
the reported characterisation of the network, the degree structure, the in-degree-of-zero
result. The graph the forecasting stages actually read is the 20-edge top-3 adjacency in
`CCM_09_adjacency_top3_diff_train.csv`, and the neural network reads a third object again, the
residual-correlation matrix in `EDA Outputs/EDA_06_corr_residual.csv`, which stage 17 also
reads for one of its comparison graphs. Feeding the robust core to
GNARX will not reproduce the reported +8.4% or the 21st-percentile null result. Technical
appendix §6.5.

**The evaluation window is fixed and is not the full record.** All model results use 1995-06 to
2025-12 (367 months): 307 training months to 2020-12, then a 60-month test period. The exploratory
tables in the report are computed on the *full* record (370–403 months per lake, to 2026-03) and
are labelled as such. These are two different samples and mixing them will not reproduce either.

**Forecast skill is computed from RMSE rounded to four decimal places.** Skill against the
unrounded value differs in the second decimal. The reported figures use the rounded convention
throughout.

**The ERA5 product is daily, the analysis is monthly, and potential evaporation is signed.** The
reanalysis download is the post-processed daily statistics product, computed by the CDS at
retrieval time rather than served from an archive, so the request parameters in `docs/DATA.md`
matter as much as the DOI. A daily-to-monthly reduction then sits between the download and every
reported climate figure.

**The DMI lead lags are data-dependent, and the index is revised at source.** Stages 14 and 16
read their seven per-lake lead lags from `CLIM_06_delta_leadlag.csv`, which stage 08 computes
from `Climate Indices/dmi.csv`. NOAA recomputes the Dipole Mode Index whenever the sea-surface
temperature dataset behind it is revised, and re-downloading it during this work moved two of the
seven lags and every DMI-dependent number with them, while leaving every water-balance, network,
neural and null-control result bit-identical. `dmi.csv` is committed here with its access date;
work from the committed copy and the reported numbers reproduce exactly. Technical appendix §7.5.


**The neural point estimates come from stage 19, not stage 15.** Stage 15 produces a single run
on seed triple (0,1,2), which ranks first of ten. The figures the report carries are the
ten-replicate means from `FC10_seed_summary.csv`. A reproducer who runs stage 15 and compares it
against the reported skill table will find a mismatch that is not an error.

Full list of known deviations and non-determinism: technical appendix §7.

---

## Data availability

Altimetry: Copernicus Climate Change Service (C3S), USDA Global Reservoir and Lake Monitor
(G-REALM), and DAHITI (DGFI-TUM). Reanalysis: ERA5 via the Copernicus Climate Data Store. Climate
indices: NOAA PSL. Full citations, versions and access dates in `docs/DATA.md`.

## Licence

Code released under the MIT Licence (`LICENSE`). The derived products and the outputs in
`Code Outputs/` are released under CC BY 4.0. Redistribution of the underlying source
data is governed by each provider's own terms.

