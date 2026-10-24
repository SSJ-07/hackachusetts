# scripts/

- `get_data.py` — idempotent downloader for the datasets in plan.md §2a. Writes
  `data/raw/manifest.json` (URL, date, sha256) and validates row counts + columns.

Owner: M2.
