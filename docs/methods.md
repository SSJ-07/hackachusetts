# methods.md — how each computed number is derived

Every number in Slot-to-Stop carries a source and a method. This file records the
estimation choices made in the data pipeline so reviewers can audit them.

## origins.parquet (pipeline/build_origins.py)

Sources:
- **ACS 2024 5-year** (U.S. Census API) — `data/raw/acs_bg.csv`
- **MassGIS Environmental Justice 2020** (ArcGIS REST) — `data/raw/ej_west.json`
- **TIGER 2024 block groups** (U.S. Census) — `data/raw/tiger_bg/`

Scope: Hampden (25013), Hampshire (25015), Franklin (25011) counties. 506 block groups.

### carless_adults — ESTIMATE
ACS `B25044` counts *households* with no vehicle, not adults. We estimate car-less
adults by scaling the adult population by the zero-vehicle household share:

```
adults_18plus   = B01003_001E (total pop) − under-18 bins (B01001 _003..006, _027..030)
zero_vehicle_hh = B25044_003E (owner, no vehicle) + B25044_010E (renter, no vehicle)
all_hh          = B25044_001E
carless_adults  = adults_18plus × (zero_vehicle_hh / all_hh)
```

This assumes car-less adults are distributed across households in proportion to the
zero-vehicle household rate. It is an approximation, labelled as such wherever shown.

### pop
`B01003_001E` (total population), rounded to int.

### age65_pct
Sum of 65+ age bins (`B01001` male _020..025, female _044..049) ÷ total population.
Range 0.0–1.0.

### lep_pct — limited-English-proficient household share
`C16002` limited-English-speaking household bins (_004 + _007 + _010 + _013) ÷ all
households (`C16002_001E`). Range 0.0–1.0.

> Note: the portal kit's EJ CSV has no GEOID, so it cannot be joined to block groups.
> Limited-English data therefore comes from ACS C16002, pulled directly from the Census.

### ej_flag
True if the block-group GEOID appears in the MassGIS EJ 2020 layer with `EJ = "Yes"`.
The layer lists EJ block groups only, so any GEOID absent from it is `False`.

### lat / lon — MVP substitute
TIGER interior point (`INTPTLAT` / `INTPTLON`), a point guaranteed to fall inside the
block-group polygon. This is an honest substitute for a true population-weighted
centroid, which would require areal interpolation against population rasters.
