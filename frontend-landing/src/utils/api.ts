import axios from 'axios';

export const VENTURE_ID = '550e8400-e29b-41d4-a716-446655440000';
export const API_KEY = 'neufin.FGUN8eq_O2erbcVVyCtdukMAtcGcwSdBErRK3TZ2FEI';

const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
    'X-Venture-ID': VENTURE_ID,
    'X-API-Key': API_KEY,
  },
});

export function authedApi(accessToken: string) {
  return axios.create({
    baseURL,
    headers: {
      'Content-Type': 'application/json',
      'X-Venture-ID': VENTURE_ID,
      'X-API-Key': API_KEY,
      'Authorization': `Bearer ${accessToken}`,
    },
  });
}
