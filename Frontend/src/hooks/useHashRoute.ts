import { useCallback, useEffect, useState } from "react";

/** All application routes (hash-based, no extra dependency). */
export const ROUTES = ["/", "/explorer", "/dashboard", "/hazards", "/compare", "/report"] as const;
export type Route = (typeof ROUTES)[number];

function parseHash(): Route {
  const h = window.location.hash.replace(/^#/, "");
  return (ROUTES as readonly string[]).includes(h) ? (h as Route) : "/";
}

/** Tiny hash router: returns [currentRoute, navigate]. */
export function useHashRoute(): [Route, (r: Route) => void] {
  const [route, setRoute] = useState<Route>(parseHash);

  useEffect(() => {
    const onChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const navigate = useCallback((r: Route) => {
    window.location.hash = r;
    window.scrollTo({ top: 0 });
  }, []);

  return [route, navigate];
}
