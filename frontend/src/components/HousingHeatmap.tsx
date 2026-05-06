import React, { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import type { LatLngBounds } from "leaflet";
import L from "leaflet";
import "leaflet.heat";

import {
  addFavoriteCity,
  fetchCitySuggestions,
  fetchFavoriteCities,
  fetchHousingHeatmap,
  removeFavoriteCity,
  type CitySuggestion,
  type FavoriteCity,
  type HeatmapPoint,
} from "../lib/api";
import { getAuthToken } from "../lib/auth";

type BBox = { south: number; north: number; west: number; east: number };

type ViewKey = "zillow" | "census" | "both";

type ViewOption = { key: ViewKey; label: string };

const VIEW_OPTIONS: Record<ViewKey, ViewOption> = {
  zillow: { key: "zillow", label: "Dataset (Zillow)" },
  census: { key: "census", label: "Live (Census ACS)" },
  both: { key: "both", label: "Both (overlay)" },
};

type MetricDef = {
  key: string;
  label: string;
  zillowMetric?: string;
  censusMetric?: string;
};

const METRICS: MetricDef[] = [
  {
    key: "home_value",
    label: "Home value",
    zillowMetric: "zhvi",
    censusMetric: "median_home_value",
  },
  {
    key: "rent",
    label: "Rent",
    zillowMetric: "zori",
    censusMetric: "median_gross_rent",
  },
  {
    key: "income",
    label: "Median household income (ACS)",
    censusMetric: "median_household_income",
  },
  {
    key: "population",
    label: "Population (ACS)",
    censusMetric: "population",
  },
  {
    key: "median_age",
    label: "Median age (ACS)",
    censusMetric: "median_age",
  },
  {
    key: "poverty_rate",
    label: "Poverty rate % (ACS)",
    censusMetric: "poverty_rate",
  },
  {
    key: "inventory",
    label: "Inventory",
    zillowMetric: "inventory",
  },
  {
    key: "price_cuts",
    label: "Price cuts",
    zillowMetric: "price_cuts",
  },
  {
    key: "new_listings",
    label: "New listings",
    zillowMetric: "new_listings",
  },
  {
    key: "mean_days_to_pending",
    label: "Mean days to pending",
    zillowMetric: "mean_days_to_pending",
  },
];

const getMetricDef = (key: string): MetricDef => {
  const found = METRICS.find((metric) => metric.key === key);
  return found ?? METRICS[0];
};

const getMetricsForView = (view: ViewKey): MetricDef[] => {
  if (view === "zillow") {
    return METRICS.filter((metric) => Boolean(metric.zillowMetric));
  }
  if (view === "census") {
    return METRICS.filter((metric) => Boolean(metric.censusMetric));
  }
  return METRICS.filter((metric) => Boolean(metric.zillowMetric) && Boolean(metric.censusMetric));
};

const boundsToBBox = (bounds: LatLngBounds): BBox => {
  const southWest = bounds.getSouthWest();
  const northEast = bounds.getNorthEast();
  return {
    south: southWest.lat,
    west: southWest.lng,
    north: northEast.lat,
    east: northEast.lng,
  };
};

const HeatLayer: React.FC<{
  points: Array<[number, number, number]>;
  radius?: number;
  blur?: number;
  minOpacity?: number;
  gradient?: Record<number, string>;
}> = ({ points, radius = 28, blur = 18, minOpacity = 0.25, gradient }) => {
  const map = useMap();

  useEffect(() => {
    const heatFactory = (L as unknown as { heatLayer?: any }).heatLayer;
    if (!heatFactory) {
      return undefined;
    }

    const layer = heatFactory(points, {
      radius,
      blur,
      minOpacity,
      ...(gradient ? { gradient } : {}),
    });

    layer.addTo(map);
    return () => {
      map.removeLayer(layer);
    };
  }, [blur, gradient, map, minOpacity, points, radius]);

  return null;
};

const BoundsReporter: React.FC<{ onChange: (bbox: BBox) => void }> = ({
  onChange,
}) => {
  const lastBBox = useRef<string>("");

  const pushBounds = (bounds: LatLngBounds) => {
    const bbox = boundsToBBox(bounds);
    const signature = `${bbox.south.toFixed(4)}:${bbox.west.toFixed(4)}:${bbox.north.toFixed(4)}:${bbox.east.toFixed(4)}`;
    if (signature === lastBBox.current) {
      return;
    }
    lastBBox.current = signature;
    onChange(bbox);
  };

  const map = useMapEvents({
    moveend() {
      pushBounds(map.getBounds());
    },
    zoomend() {
      pushBounds(map.getBounds());
    },
  });

  useEffect(() => {
    pushBounds(map.getBounds());
  }, [map]);

  return null;
};

const CenterUpdater: React.FC<{ center: [number, number] | null }> = ({
  center,
}) => {
  const map = useMap();

  useEffect(() => {
    if (!center) {
      return;
    }
    map.setView(center, Math.max(map.getZoom(), 9), { animate: false });
  }, [center, map]);

  return null;
};

const normalizeHeatPoints = (points: HeatmapPoint[]): Array<[number, number, number]> => {
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min;

  return points.map((p) => {
    const normalized = spread <= 0 ? 1 : (p.value - min) / spread;
    const intensity = 0.25 + normalized * 0.75;
    return [p.latitude, p.longitude, intensity];
  });
};

const isAbortError = (err: unknown): boolean => {
  if (!err || typeof err !== "object") {
    return false;
  }

  if ("name" in err && (err as { name?: unknown }).name === "AbortError") {
    return true;
  }

  if ("message" in err) {
    const message = String((err as { message?: unknown }).message ?? "").toLowerCase();
    if (message.includes("aborted")) {
      return true;
    }
  }

  return false;
};

const HousingHeatmap: React.FC = () => {
  const [metricKey, setMetricKey] = useState<string>(METRICS[0].key);
  const [view, setView] = useState<ViewKey>("zillow");

  const [cityQuery, setCityQuery] = useState<string>("");
  const [suggestions, setSuggestions] = useState<CitySuggestion[]>([]);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [selectedCity, setSelectedCity] = useState<CitySuggestion | null>(null);
  const [recenterTo, setRecenterTo] = useState<[number, number] | null>(null);

  const [bbox, setBbox] = useState<BBox | null>(null);
  const [points, setPoints] = useState<HeatmapPoint[]>([]);
  const [overlayZillowPoints, setOverlayZillowPoints] = useState<HeatmapPoint[]>([]);
  const [overlayCensusPoints, setOverlayCensusPoints] = useState<HeatmapPoint[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [favorites, setFavorites] = useState<FavoriteCity[]>([]);
  const [favoriteError, setFavoriteError] = useState<string | null>(null);
  const [isSavingFavorite, setIsSavingFavorite] = useState(false);

  const metricDef = useMemo(() => getMetricDef(metricKey), [metricKey]);
  const metricOptions = useMemo(() => getMetricsForView(view), [view]);
  const hasOverlayMetrics = useMemo(
    () => METRICS.some((metric) => Boolean(metric.zillowMetric) && Boolean(metric.censusMetric)),
    [],
  );

  useEffect(() => {
    if (!metricOptions.some((metric) => metric.key === metricKey)) {
      setMetricKey(metricOptions[0]?.key ?? METRICS[0].key);
    }
  }, [metricKey, metricOptions]);

  useEffect(() => {
    const query = cityQuery.trim();
    if (query.length < 2) {
      setSuggestions([]);
      setIsSuggesting(false);
      return;
    }

    let active = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      try {
        setIsSuggesting(true);
        const results = await fetchCitySuggestions(query, 8, {
          signal: controller.signal,
        });
        if (!active || controller.signal.aborted) {
          return;
        }
        setSuggestions(results);
      } catch (err) {
        if (!active || controller.signal.aborted || isAbortError(err)) {
          return;
        }

        if (!controller.signal.aborted) {
          setSuggestions([]);
        }
      } finally {
        if (active) {
          setIsSuggesting(false);
        }
      }
    }, 250);

    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [cityQuery]);

  const loadFavorites = async (signal?: AbortSignal) => {
    try {
      setFavoriteError(null);
      const token = getAuthToken();
      const results = await fetchFavoriteCities({ token, signal });
      setFavorites(results);
    } catch (err) {
      if (signal?.aborted) {
        return;
      }

      const maybeAbort =
        err && typeof err === "object" && "name" in err && (err as { name?: unknown }).name;
      if (maybeAbort === "AbortError") {
        return;
      }

      setFavorites([]);
      setFavoriteError(err instanceof Error ? err.message : "Unable to load favorites.");
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    void loadFavorites(controller.signal);

    const onAuthChanged = () => {
      void loadFavorites();
    };
    window.addEventListener("auth-changed", onAuthChanged);

    return () => {
      controller.abort();
      window.removeEventListener("auth-changed", onAuthChanged);
    };
  }, []);

  useEffect(() => {
    if (!bbox) {
      return;
    }

    if (!metricOptions.some((metric) => metric.key === metricKey)) {
      return;
    }

    const zillowLimit = selectedCity ? 2500 : 800;
    const censusLimit = 250;

    const overlayEnabled =
      view === "both" && Boolean(metricDef.zillowMetric) && Boolean(metricDef.censusMetric);

    let active = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      try {
        setIsLoading(true);
        setError(null);

        if (overlayEnabled) {
          const [zillowResult, censusResult] = await Promise.allSettled([
            fetchHousingHeatmap(metricDef.zillowMetric as string, bbox, {
              signal: controller.signal,
              limit: zillowLimit,
              source: "zillow",
            }),
            fetchHousingHeatmap(metricDef.censusMetric as string, bbox, {
              signal: controller.signal,
              limit: censusLimit,
              source: "census",
            }),
          ]);

          if (!active || controller.signal.aborted) {
            return;
          }

          const zillowPoints =
            zillowResult.status === "fulfilled" ? zillowResult.value.points ?? [] : [];
          const censusPoints =
            censusResult.status === "fulfilled" ? censusResult.value.points ?? [] : [];

          setOverlayZillowPoints(zillowPoints);
          setOverlayCensusPoints(censusPoints);

          setPoints([]);

          if (zillowResult.status === "rejected" && censusResult.status === "rejected") {
            if (isAbortError(zillowResult.reason) && isAbortError(censusResult.reason)) {
              return;
            }

            const zillowMessage =
              zillowResult.reason instanceof Error
                ? zillowResult.reason.message
                : "Unable to load Zillow heatmap.";
            const censusMessage =
              censusResult.reason instanceof Error
                ? censusResult.reason.message
                : "Unable to load Census heatmap.";
            setError(`${zillowMessage} ${censusMessage}`);
          }
        } else {
          const metricToUse = view === "census" ? metricDef.censusMetric : metricDef.zillowMetric;

          if (!metricToUse) {
            throw new Error("Selected metric is not available for this view.");
          }

          const response = await fetchHousingHeatmap(metricToUse, bbox, {
            signal: controller.signal,
            limit: view === "census" ? censusLimit : zillowLimit,
            source: view,
          });
          if (!active || controller.signal.aborted) {
            return;
          }
          setOverlayZillowPoints([]);
          setOverlayCensusPoints([]);
          setPoints(response.points ?? []);
        }
      } catch (err) {
        if (!active || controller.signal.aborted || isAbortError(err)) {
          return;
        }

        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Unable to load heatmap data.");
          setOverlayZillowPoints([]);
          setOverlayCensusPoints([]);
          setPoints([]);
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }, 200);

    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [bbox, metricDef, metricKey, metricOptions, selectedCity, view]);

  const heatPoints = useMemo(() => {
    if (!points.length) {
      return [];
    }
    return normalizeHeatPoints(points);
  }, [points]);

  const overlayZillowHeatPoints = useMemo(() => {
    if (!overlayZillowPoints.length) {
      return [];
    }
    return normalizeHeatPoints(overlayZillowPoints);
  }, [overlayZillowPoints]);

  const overlayCensusHeatPoints = useMemo(() => {
    if (!overlayCensusPoints.length) {
      return [];
    }
    return normalizeHeatPoints(overlayCensusPoints);
  }, [overlayCensusPoints]);

  const handlePickSuggestion = (item: CitySuggestion) => {
    setSelectedCity(item);
    setCityQuery(item.city);
    setSuggestions([]);
    setRecenterTo([item.latitude, item.longitude]);
  };

  const handleClearCity = () => {
    setCityQuery("");
    setSelectedCity(null);
    setRecenterTo(null);
    setSuggestions([]);
    setIsSuggesting(false);
  };

  const selectedCityFavorite = useMemo(() => {
    if (!selectedCity) {
      return null;
    }
    return favorites.find((fav) => fav.city === selectedCity.city) ?? null;
  }, [favorites, selectedCity]);

  const canToggleFavorite = Boolean(selectedCity);

  const toggleFavorite = async () => {
    if (!selectedCity) {
      return;
    }

    const token = getAuthToken();
    if (!token) {
      setFavoriteError("Log in to save favorites.");
      return;
    }

    try {
      setIsSavingFavorite(true);
      setFavoriteError(null);

      if (selectedCityFavorite) {
        await removeFavoriteCity(selectedCity.city, { token });
        setFavorites((prev) => prev.filter((fav) => fav.city !== selectedCity.city));
      } else {
        const saved = await addFavoriteCity(
          {
            city: selectedCity.city,
            latitude: selectedCity.latitude,
            longitude: selectedCity.longitude,
          },
          { token },
        );
        setFavorites((prev) => {
          const next = prev.filter((fav) => fav.city !== saved.city);
          next.push(saved);
          next.sort((a, b) => a.city.localeCompare(b.city));
          return next;
        });
      }
    } catch (err) {
      setFavoriteError(err instanceof Error ? err.message : "Unable to update favorite.");
    } finally {
      setIsSavingFavorite(false);
    }
  };

  return (
    <div className="heatmap-root">
      <div className="heatmap-controls">
        <label className="heatmap-label">
          City, State
          <div className="heatmap-city-row">
            <input
              className="heatmap-input"
              value={cityQuery}
              onChange={(e) => {
                setCityQuery(e.target.value);
                setSelectedCity(null);
                setRecenterTo(null);
              }}
              placeholder="e.g., Los Angeles, CA"
              autoComplete="off"
            />
            {cityQuery.length > 0 ? (
              <button
                type="button"
                className="heatmap-clear"
                onClick={handleClearCity}
                aria-label="Clear city search"
                title="Clear"
              >
                ×
              </button>
            ) : null}
            <button
              type="button"
              className={
                selectedCityFavorite ? "heatmap-favorite active" : "heatmap-favorite"
              }
              onClick={toggleFavorite}
              disabled={!canToggleFavorite || isSavingFavorite}
              title={
                !selectedCity
                  ? "Select a city to favorite"
                  : selectedCityFavorite
                    ? "Remove from favorites"
                    : "Add to favorites"
              }
            >
              {selectedCityFavorite ? "★" : "☆"}
            </button>
          </div>
        </label>

        <label className="heatmap-label">
          View
          <select
            className="heatmap-select"
            value={view}
            onChange={(e) => setView(e.target.value as ViewKey)}
          >
            <option value={VIEW_OPTIONS.zillow.key}>{VIEW_OPTIONS.zillow.label}</option>
            <option value={VIEW_OPTIONS.census.key}>{VIEW_OPTIONS.census.label}</option>
            <option value={VIEW_OPTIONS.both.key} disabled={!hasOverlayMetrics}>
              {VIEW_OPTIONS.both.label}
            </option>
          </select>
        </label>

        <label className="heatmap-label">
          Metric
          <select
            className="heatmap-select"
            value={metricKey}
            onChange={(e) => setMetricKey(e.target.value)}
            disabled={metricOptions.length <= 1}
          >
            {metricOptions.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {(isSuggesting || suggestions.length > 0) && (
        <div className="heatmap-suggestions">
          {suggestions.length === 0 ? (
            <div className="heatmap-suggestion muted">Searching…</div>
          ) : (
            suggestions.map((item) => (
              <button
                key={item.city}
                type="button"
                className="heatmap-suggestion"
                onClick={() => handlePickSuggestion(item)}
              >
                {item.city}
              </button>
            ))
          )}
        </div>
      )}

      {favorites.length > 0 ? (
        <div className="heatmap-favorites">
          <div className="heatmap-favorites-label">Favorites</div>
          <div className="heatmap-favorites-list">
            {favorites.map((fav) => (
              <button
                key={fav.city}
                type="button"
                className="heatmap-favorite-item"
                onClick={() =>
                  handlePickSuggestion({
                    city: fav.city,
                    latitude: fav.latitude,
                    longitude: fav.longitude,
                  })
                }
              >
                {fav.city}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="heatmap-meta">
        <span>
          {isLoading
            ? "Loading…"
            : view === "both"
              ? `${overlayZillowPoints.length} Zillow + ${overlayCensusPoints.length} Census points`
              : `${points.length} points`}
        </span>
        {error || favoriteError ? (
          <span className="heatmap-error">{error ?? favoriteError}</span>
        ) : null}
      </div>

      <div className="heatmap-map">
        <MapContainer
          center={[39.5, -98.35]}
          zoom={4}
          scrollWheelZoom
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <BoundsReporter onChange={setBbox} />
          <CenterUpdater
            center={recenterTo}
          />
          {view === "both" ? (
            <>
              {overlayZillowHeatPoints.length > 0 ? (
                <HeatLayer points={overlayZillowHeatPoints} />
              ) : null}
              {overlayCensusHeatPoints.length > 0 ? (
                <HeatLayer
                  points={overlayCensusHeatPoints}
                  radius={24}
                  blur={16}
                  minOpacity={0.18}
                  gradient={{
                    0.0: "#0b1f3b",
                    0.35: "#1956a6",
                    0.6: "#2d8cff",
                    1.0: "#bfe3ff",
                  }}
                />
              ) : null}
            </>
          ) : heatPoints.length > 0 ? (
            <HeatLayer points={heatPoints} />
          ) : null}
        </MapContainer>
      </div>
    </div>
  );
};

export default HousingHeatmap;
