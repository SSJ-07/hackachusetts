import { createContext, useContext } from "react";

/** Any ProvenanceChip can open the drawer for a given provenance id. The Planner
 * screen provides the handler; a chip rendered with a `provId` calls it. */
export type OpenProvenance = (id: string, opener: HTMLElement | null) => void;

export const ProvenanceContext = createContext<OpenProvenance | null>(null);

export function useProvenance(): OpenProvenance | null {
  return useContext(ProvenanceContext);
}
