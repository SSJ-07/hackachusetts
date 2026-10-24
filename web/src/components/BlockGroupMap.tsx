import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { FeatureCollection } from "geojson";
import { useTranslation } from "react-i18next";

/**
 * Block-group map. Reads an OPTIONAL static GeoJSON from
 * `public/data/origins.geojson` (Point features: bg_geoid, carless_adults,
 * ej_flag). If it is missing we show an accessible "map data not loaded" notice
 * rather than crashing — the audit numbers above do not depend on the map
 * (every map interaction also has a non-map alternative: the pickers).
 *
 * No basemap tiles from a paid or keyed service (ui-style.md): we use a blank
 * style and draw only our own points.
 */
const GEOJSON_URL = `${import.meta.env.BASE_URL}data/origins.geojson`;

const BLANK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    {
      id: "bg",
      type: "background",
      paint: { "background-color": "#e9edf1" },
    },
  ],
  glyphs: undefined,
};

export function BlockGroupMap() {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "missing">(
    "loading",
  );

  useEffect(() => {
    let map: maplibregl.Map | null = null;
    let cancelled = false;

    async function run() {
      // Probe for the optional data file first.
      let geojson: FeatureCollection | null = null;
      try {
        const res = await fetch(GEOJSON_URL, { headers: { Accept: "application/json" } });
        if (res.ok) {
          const text = await res.text();
          try {
            geojson = JSON.parse(text) as FeatureCollection;
          } catch {
            geojson = null;
          }
        }
      } catch {
        geojson = null;
      }
      if (cancelled) return;
      if (
        !geojson ||
        geojson.type !== "FeatureCollection" ||
        !Array.isArray(geojson.features) ||
        geojson.features.length === 0
      ) {
        setState("missing");
        return;
      }

      if (!ref.current) return;
      map = new maplibregl.Map({
        container: ref.current,
        style: BLANK_STYLE,
        center: [-72.59, 42.1],
        zoom: 9,
        attributionControl: false,
      });
      map.addControl(new maplibregl.NavigationControl({}), "top-right");
      map.on("load", () => {
        if (!map || cancelled) return;
        map.addSource("origins", { type: "geojson", data: geojson! });
        map.addLayer({
          id: "origins-circles",
          type: "circle",
          source: "origins",
          paint: {
            "circle-radius": 5,
            // colour by EJ flag; a numbered legend names the two classes.
            "circle-color": [
              "case",
              ["==", ["get", "ej_flag"], true],
              "#08519c",
              "#6baed6",
            ],
            "circle-stroke-color": "#11181c",
            "circle-stroke-width": 1,
          },
        });
        setState("ready");
      });
    }

    void run();
    return () => {
      cancelled = true;
      if (map) map.remove();
    };
  }, []);

  if (state === "missing") {
    return (
      <section className="panel" aria-labelledby="map-h">
        <h2 id="map-h">{t("map.title")}</h2>
        <p className="notice" role="note">
          {t("map.notLoaded")}
        </p>
      </section>
    );
  }

  return (
    <section className="panel" aria-labelledby="map-h">
      <h2 id="map-h">{t("map.title")}</h2>
      <div
        className="map-wrap"
        ref={ref}
        role="group"
        aria-label={t("map.title")}
      />
      <ol className="legend" aria-label={t("map.legendTitle")}>
        <li className="swatch">
          <span
            className="box"
            style={{ background: "#08519c" }}
            aria-hidden="true"
          />
          1. {t("equity.groups.ej")}
        </li>
        <li className="swatch">
          <span
            className="box"
            style={{ background: "#6baed6" }}
            aria-hidden="true"
          />
          2. {t("equity.groups.zero_veh")}
        </li>
      </ol>
    </section>
  );
}
