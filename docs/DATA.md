# Data — what to download and where to put it

The raw source data is not redistributed. This file tells you exactly what to download, what to
call it, where it goes, and how to tell it worked. Provenance, versions, the full ERA5 request
table and the daily-to-monthly reduction are in `docs/TECHNICAL_APPENDIX.pdf` §3; this file is the
operational half and does not repeat them.

Paths are relative to the repository root, which is the notebooks' working directory.

Two things are committed because they are small and public: the two climate index series in
`Climate Indices/`, and the DAHITI water-level records — which are embedded as literal text inside
notebooks `00` and `01` rather than read from a file, so there is no DAHITI download, no DAHITI
folder and no DAHITI account. A third thing is committed for a different reason: `Reference
Outputs/`, the author's own copies of the reported results, which also let you start part-way
through. See §4.

---

## 1. What to download

Seven lakes: **Victoria, Tanganyika, Malawi, Turkana, Albert, Edward, Kivu.**

### 1.1 Satellite radar altimetry

Two repositories to download; the third is already embedded. No single mission or repository
covers all seven lakes for the whole period, which is why the record is fused rather than taken
from one source.

| Repository | Provider | Where | Accessed |
|---|---|---|---|
| C3S — Lake water levels from 1992 to present derived from satellite observations | Copernicus Climate Change Service | [doi:10.24381/cds.5714c668](https://doi.org/10.24381/cds.5714c668), v5.0 | 26 Feb 2026 |
| G-REALM — Global Reservoir and Lake Monitor | USDA Foreign Agricultural Service / NASA GSFC | <https://earth.gsfc.nasa.gov/gwm/lake/Index> | 27 Feb 2026 |
| DAHITI | DGFI, Technical University of Munich | <https://dahiti.dgfi.tum.de/en/>, software v8.0 | **already embedded — nothing to download** |

Per-lake target identifiers and the missions behind each record: appendix Table T 2.
Malawi and Turkana have no DAHITI record; those two series are a two-source fusion of C3S and
G-REALM.

DAHITI asks to be cited by Schwatke, C., Dettmering, D., Bosch, W. and Seitz, F. (2015) DAHITI — an
innovative approach for estimating water level time series over inland waters using multi-mission
satellite altimetry. *Hydrology and Earth System Sciences*, 19, pp. 4345–4364.
[doi:10.5194/hess-19-4345-2015](https://doi.org/10.5194/hess-19-4345-2015)

### 1.2 ERA5 reanalysis

**ERA5 post-processed daily statistics on single levels from 1940 to present**, CDS ID
`derived-era5-single-levels-daily-statistics`,
[doi:10.24381/cds.4991cf48](https://doi.org/10.24381/cds.4991cf48), v1.0, accessed 19 March 2026.

**Reproduce the request field by field from appendix Table T 4.** This product is computed by the
CDS at retrieval time rather than served from an archive, so the DOI alone does not identify the
data — the daily statistic, the sampling frequency, the time zone and the area all change what you
receive. It is a single regional download box (N 6, W 27, S −15, E 38); per-lake series are
produced afterwards by cropping to the bounding boxes of appendix Table T 5 and averaging over the
cells inside each box.

**Stage `04` needs the CDS API client and your own credentials.** It does `import cdsapi` and
builds a `cdsapi.Client()`, which reads `~/.cdsapirc` in your home directory. That file holds your
Copernicus Climate Data Store API URL and key, and the stage raises immediately without it:

```
url: https://cds.climate.copernicus.eu/api
key: <your CDS API key>
```

Register at <https://cds.climate.copernicus.eu>, accept the licence for the ERA5 daily-statistics
dataset, and copy the credentials from your account page. Nothing else in the pipeline needs an
account or a key.

**Stage `04` does not cover the whole period.** It requests temperature for 2015–2026 and
precipitation and potential evaporation for 2021–2026. Everything earlier was requested through the
CDS web interface against the same dataset, area and variables, and stage `05` reads 1992–2025, so
the 2026 downloads are never used. The years you must fetch by hand are therefore **1992–2014 for
temperature and 1992–2020 for precipitation and potential evaporation** — use the request in
appendix Table T 4 for those too, rather than mixing request routes.

The download is daily and every analysis is monthly. Stage `05` does the reduction — spatial
first with an unweighted mean over the cells in the box, then temporal, taking the monthly mean
for temperature and the monthly sum for precipitation and potential evaporation, with Kelvin
converted to °C and metres to millimetres, and potential evaporation negated so it enters as a
positive magnitude. The full specification is appendix §3.4; the checks are in §3 below.

**Copernicus attribution**, for both C3S products: cite the CDS catalogue entry and give clear,
visible attribution to the Copernicus programme. Neither the European Commission nor ECMWF is
responsible for any use made of the information.

### 1.3 Climate indices — committed, do not refresh

| File | Index | Source | Accessed |
|---|---|---|---|
| `Climate Indices/dmi.csv` | Dipole Mode Index | NOAA PSL, <https://psl.noaa.gov/data/timeseries/month/DMI/> — calculated at PSL from HadISST 1.1 | 6 August 2026 |
| `Climate Indices/nino34.csv` | Niño 3.4 | NOAA PSL, <https://psl.noaa.gov/data/timeseries/month/Nino34_CPC/> — derived from NOAA ERSST v5 | 20 June 2026 |

**Work from the committed files.** NOAA recomputes the Dipole Mode Index whenever the sea-surface
temperature dataset behind it is revised, and the seven per-lake DMI lead lags are read from it at
run time by stages 14 and 16. Re-downloading it during this work moved two of the seven lags and
every DMI-dependent number with them. The committed vintage is part of the specification;
appendix §8.5.

Both indices are used: DMI is carried into the models, Niño 3.4 is retained because the choice
between them is made empirically and the comparison is reported.

Cite the DMI to Saji, N.H. and Yamagata, T. (2003) Possible impacts of Indian Ocean Dipole mode
events on global climate. *Climate Research*, 25(2), pp. 151–169. The Niño 3.4 series carries no
suggested citation of its own.

---

## 2. Where to put it

**Filenames are exact.** The loaders build them by string substitution on the lake name and on the
year, so `Lake Albert.txt` in place of `Albert Water Level.txt` fails with no useful diagnosis, and
a year folder whose file is named differently is skipped with a one-line `[skip]` message rather
than an error.

```
<repo-root>/
├── Grealm Data/
│   └── <Lake> Water Level.txt              7 files: Albert, Edward, Kivu, Malawi,
│                                           Tanganyika, Turkana, Victoria
├── Copernicus Data/
│   ├── Water Level Satellite Data/
│   │   └── <Lake>_Data.nc                  7 files, C3S altimetry — make this folder by hand
│   ├── 2m Temp Data/<YEAR>/
│   │   └── ERA5_2mTemp_<YEAR>.nc           one file per year, 1992–2025
│   └── Precip and Evap Data/<YEAR>/
│       ├── ERA5_Precip_Evap_<YEAR>_H1.nc   January to June
│       └── ERA5_Precip_Evap_<YEAR>_H2.nc   July to December
├── Climate Indices/                        committed — dmi.csv, nino34.csv
└── Reference Outputs/                      committed — see §4
```

Stage `04` creates the two ERA5 year folders as it downloads. `Water Level Satellite Data/` has to
be made by hand.


**Two years do not follow the half-year pattern**, because both predate stage `04`'s 2021 start
and were fetched by hand. Stage `05` handles both:

- **1992** has no `_H1`/`_H2` pair. Precipitation and potential evaporation are two separate
  single-variable files, `ERA5_Precip_1992.nc` and `ERA5_Evap_1992.nc`, in
  `Precip and Evap Data/1992/`. The loader falls back to this pattern only when no combined file
  is present.
- **2020** holds a single combined file under one of the two half-year names rather than a pair.
  Whichever name it carries, it must cover the whole year — stage `05` reads whatever is there
  without checking the span, so confirm 2020 has twelve months of `precip_mm` and `pet_mm` in the
  output before going further.

The 1992 temperature file covers September to December only, which is why the monthly climate
record begins at 1992-09 rather than 1992-01.

The CDS sometimes returns a ZIP archive with a `.nc` extension when several variables are
requested together. Stage `05` detects this and extracts it, so you do not need to unpack anything
by hand.

Nothing goes in a DAHITI folder — there isn't one, and there is nothing to put in it. The
`<Lake>_DAHITI.xlsx` files you will see appear are written by stage `01` into
`Code Outputs/Lake Level Outputs/` and read back by the same stage; they are outputs, not inputs.

`Code Outputs/` is not in the repository. Every stage writes into it and the notebooks create it
on the first run.

---

## 3. Checks that tell you the download worked

| After stage | Check |
|---|---|
| `01` | `Code Outputs/Lake Level Outputs/African_Great_Lakes_Water_Levels.xlsx` holds all seven lakes |
| `03` | Coverage matches the table in §5 below, lake for lake |
| `05` | `Lake_Climate_Monthly.xlsx` is 2,800 rows: 400 months per lake, 1992-09 to 2025-12, with no nulls in `precip_mm`, `pet_mm` or `temp_C`. Precipitation and potential evaporation are read from half-year files and temperature from one file per year, and a missing or misnamed file is skipped rather than flagged, so check the columns as well as the row count |
| `05` | Turkana comes out at 283 mm precipitation against 2,103 mm potential evaporation — a water balance of **−1,820 mm/yr**, the only negative value of the seven. If you get roughly **+2,386 mm/yr**, ERA5's native negative sign for potential evaporation has not been negated, and the strongest empirical finding in the report is inverted |

---

## 4. Why `Reference Outputs/` is committed

Altimetry repositories reprocess their archives and the ERA5 daily product is recomputed on every
retrieval, so a download made today may not be byte-identical to the one used here — and a
reproducer who cannot match the fused series has no way to tell whether the difference came from
the data or from their own run.

`Reference Outputs/` removes that ambiguity. Four of its files are the derived data products,
which are also the entry points for a partial reproduction:

| File | Reference copy | Produced by | Lets you start at |
|---|---|---|---|
| `African_Great_Lakes_Water_Levels.xlsx` | `Reference Outputs/Lake Level Outputs/` | stages 00–01 | fusion |
| `Unified_BiasAligned_Levels.xlsx` | `Reference Outputs/Fusion Outputs/` | stage 02 | gap interpolation |
| `Unified_Interpolated_Levels.xlsx` | `Reference Outputs/Gap Interpolation Outputs/` | stage 03 | all EDA and modelling |
| `Lake_Climate_Monthly.xlsx` | `Reference Outputs/Climate Data Extraction Outputs/` | stage 05 | climate EDA and exogenous models |

Nothing in the pipeline reads `Reference Outputs/`. Stages 06 onward read from `Code Outputs/`, so
to start part-way through, copy the reference set across first:

```bash
mkdir -p "Code Outputs" && cp -r "Reference Outputs/." "Code Outputs/"
```

Copy the whole set rather than picking files out — stage 15 falls back silently to a different
adjacency if `EDA Outputs/EDA_06_corr_residual.csv` is missing. The full contents of
`Reference Outputs/` and the report float each file backs are in appendix §7.

---

## 5. Coverage after interpolation, for reference

Interior gaps are filled by time-weighted interpolation, strictly inside the observed range, with
every filled month flagged. `MAX_GAP` is `None`: there is no cap on run length, so every internal
gap is filled however long it is.

| Lake | Months | Observed | Interpolated | % | Longest run |
|---|---|---|---|---|---|
| Kivu | 371 | 317 | 54 | 14.6 | 4 |
| Edward | 371 | 330 | 41 | 11.1 | 6 |
| Albert | 370 | 355 | 15 | 4.1 | 1 |
| Turkana | 402 | 401 | 1 | 0.2 | 1 |
| Malawi | 403 | 403 | 0 | 0.0 | — |
| Tanganyika | 401 | 401 | 0 | 0.0 | — |
| Victoria | 402 | 402 | 0 | 0.0 | — |

If your regenerated fusion does not reproduce these counts, the difference is in the raw
downloads, not in the code.
