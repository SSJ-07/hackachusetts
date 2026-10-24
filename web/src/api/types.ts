// Contract types — hand-mirrored from docs/contracts.md §3 and cross-checked
// against the generated OpenAPI schema (./schema.d.ts). These are the shapes the
// UI renders; a drift between this file and schema.d.ts is a bug.
//
// Times are integer seconds since local-midnight of the service date and may
// exceed 86400 (never wrapped) — see docs/contracts.md conventions.

import type { components } from "./schema";

export type Day = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";

/** One hour cell of the audit grid. `share = reached / n`. */
export interface AuditCell {
  day: Day;
  /** appointment start hour, 24h local (7..18) */
  hour: number;
  /** reached / n, 0.0..1.0 */
  share: number;
  /** car-less adults in the community */
  n: number;
  /** how many of them can reach the clinic for this hour */
  reached: number;
}

/** One equity split: a share of a subpopulation of size n. */
export interface EquityGroup {
  share: number;
  n: number;
}

/** The four equity splits shown in the EquityPanel. */
export interface Equity {
  ej: EquityGroup;
  lep: EquityGroup;
  age65: EquityGroup;
  zero_veh: EquityGroup;
}

/** A citation for an on-screen number: name + vintage, optional link. */
export interface SourceRef {
  name: string;
  vintage: string;
  url?: string | null;
}

/** GET /audit and POST /whatif both return this shape. */
export interface AuditResponse {
  cells: AuditCell[];
  equity: Equity;
  sources: SourceRef[];
}

/** POST /whatif request body. */
export interface WhatIfRequest {
  clinic: string;
  shift: {
    /** e.g. "mon-08" — a (day, hour) block */
    block: string;
    /** new start hour, 24h local */
    to: number;
  };
}

/** GET /clinics — the clinics the audit covers. */
export interface Clinic {
  clinic_id: string;
  clinic_name: string;
  visit_type: string;
  visit_minutes: number;
  stop_id: string;
  is_demo_anchor: boolean;
}

export interface ClinicsResponse {
  clinics: Clinic[];
  sources: SourceRef[];
}

/** GET /audit/blockgroups — per-block-group reachable share for the map. */
export interface BlockGroupFeature {
  bg_geoid: string;
  lat: number;
  lon: number;
  carless_adults: number;
  share: number;
  /** transit desert for this clinic/day/hour */
  desert: boolean;
}

export interface BlockGroupsResponse {
  features: BlockGroupFeature[];
  sources: SourceRef[];
}

/** One top-k schedule change the optimizer proposes (GET /suggest). */
export interface SuggestChange {
  /** optimizer move kind, e.g. "move_block" */
  kind: string;
  day: string;
  /** block key the change acts on, e.g. "mon-08" */
  block: string;
  /** new start hour, 24h local */
  to: number;
}

/** One suggestion: a change plus the gain it buys and its citations. */
export interface Suggestion {
  change: SuggestChange;
  /** extra visit-hours of reach this change buys */
  gain_visit_hours: number;
  /** extra car-less adults reached by this change */
  gain_people: number;
  /** provenance for every number in this suggestion; a source may carry
   * `illustrative: true` when it is not yet backed by real data. */
  sources: SuggestSource[];
}

/** A source ref on a suggestion. Superset of SourceRef: the optimizer may flag
 * a source as illustrative (synthetic/placeholder, not real-data-backed). */
export interface SuggestSource extends SourceRef {
  illustrative?: boolean;
}

/** GET /suggest?clinic&day&k&blocks — top-k schedule changes. */
export interface SuggestResponse {
  clinic: string;
  day: string;
  k: number;
  baseline_score: number;
  suggested_score: number;
  baseline_blocks: number[];
  suggested_blocks: number[];
  open_hours: number[];
  changes: Suggestion[];
  sources: SuggestSource[];
}

// --- Compile-time assertions that our hand types match the generated schema.
// If the OpenAPI schema drifts from this file, one of these lines fails to
// typecheck, which fails `npm run build`.
type _AssertAssignable<A extends B, B> = [A] extends [B] ? true : never;
export type _AuditOk = _AssertAssignable<
  components["schemas"]["AuditResponse"],
  AuditResponse
>;
export type _CellOk = _AssertAssignable<
  components["schemas"]["AuditCell"],
  AuditCell
>;
export type _EquityOk = _AssertAssignable<
  components["schemas"]["Equity"],
  Equity
>;
export type _SourceOk = _AssertAssignable<
  components["schemas"]["SourceRef"],
  SourceRef
>;
export type _ClinicsOk = _AssertAssignable<
  components["schemas"]["ClinicsResponse"],
  ClinicsResponse
>;
export type _BgOk = _AssertAssignable<
  components["schemas"]["BlockGroupsResponse"],
  BlockGroupsResponse
>;
