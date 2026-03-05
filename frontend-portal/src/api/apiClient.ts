import axios, { AxiosInstance } from "axios";
import { toast } from "sonner";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

if (!API_BASE_URL) {
  // Intentionally fail fast in dev if the env var is missing.
  // In production you may want to handle this more gracefully.
  // eslint-disable-next-line no-console
  console.warn("VITE_API_BASE_URL is not set. API calls will likely fail.");
}

let currentVentureId: string | null = null;

export const setVentureId = (ventureId: string | null) => {
  currentVentureId = ventureId;
};

const getVentureId = (): string | null => {
  if (currentVentureId !== null) {
    return currentVentureId;
  }

  try {
    const stored = window.localStorage.getItem("ventureId");
    return stored || null;
  } catch {
    return null;
  }
};

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const ventureId = getVentureId();

  if (ventureId) {
    if (!config.headers) {
      config.headers = {};
    }

    config.headers["X-Venture-ID"] = ventureId;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status as number | undefined;

    if (status === 422) {
      toast.error("Data Validation Error: Please check your input.");
    } else if (status === 401 || status === 403) {
      toast.error("Access Denied: Invalid Venture ID.");
    } else if (status >= 500) {
      toast.error("Server Error: Please try again in a moment.");
    }

    return Promise.reject(error);
  },
);

export default apiClient;

