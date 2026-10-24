import { useEffect, useState } from "react";

/** The three top-level routes. Hash-based so it works on static hosting with no
 * server rewrite and adds no router dependency. */
export type Route = "/audit" | "/planner" | "/about";

const ROUTES: Route[] = ["/audit", "/planner", "/about"];

function parse(hash: string): Route {
  const path = hash.replace(/^#/, "");
  return (ROUTES as string[]).includes(path) ? (path as Route) : "/audit";
}

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() =>
    typeof window === "undefined" ? "/audit" : parse(window.location.hash),
  );
  useEffect(() => {
    const onHash = () => setRoute(parse(window.location.hash));
    window.addEventListener("hashchange", onHash);
    if (!window.location.hash) window.location.hash = "#/audit";
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return route;
}
