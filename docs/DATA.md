# Data

The raw source data is not redistributed. This file tells you exactly what to download, from
where, and where to put it. Paths are relative to the repository root, which is the notebooks'
working directory.

Two things are committed, because they are small and let you start part-way through:

- `Climate Indices/` — the two climate index series (a few kilobytes each, public, unmodified).
- Four derived products — `African_Great_Lakes_Water_Levels.xlsx` at the root and three unified
  files inside `Code Outputs/`. See "Why the derived products are committed" below.

---

## 1. What to download

### 1.1 Satellite radar altimetry — lake water surface elevation

Three repositories are used. No single mission or repository covers all seven lakes for the
whole period, which is why the record is fused rather than taken from one source.

Lakes: **Victoria, Tanganyika, Malawi, Turkana, Albert, Edward, Kivu.**

| Repository | Provider | Identifier | Version | Accessed |
|---|---|---|---|---|
| C3S — Lake water levels from 1992 to present derived from satellite observations | Copernicus Climate Change Service | [doi:10.24381/cds.5714c668](https://doi.org/10.24381/cds.5714c668) | v5.0 | 26 Feb 2026 |
| G-REALM — Global Reservoir and Lake Monitor | USDA Foreign Agricultural Service / NASA | <https://ipad.fas.usda.gov/cropexplorer/global_reservoir/> | per-lake target IDs below | 27 Feb 2026 |
| DAHITI — Database for Hydrological Time Series of Inland Waters | DGFI, Technical University of Munich | <https://dahiti.dgfi.tum.de/en/products/water-level-altimetry/> | software v8.0 | 29 Feb 2026 |

The C3S backbone draws on TOPEX/Poseidon, Jason-1/2/3, ENVISAT, Sentinel-3A and Sentinel-6.

**Per-lake target identifiers:**

| Lake | G-REALM ID | Cadence | DAHITI ID | Missions in the DAHITI record |
|---|---|---|---|---|
| Victoria | 000314 | 10-day | 2 | TOPEX, Poseidon, Jason-1/2/3, Sentinel-6A |
| Tanganyika | 000315 | 10-day | 25 | TOPEX, Poseidon, Jason-1/2/3, Sentinel-6A |
| Malawi | 000317 | 10-day | — | — |
| Turkana | 000093 | 10-day | — | — |
| Albert | 000405 | monthly | 85 | ICESat-2 (ATL13 v7, beams 1L–3R), Jason-1 (SGDR-E), SARAL (SGDR-F), Sentinel-3A/3B (NTC), TOPEX/Poseidon (Side-B, GDR-F) |
| Edward | 000004 | monthly | 86 | Sentinel-3A, SARAL, Envisat v3 |
| Kivu | 000069 | monthly | 87 | Sentinel-3A, SARAL, Envisat v3 |

> **Malawi and Turkana have no DAHITI record.** Those two series are a two-source fusion of
> C3S and G-REALM.

**Citing DAHITI.** DAHITI asks to be cited by its methodology paper: Schwatke, C.,
Dettmering, D., Bosch, W. and Seitz, F. (2015) DAHITI — an innovative approach for estimating
water level time series over inland waters using multi-mission satellite altimetry.
*Hydrology and Earth System Sciences*, 19, pp. 4345–4364.
[doi:10.5194/hess-19-4345-2015](https://doi.org/10.5194/hess-19-4345-2015)

### 1.2 ERA5 reanalysis — climate covariates

**Dataset:** ERA5 post-processed daily statistics on single levels from 1940 to present
· CDS ID `derived-era5-single-levels-daily-statistics`
· [doi:10.24381/cds.4991cf48](https://doi.org/10.24381/cds.4991cf48) · v1.0 · accessed 19 March 2026.

Request specification:

| Field | Value |
|---|---|
| `product_type` | `reanalysis` |
| `variable` | `total_precipitation`, `potential_evaporation`, `2m_temperature` |
| `year` | 1992–2026 |
| `month` | all |
| `day` | all |
| `daily_statistic` | `daily_mean` for `2m_temperature`; `daily_sum` for `total_precipitation` and `potential_evaporation` |
| `time_zone` | `utc+00:00` |
| `frequency` | `1_hourly` |
| `area` (N/W/S/E) | `6, 27, -15, 38` |
| `data_format` | `netcdf` |

> **This product is computed at retrieval time, not served from an archive.** The CDS
> documentation states that the daily aggregation "is calculated during the retrieval process
> and is not part of a permanently archived dataset". The request fields above therefore
> define the data far more tightly than the DOI alone does.

This is a **single regional download box**. Per-lake series are produced afterwards by
cropping to per-lake bounding boxes inside it and averaging over the box:

| Lake | South | North | West | East |
|---|---|---|---|---|
| Victoria | −3.10 | 0.60 | 31.50 | 34.90 |
| Tanganyika | −8.90 | −3.30 | 29.00 | 31.20 |
| Malawi | −14.60 | −9.40 | 33.90 | 35.30 |
| Turkana | 2.40 | 4.70 | 35.80 | 36.80 |
| Albert | 1.00 | 2.40 | 30.30 | 31.50 |
| Edward | −0.70 | −0.05 | 29.20 | 30.00 |
| Kivu | −2.60 | −1.50 | 28.80 | 29.50 |

> **These are bounding boxes, not hydrological catchments.** This is a key distinction.
> Lake Turkana's box reaches 4.70°N, so the download extent's 6°N boundary sits only 1.3°
> above it, while the Omo headwaters, which supply over 80% of Turkana's inflow, lie north of
> 6°N and outside the domain entirely. 

**Daily to monthly.** The downloaded product is daily and every analysis is monthly. The
reduction, performed in stage 05: mask to the lake's bounding box and take
an unweighted mean over the cells inside it; then resample to month start, taking the **mean**
for temperature and the **sum** for precipitation and potential evaporation. Spatial first, then
temporal. Kelvin to °C, metres to millimetres.

Potential evaporation enters as a **positive magnitude**, ERA5 reports it negative under the
downward-positive convention and the extraction negates it. The check: Turkana should come out
at 283 mm precipitation against 2,103 mm potential evaporation, water balance −1,820 mm.

**Retrieval history.** `04_era5_download.ipynb` covers temperature from 2015 and precipitation
and evaporation from 2021; earlier years were requested through the CDS web interface against
the same dataset, area and variables. Use the programmatic request for the whole 1992–2026
period rather than mixing routes.

**Copernicus attribution** (applies to both C3S products): cite the CDS catalogue entry and
give clear, visible attribution to the Copernicus programme for each product used. Neither
the European Commission nor ECMWF is responsible for any use made of the information.

### 1.3 Climate indices

Committed under `Climate Indices/`, unmodified, with their source noted here so you can refresh them:

| File | Index | Source |
|---|---|---|
| `Climate Indices/dmi.csv` | Dipole Mode Index | NOAA PSL, <https://psl.noaa.gov/data/timeseries/month/DMI/> — calculated at PSL from HadISST 1.1 |
| `Climate Indices/nino34.csv` | Niño 3.4 | NOAA PSL, <https://psl.noaa.gov/data/timeseries/month/Nino34_CPC/> — derived from NOAA ERSST v5 |

Both are used. DMI is the index carried into the models; Niño 3.4 is retained because the
choice between them is made empirically and the comparison is reported.

Cite the DMI to Saji, N.H. and Yamagata, T. (2003) Possible impacts of Indian Ocean Dipole mode
events on global climate. *Climate Research*, 25(2), pp. 151–169. The Niño 3.4 series carries no
suggested citation of its own.

---

## 2. Where to put it

The notebooks read these paths relative to the repository root. Filenames are exact, the
loaders build them by string substitution on the lake name.

```
<repo-root>/
├── Grealm Data/
│   └── <Lake> Water Level.txt              7 files: Albert, Edward, Kivu, Malawi,
│                                           Tanganyika, Turkana, Victoria
├── Copernicus Data/
│   ├── Water Level Satellite Data/
│   │   └── <Lake>_Data.nc                  7 files, C3S altimetry
│   ├── 2m Temp Data/<YEAR>/
│   │   └── ERA5_2mTemp_<YEAR>.nc           one file per year, 1992-2025
│   └── Precip and Evap Data/<YEAR>/
│       ├── ERA5_Precip_Evap_<YEAR>_H1.nc   January to June
│       └── ERA5_Precip_Evap_<YEAR>_H2.nc   July to December
├── Albert_DAHITI.xlsx
├── Edward_DAHITI.xlsx
└── Kivu_DAHITI.xlsx
├── Climate Indices/                        committed — dmi.csv, nino34.csv
└── Code Outputs/                           committed — reference outputs, by stage
```

> **There are three DAHITI spreadsheets, not five.** Victoria's and Tanganyika's DAHITI records
> are embedded directly in notebook `00_collate_victoria_tanganyika.ipynb` as literal text
> rather than read from a file, so those two series need no download and reproduce exactly.
> Malawi and Turkana have no DAHITI record at all. Nothing is missing.

---

## 3. Why the derived products are committed

Satellite altimetry repositories reprocess their archives, and the ERA5 daily product is
recomputed on every retrieval. A download made today will not necessarily be byte-identical to
the one used here, and a reproducer who cannot match the fused series has no way to tell
whether the difference came from the data or from their own run of the code.

Committing the four derived products removes that ambiguity:

| File | Committed location | Produced by | Lets you start at |
|---|---|---|---|
| `African_Great_Lakes_Water_Levels.xlsx` | repository root | stages 00–01 | fusion |
| `Unified_BiasAligned_Levels.xlsx` | `Code Outputs/Fusion Outputs/` | stage 02 | gap interpolation |
| `Unified_Interpolated_Levels.xlsx` | `Code Outputs/Gap Interpolation Outputs/` | stage 03 | all EDA and modelling |
| `Lake_Climate_Monthly.xlsx` | `Code Outputs/Climate Data Extraction Outputs/` | stage 05 | climate EDA and exogenous models |

`Unified_Interpolated_Levels.xlsx` is the file every modelling stage actually reads. If your
interest is the forecasting results rather than the record construction, start at stage 06 and
skip stages 00 to 05 entirely.

All four regenerate from the raw downloads. The last two are not purely supporting material:
stages 06 onward read them from inside `Code Outputs/`, which is why that folder is committed.

---

## 4. Coverage and interpolation, for reference

Interior gaps are filled by time-weighted interpolation, strictly inside the observed range,
with every filled month flagged. `MAX_GAP` is `None`: there is no cap on run length, so every
internal gap is filled however long it is. Coverage is uneven and the pattern matters to the
results:

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
