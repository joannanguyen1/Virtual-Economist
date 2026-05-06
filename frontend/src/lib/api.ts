const isBrowser = typeof window !== "undefined";
const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

const currentOrigin = () => (isBrowser ? window.location.origin : "");
const isLocalRuntime = () =>
  isBrowser ? LOCAL_HOSTNAMES.has(window.location.hostname) : true;

export const getAgentApiBase = (): string => {
  const configured = process.env.REACT_APP_AGENT_API_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }

  if (!isLocalRuntime()) {
    return "";
  }

  return "http://localhost:8000";
};

export const getAuthApiBase = (): string => {
  const configured = process.env.REACT_APP_API_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }

  if (!isLocalRuntime()) {
    return `${currentOrigin()}/auth`;
  }

  return "http://localhost:800";
};

type FetchOptions = {
  token?: string | null;
  signal?: AbortSignal;
  limit?: number;
  source?: string;
};

const buildHeaders = (token?: string | null) => ({
  "Content-Type": "application/json",
  ...(token ? { Authorization: `Bearer ${token}` } : {}),
});

export type CitySuggestion = {
  city: string;
  latitude: number;
  longitude: number;
};

export const fetchCitySuggestions = async (
  query: string,
  limit = 10,
  options: FetchOptions = {},
): Promise<CitySuggestion[]> => {
  const API_BASE_URL = getAgentApiBase();
  const url = new URL(`${API_BASE_URL}/api/insights/cities`);
  url.searchParams.set("q", query);
  url.searchParams.set("limit", String(limit));

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: buildHeaders(options.token),
    signal: options.signal,
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch cities (${res.status}).`);
  }

  const payload = (await res.json()) as unknown;
  return Array.isArray(payload) ? (payload as CitySuggestion[]) : [];
};

export type HeatmapPoint = {
  city: string;
  latitude: number;
  longitude: number;
  value: number;
  as_of?: string | null;
};

export type HousingHeatmapResponse = {
  metric: string;
  as_of: string | null;
  point_count: number;
  points: HeatmapPoint[];
};

export const fetchHousingHeatmap = async (
  metric: string,
  bbox: { south: number; north: number; west: number; east: number },
  options: FetchOptions = {},
): Promise<HousingHeatmapResponse> => {
  const API_BASE_URL = getAgentApiBase();
  const url = new URL(`${API_BASE_URL}/api/insights/housing-heatmap`);
  url.searchParams.set("metric", metric);
  if (options.source) {
    url.searchParams.set("source", options.source);
  }
  url.searchParams.set("south", String(bbox.south));
  url.searchParams.set("north", String(bbox.north));
  url.searchParams.set("west", String(bbox.west));
  url.searchParams.set("east", String(bbox.east));
  if (typeof options.limit === "number" && Number.isFinite(options.limit)) {
    url.searchParams.set("limit", String(options.limit));
  }

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: buildHeaders(options.token),
    signal: options.signal,
  });

  const payload = (await res.json()) as unknown;
  if (!res.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail?: unknown }).detail)
        : `Failed to fetch heatmap (${res.status}).`;
    throw new Error(detail);
  }

  return payload as HousingHeatmapResponse;
};

export type FavoriteCity = {
  city: string;
  latitude: number;
  longitude: number;
};

export const fetchFavoriteCities = async (
  options: FetchOptions = {},
): Promise<FavoriteCity[]> => {
  const API_BASE_URL = getAgentApiBase();
  const url = new URL(`${API_BASE_URL}/api/favorites/cities`);

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: buildHeaders(options.token),
    signal: options.signal,
  });

  if (res.status === 401) {
    return [];
  }

  if (!res.ok) {
    throw new Error(`Failed to fetch favorites (${res.status}).`);
  }

  const payload = (await res.json()) as unknown;
  return Array.isArray(payload) ? (payload as FavoriteCity[]) : [];
};

export const addFavoriteCity = async (
  city: FavoriteCity,
  options: FetchOptions = {},
): Promise<FavoriteCity> => {
  const API_BASE_URL = getAgentApiBase();
  const url = new URL(`${API_BASE_URL}/api/favorites/cities`);

  const res = await fetch(url.toString(), {
    method: "POST",
    headers: buildHeaders(options.token),
    signal: options.signal,
    body: JSON.stringify(city),
  });

  const payload = (await res.json()) as unknown;

  if (!res.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail?: unknown }).detail)
        : `Failed to save favorite (${res.status}).`;
    throw new Error(detail);
  }

  return payload as FavoriteCity;
};

export const removeFavoriteCity = async (
  cityLabel: string,
  options: FetchOptions = {},
): Promise<boolean> => {
  const API_BASE_URL = getAgentApiBase();
  const url = new URL(`${API_BASE_URL}/api/favorites/cities`);
  url.searchParams.set("city", cityLabel);

  const res = await fetch(url.toString(), {
    method: "DELETE",
    headers: buildHeaders(options.token),
    signal: options.signal,
  });

  const payload = (await res.json()) as unknown;
  if (!res.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail?: unknown }).detail)
        : `Failed to remove favorite (${res.status}).`;
    throw new Error(detail);
  }

  return Boolean(
    payload && typeof payload === "object" && "ok" in payload
      ? (payload as { ok?: unknown }).ok
      : false,
  );
};
