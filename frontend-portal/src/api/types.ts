export interface HoldingOut {
  ticker: string;
  quantity: number;
  avg_price: number;
  source: string;
  /**
   * ISO-8601 date-time string.
   */
  imported_at: string;
}

export interface BiasFrequency {
  bias_name: string;
  frequency: number;
}

export interface RecentNudge {
  user_id: string;
  coach_note: string;
  detected_biases: string[];
  /**
   * May be null in the API response.
   */
  behavioral_risk_score: number | null;
  /**
   * ISO-8601 date-time string.
   */
  analyzed_at: string;
}

export interface DashboardSummaryResponse {
  venture_id: string;
  total_trade_volume: number;
  top_biases: BiasFrequency[];
  recent_nudges: RecentNudge[];
}

export interface VentureRiskEntry {
  venture: string;
  avg_risk: number;
  total_trades: number;
}

export interface UploadSummary {
  imported: number;
  skipped: number;
  errors: string[];
}

export interface ChatResponse {
  venture_id: string;
  response: string;
  pii_detected: string[];
}


