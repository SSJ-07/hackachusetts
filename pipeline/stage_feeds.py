"""Stage the GTFS feeds into data/cache/ for the router (spec: multi-feed, task 7b).

Run from the repo root:   python pipeline/stage_feeds.py

  data/raw/pvta_gtfs.zip        -> data/cache/pvta/   (from scripts/get_data.py)
  data/manual/frta_minigtfs/    -> data/cache/frta/   (committed source of truth)

Idempotent: a feed is re-staged only when its source changed (sha256 of the inputs,
kept in data/cache/<feed>/.staged_from). `make data` should call this after
get_data.py so FRTA is picked up automatically.
"""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
PVTA_ZIP = ROOT / "data" / "raw" / "pvta_gtfs.zip"
FRTA_SRC = ROOT / "data" / "manual" / "frta_minigtfs"
GTFS_SUFFIX = ".txt"  # only GTFS tables are staged (README etc. stay in data/manual)


def _sha_files(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def _up_to_date(dest: Path, digest: str) -> bool:
    stamp = dest / ".staged_from"
    return stamp.is_file() and stamp.read_text(encoding="utf-8").strip() == digest


def _replace_dir(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)


def stage_pvta() -> str:
    if not PVTA_ZIP.is_file():
        return f"[skip] {PVTA_ZIP.relative_to(ROOT)} missing (run scripts/get_data.py)"
    dest = CACHE / "pvta"
    digest = _sha_files([PVTA_ZIP])
    if _up_to_date(dest, digest):
        return "[skip] data/cache/pvta up to date"
    _replace_dir(dest)
    with zipfile.ZipFile(PVTA_ZIP) as z:
        for name in z.namelist():
            # flat GTFS tables only; refuse paths that could escape dest
            if "/" in name or "\\" in name or ".." in name or not name.endswith(GTFS_SUFFIX):
                continue
            (dest / name).write_bytes(z.read(name))
    (dest / ".staged_from").write_text(digest, encoding="utf-8")
    return f"[ ok ] data/cache/pvta: {len(list(dest.glob('*.txt')))} tables"


def stage_frta() -> str:
    tables = sorted(FRTA_SRC.glob(f"*{GTFS_SUFFIX}"))
    if not tables:
        return f"[skip] no FRTA tables in {FRTA_SRC.relative_to(ROOT)}"
    dest = CACHE / "frta"
    digest = _sha_files(tables)
    if _up_to_date(dest, digest):
        return "[skip] data/cache/frta up to date"
    _replace_dir(dest)
    for t in tables:
        shutil.copy2(t, dest / t.name)
    (dest / ".staged_from").write_text(digest, encoding="utf-8")
    return f"[ ok ] data/cache/frta: {len(tables)} tables"


def main() -> None:
    print(stage_pvta())
    print(stage_frta())


if __name__ == "__main__":
    main()
