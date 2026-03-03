export interface Trade {
  id: string;
  timestamp: number;
  asset: string;
  side: 'BUY' | 'SELL';
  price: number;
  quantity: number;
  sentiment: number; // 0-1 scale
  primaryBias: string;
  userNote?: string; // Optional thesis note from pre-flight check
}

export interface BiasAlert {
  id: string;
  type: 'ANCHORING' | 'FOMO' | 'LOSS_AVERSION' | 'CONFIRMATION' | 'RECENCY';
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  message: string;
  timestamp: number;
}

export interface CoachNote {
  id: string;
  timestamp: number;
  note: string;
  type: 'WARNING' | 'INFO' | 'SUCCESS';
}

export interface LiquidityLevel {
  price: number;
  volume: number;
  intensity: number; // 0-1 for heatmap
}