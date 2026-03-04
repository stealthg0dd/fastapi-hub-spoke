import axios from 'axios';

// ── Neufin venture constants ──────────────────────────────────────────────────
export const VENTURE_ID = '550e8400-e29b-41d4-a716-446655440000';
export const API_KEY    = 'neufin.FGUN8eq_O2erbcVVyCtdukMAtcGcwSdBErRK3TZ2FEI';

// Hardcoded demo user — replace with real auth when auth layer is added
export const USER_ID = '00000000-0000-0000-0000-000000000001';

// ── Axios instance ────────────────────────────────────────────────────────────
// Use || (not ??) so that an empty-string VITE_API_URL (e.g. unset in Vercel)
// falls back to the localhost default rather than silently using "" as the URL.
const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
    'X-Venture-ID': VENTURE_ID,
    'X-API-Key': API_KEY,
  },
});

// ── Response shape helpers ────────────────────────────────────────────────────

export interface DashboardSummary {
  venture_id: string;
  total_trade_volume: number;
  top_biases: { bias_name: string; frequency: number }[];
  recent_nudges: {
    user_id: string;
    coach_note: string;
    detected_biases: string[];
    behavioral_risk_score: number | null;
    analyzed_at: string;
  }[];
}

export interface PortfolioHolding {
  ticker: string;
  quantity: number;
  avg_price: number;
  source: string;
  imported_at: string;
}

export interface SubscriptionResponse {
  status: 'already_subscribed' | 'trial_active' | 'checkout_required';
  trial_ends_at: string | null;
  checkout_url: string | null;
}
