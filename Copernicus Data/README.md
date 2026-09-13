# Copernicus Data

**This folder is intentionally empty in the repository.** The C3S altimetry and the ERA5
reanalysis are public but are not redistributed here. Download them yourself and build the
subfolder structure below, the loaders address these paths exactly.

```
Copernicus Data/
├── Water Level Satellite Data/
│   └── <Lake>_Data.nc                  7 files, C3S altimetry
├── 2m Temp Data/<YEAR>/
│   └── ERA5_2mTemp_<YEAR>.nc           one file per year, 1992-2025
└── Precip and Evap Data/<YEAR>/
    ├── ERA5_Precip_Evap_<YEAR>_H1.nc   January to June
    └── ERA5_Precip_Evap_<YEAR>_H2.nc   July to December
```

`<Lake>` is one of Albert, Edward, Kivu, Malawi, Tanganyika, Turkana, Victoria.

`04_era5_download.ipynb` creates the two ERA5 year folders as it downloads.
`Water Level Satellite Data/` has to be made by hand.

Sources, exact request parameters and access dates: `docs/DATA.md`. The ERA5 daily product is
computed by the CDS at retrieval time rather than served from an archive, so the request
parameters matter as much as the DOI, reproduce them field by field.
