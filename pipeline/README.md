# pipeline/

Offline data-prep steps that build the cached Parquet files.

- `build_origins.py` — join ACS (B25044, B01003, B01001, C16002) to TIGER block groups;
  compute car-less adults; add EJ flags + limited-English %. → `data/cache/origins.parquet`
- `stops_walk.py` — nearest PVTA stops within 800 m per origin; walk minutes. → `data/cache/stops_walk.parquet`

Owner: M2.
