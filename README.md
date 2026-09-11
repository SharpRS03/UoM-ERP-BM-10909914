# Dependence Without Predictability in Forecasting Seven African Great Lakes from Fused Satellite Altimetry

Code and supporting materials for an MSc Data Science extended research project
(University of Manchester, 2026).

The project builds a continuous, datum-consistent monthly water-level record for seven lakes of
the East African Rift from three satellite radar altimetry repositories, recovers a directed
dependence network between them using Convergent Cross Mapping (CCM), and tests whether that
network carries transferable forecasting information against calibrated null controls.

This repository is the reproducibility package for that report. It contains every notebook
and module needed to regenerate the reported results, a reference copy of the outputs behind
every figure and table the report cites, and nothing that does not serve that purpose.

---

## Layout

The repository root *is* the project directory. Notebooks read their inputs with paths relative
to it — `Grealm Data/…`, `Code Outputs/…`, `Climate Indices/…` — so they run from here, with the
imported modules beside them. They are deliberately not split into `src/` and `notebooks/`
subfolders: moving them would change their working directory and break every one of those
relative paths, not merely the two module imports. The numbering carries the run order.

```
00_collate_victoria_tanganyika.ipynb   …   22_study_area_map.ipynb
ccm_core.py            imported by stage 10
gnarx_core.py          imported by stage 16
forecast_gnarx.py      imported by stage 16

Grealm Data/           not redistributed — download here
Copernicus Data/       not redistributed — download here
Climate Indices/       committed: dmi.csv, nino34.csv

Code Outputs/          NOT committed. Every stage writes here; created on the first run
Reference Outputs/     committed supporting material — the authors' own results,
                       in the same subfolder layout as Code Outputs/

docs/                  technical appendix, pipeline schematic, data instructions
environment.yml        the conda environment as used
requirements.txt       equivalent pip pins
```

| Stages | What happens |
|---|---|
| `00`–`05` | Record construction — collation, bias-aligned fusion, gap interpolation, ERA5 download and per-lake climate extraction |
| `06`–`09` | Exploratory analysis — STL, stationarity, trends, PCA, and the climate stock-versus-flux contrast |
| `10` | Dependence — the CCM network, four preprocessing variants, 200 surrogates |
| `11`–`19` | Forecasting — univariate baselines, VAR/VARX, SARIMAX, the graph neural network, GNAR/GNARX, and both calibrated nulls |
| `20`, `21`, `22` | Reported output — scale-free metrics, the report figures, the study area map |

### Why there are two output folders

Every stage writes into `Code Outputs/`, which is not committed, a fresh clone does not have
it, and the notebooks create it on the first run. `Reference Outputs/` holds the authors' own
copies of the same files, under the same subfolder names, and nothing in the pipeline ever reads
it.

They are kept apart for one reason: a committed copy sitting at the path a stage writes to would
be overwritten by the first run and would be worth nothing as a comparison. Separating them means
you can run the whole pipeline and still have the original numbers to check against.

`Reference Outputs/` is **supporting material**. It contains the file
behind each numbered figure and table in the report, the file behind each reported quantity given
in the report's prose, and the four derived data products listed below — the set named in the
technical appendix's provenance map (§7), and no more. A full run writes considerably more than
this; none of the rest is committed, because material that does not support a reported result
makes the package harder to navigate.

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

`requirements.txt` carries equivalent pip pins if conda is unavailable, but `environment.yml` is
the specification the reported results were produced under. The neural network ran on a CPU-only
OpenBLAS build of PyTorch 2.10.0 on Apple Silicon — no CUDA, no Metal. Linear algebra backend and
thread count both affect floating-point summation order, so a different build will move those
results even with identical seeds. Stage 16 pins all BLAS thread counts to 1 for the same reason;
leave that pinning in place.

Exact versions and hardware: `docs/TECHNICAL_APPENDIX.pdf` §4.

### 2. Data

Only two folders need populating, and the raw inputs for both are public but **not redistributed
here**. `docs/DATA.md` gives the source of each product, the exact ERA5 request, the per-lake
target identifiers, and the folder and file names the notebooks expect.

Two small things are committed: the two climate index series under `Climate Indices/`, and,
inside the notebooks rather than in a data folder, the DAHITI water-level records. All five
DAHITI series are embedded as literal values in stages `00` and `01`, so there is no DAHITI
download, no DAHITI folder, and no account needed. The `<Lake>_DAHITI.xlsx` files are outputs
of stage `01`, not inputs to it.

