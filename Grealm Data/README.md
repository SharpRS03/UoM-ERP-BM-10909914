# Grealm Data

**This folder is intentionally empty in the repository.** The G-REALM water-level records are
public but are not redistributed here; download them yourself and place them in this folder.

Seven files are expected, named exactly as below. The loaders build these names by string
substitution on the lake name, so a differently named file is reported as not found and that
lake's G-REALM source is silently dropped from the fusion rather than raising an error:

```
Albert Water Level.txt
Edward Water Level.txt
Kivu Water Level.txt
Malawi Water Level.txt
Tanganyika Water Level.txt
Turkana Water Level.txt
Victoria Water Level.txt
```

Source: USDA Foreign Agricultural Service / NASA GSFC, Global Reservoir and Lake Monitor,
<https://earth.gsfc.nasa.gov/gwm/lake/Index>. The per-lake target identifiers and the access date
used for the reported results are in `docs/DATA.md`; the identifiers, cadences and contributing
missions are also tabulated in `docs/TECHNICAL_APPENDIX.pdf` §3.2.
