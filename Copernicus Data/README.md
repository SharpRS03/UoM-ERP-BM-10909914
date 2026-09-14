# Copernicus Data

**This folder is intentionally empty in the repository.** The C3S altimetry and the ERA5
reanalysis are public but are not redistributed here. Download them yourself and build the
subfolder structure below — the loaders address these paths exactly.

```
Copernicus Data/
├── Water Level Satellite Data/
│   └── <Lake>_Data.nc                  7 files, C3S altimetry
├── 2m Temp Data/<YEAR>/
│   └── ERA5_2mTemp_<YEAR>.nc           one file per year, 1992-2025
└── Precip and Evap Data/<YEAR>/
    ├── ERA5_Precip_Evap_<YEAR>_H1.nc   January to June
    └── ERA5_Precip_Evap_<YEAR>_H2.nc   July to December, 1992-2025
```

`<Lake>` is one of Albert, Edward, Kivu, Malawi, Tanganyika, Turkana, Victoria.
`Water Level Satellite Data/` has to be made by hand; `04_era5_download.ipynb` creates the two
ERA5 year folders as it downloads.

## The check

`Lake_Climate_Monthly.xlsx` should hold 2,800 rows — 400 months per lake, 1992-09 to 2025-12 —
with no nulls in `precip_mm`, `pet_mm` or `temp_C`. Check the columns as well as the row count:
the index is the union of the three variables, so a missing year shows up as an empty column
rather than as missing rows.

The CDS returns a ZIP archive with a `.nc` extension when several variables are requested
together. Stage 05 detects this and extracts it, so nothing needs unpacking by hand.

## Sources

Full sources, exact request parameters and access dates: `docs/DATA.md` and
`docs/TECHNICAL_APPENDIX.pdf` §3. The ERA5 daily product is computed by the CDS at retrieval time
rather than served from an archive, so the request parameters matter as much as the DOI —
reproduce them field by field from appendix Table T 4.