### 3. Run order

Run the notebooks in numerical order, in Jupyter or non-interactively:

```bash
for nb in [0-9][0-9]_*.ipynb; do
  jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

To skip the record construction and start at `06_eda.ipynb`, copy the reference outputs across
first — stages `06` onward read from `Code Outputs/`, not from `Reference Outputs/`:

```bash
mkdir -p "Code Outputs" && cp -r "Reference Outputs/." "Code Outputs/"
```

The two files that matter for this are
`Gap Interpolation Outputs/Unified_Interpolated_Levels.xlsx` and
`Climate Data Extraction Outputs/Lake_Climate_Monthly.xlsx`; copying the whole set is simply
easier than picking them out.

Stage 20 must run after every forecasting stage and before the figures: it is the post-processor
that adds the nRMSE and MASE columns, and every scale-free number in the report comes from it. It
skips any metrics file it cannot find rather than failing, so an out-of-order run fails quietly.

Full stage table with inputs and parameters: `docs/TECHNICAL_APPENDIX.pdf` §5.

### 4. Checking a reproduction

Compare your `Code Outputs/` against the committed `Reference Outputs/`. The provenance map in
`docs/TECHNICAL_APPENDIX.pdf` §7 names the file behind every reported figure, table and quoted
number, so any result in the report can be traced to a single file and checked directly.

Three stages are expected to differ on different hardware — `15`, `18` and `19`, the neural
network and its two null suites. `docs/TECHNICAL_APPENDIX.pdf` §8.1 states what agreement to
expect from every stage, and §8 lists each place a difference is expected and why.

---

## Six things a reproducer needs to know before starting

**Three different graphs appear in this project, and the one the report describes is not the one
the models use.** The 19-edge robust core in `CCM Outputs/CCM_12_robust_core.csv` is the reported
*characterisation* of the network — the degree structure, the in-degree-of-zero result. The graph
the forecasting stages actually read is the 20-edge top-3 adjacency in
`CCM_09_adjacency_top3_diff_train.csv`, and the neural network reads a third object again, the
residual-correlation matrix in `EDA Outputs/EDA_06_corr_residual.csv`, which stage 17 also reads
for one of its comparison graphs. Feeding the robust core to GNARX will not reproduce the
reported +8.4% or the 21st-percentile null result. Technical appendix §6.5.

**The evaluation window is fixed and is not the full record.** All model results use 1995-06 to
2025-12 (367 months): 307 training months to 2020-12, then a 60-month test period. The exploratory
tables in the report are computed on the *full* record (370–403 months per lake, to 2026-03) and
are labelled as such. These are two different samples and mixing them will not reproduce either.

**Forecast skill is computed from RMSE rounded to four decimal places.** Skill against the
unrounded value differs in the second decimal. The reported figures use the rounded convention
throughout.

**The ERA5 product is daily, the analysis is monthly, and potential evaporation is signed.** The
reanalysis download is the post-processed *daily* statistics product, computed by the CDS at
retrieval time rather than served from an archive, so the request parameters in `docs/DATA.md`
matter as much as the DOI. A daily-to-monthly reduction then sits between the download and every
reported climate figure. Potential evaporation enters as a positive magnitude: leaving ERA5's
native negative sign in place gives Lake Turkana a water balance of roughly +2,386 mm/yr instead
of the reported −1,820 mm/yr, and inverts the strongest empirical finding in the report.

**The DMI lead lags are data-dependent, and the index is revised at source.** Stages 14 and 16
read their seven per-lake lead lags from `CLIM_06_delta_leadlag.csv`, which stage 08 computes
from `Climate Indices/dmi.csv`. NOAA recomputes the Dipole Mode Index whenever the sea-surface
temperature dataset behind it is revised, and re-downloading it during this work moved two of the
seven lags and every DMI-dependent number with them, while leaving every water-balance, network,
neural and null-control result bit-identical. `dmi.csv` is committed here with its access date;
work from the committed copy and the reported numbers reproduce exactly. Technical appendix §8.8.

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

Code released under the MIT Licence (`LICENSE`). The derived products and the reference outputs
are released under CC BY 4.0. Redistribution of the underlying source data is governed by each
provider's own terms.
