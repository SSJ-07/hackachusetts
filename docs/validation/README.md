# GTFS validation reports

Validator: MobilityData `gtfs-validator` **v8.0.1** CLI
(jar sha256 `19293DDD9B6F954F216D4F12054BD8A3232921751C4484339E339764A91000E2`),
country code `us`. Run 2026-10-24. Reports: `pvta/report.json`, `frta/report.json`
(`system_errors.json` is empty for both). The HTML view is not committed; regenerate with:

```
java -jar data/raw/gtfs-validator-8.0.1-cli.jar -i data/raw/pvta_gtfs.zip -o docs/validation/pvta -c us
java -jar data/raw/gtfs-validator-8.0.1-cli.jar -i <zip of data/manual/frta_minigtfs/*.txt> -o docs/validation/frta -c us
```

| Feed | Input | Errors | Warnings |
|---|---|---|---|
| PVTA | `data/raw/pvta_gtfs.zip` (sha256 `08B62BBC…A064`) | 522 | 11,046 |
| FRTA | `data/manual/frta_minigtfs/` (Trillium, MobilityDatabase mdb-429) | 0 | 14 |

## Triage

We never edit a published feed. Each notice is either harmless to routing or documented.

| Feed | Notice | Count | Affects routing? | Decision |
|---|---|---|---|---|
| PVTA | `trip_distance_exceeds_shape_distance` (ERROR) | 300 | No — the engine never reads `shapes.txt` or `shape_dist_traveled` | documented |
| PVTA | `equal_shape_distance_diff_coordinates` (ERROR) | 222 | No — shapes only | documented |
| PVTA | 3 more shape-distance warnings | 10,811 | No — shapes only | documented |
| PVTA | `stop_too_far_from_shape_using_user_distance` | 224 | No — shapes only | documented |
| PVTA | `expired_calendar` | 9 | No — the loader activates services by date, so expired ones never run | documented |
| PVTA | `missing_recommended_field` (`feed_info.feed_version`) | 1 | No | documented |
| PVTA | `mixed_case_recommended_field` (route `38NS`) | 1 | No | documented |
| FRTA | `stop_without_stop_time` | 11 | No — unused stops are never boarded | documented |
| FRTA | `fast_travel_between_consecutive_stops` | 3 | **Yes, slightly** — see below | documented, open |

**FRTA fast travel.** One trip, Route 32 `t_6151941_b_86595_tn_0`, runs about 6 km along
E River St (Orange) between 15:00:00 and 15:02:00 (~180–200 km/h). Arrivals at later
stops on that trip are therefore early by several minutes. The error is optimistic: it can
only make an origin look reachable when it is not, and only via that one afternoon trip
(later stops on it may include Greenfield). The PVTA side is untouched. We keep the
published times (no guessed fix); report to FRTA/Trillium as a feed issue.
