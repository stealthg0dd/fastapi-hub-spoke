import type { Trade, BiasAlert, CoachNote, LiquidityLevel } from '../types/trading';

// SEC fee: $0.01 per share
// Brokerage fee: $0.50 per trade (standard)
export const calculatePnL = (shares: number, entryPrice: number, exitPrice: number, side: 'BUY' | 'SELL'): number => {
  const rawPnL = side === 'BUY' ? (exitPrice - entryPrice) * shares : (entryPrice - exitPrice) * shares;
  const secFee = shares * 0.01; // $0.01 per share SEC fee
  const brokerageFee = 0.50; // $0.50 per trade
  return rawPnL - secFee - brokerageFee;
};

export const generateCandlestickData = (basePrice: number = 178.50) => {
  const data = [];
  let currentPrice = basePrice;
  const now = Date.now() / 1000;
  
  for (let i = 300; i >= 0; i--) {
    const time = now - i * 300; // 5-minute candles
    const change = (Math.random() - 0.5) * 2; // Smaller movements for stocks
    currentPrice += change;
    
    const open = currentPrice;
    const close = currentPrice + (Math.random() - 0.5) * 1.5;
    const high = Math.max(open, close) + Math.random() * 0.8;
    const low = Math.min(open, close) - Math.random() * 0.8;
    
    data.push({
      time: Math.floor(time) as any,
      open,
      high,
      low,
      close,
    });
  }
  
  return data;
};

export const generateLiquidityData = (currentPrice: number): LiquidityLevel[] => {
  const levels: LiquidityLevel[] = [];
  const range = 5; // $5 range for stocks
  const step = 0.25; // Quarter increments
  
  for (let i = -range; i <= range; i += step) {
    const price = currentPrice + i;
    const distance = Math.abs(i);
    // Bid/Ask sizes in hundreds of shares
    const volume = (Math.random() * 50 + (distance < 1 ? 80 : 30)) * 100;
    const intensity = Math.min(1, volume / 10000);
    
    levels.push({ price, volume, intensity });
  }
  
  return levels.sort((a, b) => b.price - a.price);
};

export const mockTrades: Trade[] = [
  {
    id: '1',
    timestamp: Date.now() - 120000,
    asset: 'AAPL',
    side: 'BUY',
    price: 178.25,
    quantity: 50,
    sentiment: 0.85,
    primaryBias: 'FOMO'
  },
  {
    id: '2',
    timestamp: Date.now() - 180000,
    asset: 'TSLA',
    side: 'SELL',
    price: 242.75,
    quantity: 25,
    sentiment: 0.35,
    primaryBias: 'LOSS_AVERSION'
  },
  {
    id: '3',
    timestamp: Date.now() - 300000,
    asset: 'NVDA',
    side: 'BUY',
    price: 862.50,
    quantity: 10,
    sentiment: 0.55,
    primaryBias: 'NEUTRAL'
  },
  {
    id: '4',
    timestamp: Date.now() - 420000,
    asset: 'MSFT',
    side: 'SELL',
    price: 417.20,
    quantity: 30,
    sentiment: 0.92,
    primaryBias: 'OVERCONFIDENCE'
  },
  {
    id: '5',
    timestamp: Date.now() - 540000,
    asset: 'GOOGL',
    side: 'BUY',
    price: 141.80,
    quantity: 40,
    sentiment: 0.68,
    primaryBias: 'CONFIRMATION'
  },
];

export const mockBiasAlerts: BiasAlert[] = [
  {
    id: '1',
    type: 'ANCHORING',
    severity: 'HIGH',
    message: 'Price anchored to $178 — ignoring new data',
    timestamp: Date.now() - 60000
  },
  {
    id: '2',
    type: 'FOMO',
    severity: 'MEDIUM',
    message: 'Elevated FOMO detected in recent entries',
    timestamp: Date.now() - 180000
  },
  {
    id: '3',
    type: 'LOSS_AVERSION',
    severity: 'LOW',
    message: 'Holding losing position longer than strategy allows',
    timestamp: Date.now() - 300000
  },
];

export const mockCoachNotes: CoachNote[] = [
  {
    id: '1',
    timestamp: Date.now() - 30000,
    note: 'Risk score elevated to 7.2 — consider reducing position size',
    type: 'WARNING'
  },
  {
    id: '2',
    timestamp: Date.now() - 90000,
    note: 'Sentiment divergence detected between tech and financial sectors',
    type: 'INFO'
  },
  {
    id: '3',
    timestamp: Date.now() - 150000,
    note: 'Position sizing adheres to risk parameters — well executed',
    type: 'SUCCESS'
  },
  {
    id: '4',
    timestamp: Date.now() - 240000,
    note: 'Multiple FOMO signals in last 30m — recommend pause',
    type: 'WARNING'
  },
  {
    id: '5',
    timestamp: Date.now() - 320000,
    note: 'Market volatility increasing — adjust stop losses',
    type: 'INFO'
  },
];

// Market hours checker (9:30 AM - 4:00 PM EST)
export const isMarketHours = (): boolean => {
  const now = new Date();
  const estTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const hours = estTime.getHours();
  const minutes = estTime.getMinutes();
  const currentTime = hours * 60 + minutes;
  
  const marketOpen = 9 * 60 + 30; // 9:30 AM
  const marketClose = 16 * 60; // 4:00 PM
  
  return currentTime >= marketOpen && currentTime < marketClose;
};

export const getMarketStatus = (): 'OPEN' | 'PRE_MARKET' | 'POST_MARKET' | 'CLOSED' => {
  const now = new Date();
  const estTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const hours = estTime.getHours();
  const minutes = estTime.getMinutes();
  const currentTime = hours * 60 + minutes;
  const dayOfWeek = estTime.getDay();
  
  // Weekend check
  if (dayOfWeek === 0 || dayOfWeek === 6) {
    return 'CLOSED';
  }
  
  const preMarketStart = 4 * 60; // 4:00 AM
  const marketOpen = 9 * 60 + 30; // 9:30 AM
  const marketClose = 16 * 60; // 4:00 PM
  const postMarketEnd = 20 * 60; // 8:00 PM
  
  if (currentTime >= marketOpen && currentTime < marketClose) {
    return 'OPEN';
  } else if (currentTime >= preMarketStart && currentTime < marketOpen) {
    return 'PRE_MARKET';
  } else if (currentTime >= marketClose && currentTime < postMarketEnd) {
    return 'POST_MARKET';
  }
  
  return 'CLOSED';
};
