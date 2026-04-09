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
