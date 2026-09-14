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
relative paths, not merely the module imports. The numbering carries the run order.

```
00_collate_victoria_tanganyika.ipynb   …   22_study_area_map.ipynb   23 notebooks
ccm_core.py            imported by stage 10
gnarx_core.py          imported by stages 16 and 17
forecast_gnarx.py      imported by stage 17

Grealm Data/           not redistributed — download here
Copernicus Data/       not redistributed — download here
Climate Indices/       committed: dmi.csv, nino34.csv

Code Outputs/          NOT committed. Every stage writes here; created on the first run
Reference Outputs/     committed supporting material — the author's own results,
                       in the same subfolder layout as Code Outputs/

docs/                  technical appendix, data instructions
environment.yml        the conda environment as used
requirements.txt       equivalent pip pins
```

| Stages | What happens |
|---|---|
| `00`–`05` | Record construction — collation, bias-aligned fusion, gap interpolation, ERA5 download and per-lake climate extraction |
| `06`–`09` | Exploratory analysis — STL, stationarity, trends, PCA, and the climate stock-versus-flux contrast |
| `10` | Dependence — the CCM network, four preprocessing variants, 200 surrogates per edge and a 200-trial AR(1) negative control |
| `11`–`19` | Forecasting — univariate baselines, VAR/VARX, SARIMAX, the graph neural network, GNAR/GNARX, both calibrated nulls, and the neural seed-variance replication |
| `20`, `21`, `22` | Reported output — scale-free metrics, the report figures, the study area map |

### Why there are two output folders

Every stage writes into `Code Outputs/`, which is not committed, a fresh clone does not have
it, and the notebooks create it on the first run. `Reference Outputs/` holds the author's own
copies of the same files, under the same subfolder names, and nothing in the pipeline ever reads
it.

They are kept apart for one reason: a committed copy sitting at the path a stage writes to would
be overwritten by the first run and would be worth nothing as a comparison. Separating them means
you can run the whole pipeline and still have the original numbers to check against.

`Reference Outputs/` is **supporting material**, and it holds three things. The file behind each
numbered figure and table in the report, the set named in the technical appendix's provenance map (§7). The four derived data
products, which are also the entry points for a partial reproduction. And the handful of
intermediate files that a later stage reads as an *input* rather than a reader reads as a result:
the CCM adjacency matrices, the residual-correlation matrix, the DMI lead-lag table, the shared
baseline predictions and the selected ARIMA orders. That last group is what makes "start at stage
06" and "start at stage 11" work.

A full run writes considerably more than this; none of the rest is committed, because material
that does not support a reported result makes the package harder to navigate.

---

## Reproducing the analysis

### 1. Environment

Python 3.13.9, managed with conda:

```bash
git clone https://github.com/SharpRS03/UoM-ERP-BM-10909914.git
cd UoM-ERP-BM-10909914
conda env create -f environment.yml
conda activate aglakes
jupyter lab            # start from the repository root, not from a subfolder
```

`requirements.txt` carries equivalent pip pins if conda is unavailable, but `environment.yml` is
the specification the reported results were produced under. The neural network ran on a CPU-only
OpenBLAS build of PyTorch 2.10.0 on Apple Silicon — no CUDA, no Metal. Linear algebra backend and
thread count both affect floating-point summation order, so a different build will move those
results even with identical seeds.

Thread pinning is not uniform and that is deliberate: stages `10`–`14`, `16` and `17` set all four
BLAS thread-count variables to 1 before importing NumPy, and `forecast_gnarx.py` does the same.
The three neural stages — `15`, `18` and `19` — do not, which is one reason they are the least
portable stages in the pipeline. Leave the pinning that is there in place.

Two environment variables affect the run and both should be left unset:

- **`AGL_ROOT`** — stages `09`, `10`, `11`, `14`, `16`, `17`, `18`, `19`, `20` and `21` read it as an
  optional project root and fall back to the working directory. The other thirteen stages use plain
  relative paths. Set it, and part of the run reads one tree while the rest reads another, with no
  error.
- **`GNN_SMOKE`, `N_NULL`, `N_REP`** — smoke-test and trial-count overrides in stages `18` and `19`.
  Smoke mode writes its outputs under a `_SMOKE` suffix, so it cannot silently corrupt a real run,
  but the real files will simply not be produced.

Stage `22` needs `cartopy` and downloads Natural Earth shapefiles the first time it runs, so it
needs a network connection. Nothing else in the pipeline does.

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

Copy the whole set rather than picking files out. The two that matter most are
`Gap Interpolation Outputs/Unified_Interpolated_Levels.xlsx` and
`Climate Data Extraction Outputs/Lake_Climate_Monthly.xlsx`.

Three ordering constraints are worth knowing before you start:

- **Stage `11` is a hard dependency of `12`, `13`, `14`, `16` and `17`.** It writes
  `Baseline Outputs/Baseline_predictions.csv`, from which every later stage loads the 3,108
  RandomWalk and SARIMA forecasts that all skill percentages are measured against, and never
  re-fits them. It also writes compatibility copies at
  `Arima Forecast Outputs/FC_orders.csv` and `FC_metrics.csv`, which stages `12`, `13`, `14` and
  `20` read by that path.
- **Stage `17` re-runs stage `16` in full.** Its first statement is `import forecast_gnarx`, and
  that module executes the whole GNARX pipeline at import time, rewriting `FC7_gnarx_metrics.csv`,
  `FC7_gnarx_coeffs.csv` and `FC7_gnarx_orders.csv` before the sensitivity analysis begins. This is
  intentional, it is what guarantees the null control cannot drift from the primary result, and
  the notebook asserts that the primary graph reproduces FC7 exactly, but it roughly doubles the
  stage's runtime and means stage `17` cannot be run against a stale FC7.
- **Stage `20` must run after every forecasting stage and before the figures.** It is the
  post-processor that adds the nRMSE and MASE columns, and every scale-free number in the report
  comes from it. It skips any metrics file it cannot find rather than failing, so an out-of-order
  run fails quietly.

Full stage table: `docs/TECHNICAL_APPENDIX.pdf` §5. Every fixed parameter: §6.

---

## Five things a reproducer needs to know before starting

**Three different graphs appear in this project, and the one the report describes is not the one
the models use.** The 19-edge robust core in `CCM Outputs/CCM_12_robust_core.csv` is the reported
*characterisation* of the network — the degree structure, the in-degree-of-zero result. The graph
the forecasting stages actually read is the 20-edge top-3 adjacency in
`CCM_09_adjacency_top3_diff_train.csv`, and the neural network reads a third object again, the
residual-correlation matrix in `EDA Outputs/EDA_06_corr_residual.csv`, which stages 17, 18 and 19
also read for their comparison graphs. Feeding the robust core to GNARX will not reproduce the
reported +8.4% or the 21st-percentile null result. Technical appendix §6.4.

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
temperature dataset behind it is revised, and re-downloading could affect the results. 
`dmi.csv` is committed here with its access date;
work from the committed copy and the reported numbers reproduce exactly. Technical appendix §8.5.


Full list of known deviations and non-determinism: technical appendix §8.

---

## Data availability

Altimetry: Copernicus Climate Change Service (C3S), USDA Global Reservoir and Lake Monitor
(G-REALM), and DAHITI (DGFI-TUM). Reanalysis: ERA5 via the Copernicus Climate Data Store. Climate
indices: NOAA PSL. Full citations, versions and access dates in `docs/DATA.md`.

## Licence

Code released under the MIT Licence (`LICENSE.txt`). The derived products and the reference outputs
are released under CC BY 4.0. Redistribution of the underlying source data is governed by each
provider's own terms.
