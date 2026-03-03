import { useCallback, useEffect, useState } from 'react';
import { TradingChart } from '../components/TradingChart';
import { BiasTerminal } from '../components/BiasTerminal';
import { ExecutionDock } from '../components/ExecutionDock';
import { TradeEntry } from '../components/TradeEntry';
import { Header } from '../components/Header';
import { MarketStats } from '../components/MarketStats';
import { TrialBanner } from '../components/TrialBanner';
import { PreFlightCheckModal } from '../components/PreFlightCheckModal';
import { EquityCurve } from '../components/EquityCurve';
import { TickerSearch } from '../components/TickerSearch';
import { EmotionalBreaker } from '../components/EmotionalBreaker';
import { Watchlist } from '../components/Watchlist';
import { TrialExpiredOverlay } from '../components/TrialExpiredOverlay';
import { mockTrades } from '../utils/mockData';
import { api, USER_ID, type DashboardSummary } from '../../utils/api';
import { useSubscriptionContext } from '../hooks/useSubscription';
import type { BiasAlert, CoachNote, Trade } from '../types/trading';

interface SelectedStock {
  ticker: string;
  name: string;
  exchange: 'NYSE' | 'NASDAQ';
  price: number;
}

// ── Mapping helpers ────────────────────────────────────────────────────────────

function mapBiasType(name: string): BiasAlert['type'] {
  const n = name.toLowerCase();
  if (n.includes('anchor')) return 'ANCHORING';
  if (n.includes('fomo') || n.includes('overconfid')) return 'FOMO';
  if (n.includes('loss')) return 'LOSS_AVERSION';
  if (n.includes('recency') || n.includes('recent')) return 'RECENCY';
  return 'CONFIRMATION';
}

function mapBiasAlerts(summary: DashboardSummary): BiasAlert[] {
  return summary.top_biases.map((b, i) => ({
    id: `bias-${i}`,
    type: mapBiasType(b.bias_name),
    severity: b.frequency >= 3 ? 'HIGH' : b.frequency >= 2 ? 'MEDIUM' : 'LOW',
    message: `Detected ${b.frequency} time${b.frequency !== 1 ? 's' : ''} in recent trades`,
    timestamp: Date.now(),
  }));
}

function mapCoachNotes(summary: DashboardSummary): CoachNote[] {
  return summary.recent_nudges
    .filter(n => n.coach_note)
    .map(n => {
      const risk = n.behavioral_risk_score ?? 5;
      return {
        id: `note-${n.user_id}-${n.analyzed_at}`,
        timestamp: new Date(n.analyzed_at).getTime(),
        type: risk > 7 ? 'WARNING' : risk < 3 ? 'SUCCESS' : 'INFO',
        note: n.coach_note,
      } satisfies CoachNote;
    });
}

function maxRiskScore(summary: DashboardSummary): number {
  const scores = summary.recent_nudges
    .map(n => n.behavioral_risk_score)
    .filter((s): s is number => s != null);
  return scores.length > 0 ? Math.max(...scores) : 5.0;
}

// ─────────────────────────────────────────────────────────────────────────────

export function TradingDashboard() {
  const subscription = useSubscriptionContext();

  const [riskScore, setRiskScore] = useState(5.0);
  const [biasAlerts, setBiasAlerts] = useState<BiasAlert[]>([]);
  const [coachNotes, setCoachNotes] = useState<CoachNote[]>([]);
  const [trades, setTrades] = useState<Trade[]>(mockTrades);
  const [showPreFlight, setShowPreFlight] = useState(false);
  const [pendingTrade, setPendingTrade] = useState<{ side: 'BUY' | 'SELL'; sentiment: number } | null>(null);
  const [selectedStock, setSelectedStock] = useState<SelectedStock>({
    ticker: 'AAPL',
    name: 'Apple Inc.',
    exchange: 'NASDAQ',
    price: 178.52
  });
  const [isFrozen, setIsFrozen] = useState(false);
  const [freezeTimeRemaining, setFreezeTimeRemaining] = useState(0);
  const [showTrialExpired, setShowTrialExpired] = useState(false);

  // ── Fetch dashboard summary on mount ────────────────────────────────────────
  const fetchDashboard = useCallback(async () => {
    try {
      const { data } = await api.get<DashboardSummary>('/spokes/neufin/dashboard-summary');
      setBiasAlerts(mapBiasAlerts(data));
      setCoachNotes(mapCoachNotes(data));
      setRiskScore(maxRiskScore(data));
    } catch {
      // Keep defaults if backend is unavailable
    }
  }, []);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  // ── Trade handlers ───────────────────────────────────────────────────────────

  const handleTradeRequest = (side: 'BUY' | 'SELL', sentiment: number) => {
    if (isFrozen) return;
    setPendingTrade({ side, sentiment });
    setShowPreFlight(true);
  };

  const handleConfirmTrade = async (thesis: string, sentiment: number) => {
    if (!pendingTrade || isFrozen) return;

    const executedPrice = selectedStock.price + (Math.random() - 0.5) * 2;
    const quantity = Math.floor(Math.random() * 100) + 10;
    const now = new Date().toISOString();

    const newTrade: Trade = {
      id: Date.now().toString(),
      timestamp: Date.now(),
      asset: selectedStock.ticker,
      side: pendingTrade.side,
      price: executedPrice,
      quantity,
      sentiment,
      primaryBias: sentiment > 0.8 ? 'FOMO' : sentiment < 0.3 ? 'FEAR' : 'NEUTRAL',
      userNote: thesis
    };

    setTrades(prev => [newTrade, ...prev]);

    const newRisk = Math.min(10, riskScore + (sentiment > 0.7 ? 0.5 : -0.2));
    setRiskScore(parseFloat(newRisk.toFixed(1)));

    setPendingTrade(null);

    // Submit to backend; refresh dashboard after profiler runs (~2s)
    try {
      await api.post('/spokes/neufin/trades', {
        user_id: USER_ID,
        asset: newTrade.asset,
        traded_at: now,
        price: executedPrice,
        sentiment_score: sentiment * 2 - 1, // convert [0,1] → [-1,1]
      });
      setTimeout(fetchDashboard, 2000);
    } catch {
      // Non-fatal: trade shown locally even if backend write fails
    }
  };

  const handleSelectTicker = (stock: SelectedStock | string) => {
    if (typeof stock === 'string') {
      const mockPrice = 100 + Math.random() * 500;
      setSelectedStock({
        ticker: stock,
        name: `${stock} Company`,
        exchange: 'NASDAQ',
        price: mockPrice
      });
    } else {
      setSelectedStock(stock);
    }
  };

  const handleActivateBreaker = () => {
    setIsFrozen(true);
    setFreezeTimeRemaining(300);

    const interval = setInterval(() => {
      setFreezeTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setIsFrozen(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleUpgradeClick = () => {
    if (subscription.checkoutUrl) {
      window.location.href = subscription.checkoutUrl;
    } else {
      setShowTrialExpired(true);
    }
  };

  return (
    <div className="h-screen w-screen bg-[#0B0E11] flex flex-col overflow-hidden">
      {/* Trial Banner — shown during active trial only */}
      {subscription.status === 'trial_active' && (
        <TrialBanner
          onUpgradeClick={handleUpgradeClick}
          daysRemaining={subscription.daysRemaining}
        />
      )}

      {/* Top Bar */}
      <Header
        currentPrice={selectedStock.price}
        priceChange={1.33}
        ticker={selectedStock.ticker}
      />

      {/* Main Content Area — scrollable on small screens */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Left Side: Chart + Entry Widget */}
        <div className="flex-1 flex flex-col gap-3 p-4 min-w-0 overflow-y-auto">
          {/* Ticker Search */}
          <div className="w-full max-w-md shrink-0">
            <TickerSearch
              onSelectTicker={handleSelectTicker}
              currentTicker={selectedStock.ticker}
            />
          </div>

          {/* Market Stats */}
          <div className="shrink-0">
            <MarketStats ticker={selectedStock.ticker} currentPrice={selectedStock.price} />
          </div>

          {/* Trading Chart */}
          <div className="flex-1 min-h-[280px]">
            <TradingChart ticker={selectedStock.ticker} currentPrice={selectedStock.price} />
          </div>

          {/* Bottom Row: Equity Curve + Trade Entry */}
          <div className="grid grid-cols-2 gap-4 h-56 shrink-0">
            <EquityCurve trades={trades} />
            <TradeEntry onTrade={handleTradeRequest} disabled={isFrozen} />
          </div>

          {/* Execution Dock */}
          <div className="h-56 shrink-0">
            <ExecutionDock trades={trades} />
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="w-72 shrink-0 flex flex-col gap-3 p-4 pl-0 overflow-y-auto">
          {/* Watchlist */}
          <div className="h-56 shrink-0">
            <Watchlist onSelectTicker={handleSelectTicker} />
          </div>

          {/* Emotional Breaker */}
          <div className="shrink-0">
            <EmotionalBreaker
              riskScore={riskScore}
              onActivate={handleActivateBreaker}
              isActive={isFrozen}
              remainingTime={freezeTimeRemaining}
            />
          </div>

          {/* Bias Terminal — wired to backend behavioral engine */}
          <div className="flex-1 min-h-[300px]">
            <BiasTerminal
              riskScore={riskScore}
              alerts={biasAlerts}
              coachNotes={coachNotes}
            />
          </div>
        </div>
      </div>

      {/* Pre-Flight Check Modal */}
      <PreFlightCheckModal
        isOpen={showPreFlight}
        onClose={() => {
          setShowPreFlight(false);
          setPendingTrade(null);
        }}
        onConfirm={handleConfirmTrade}
        tradeSide={pendingTrade?.side || 'BUY'}
        currentSentiment={pendingTrade?.sentiment || 0.5}
      />

      {/* Trial Expired Overlay (local fallback) */}
      {showTrialExpired && (
        <TrialExpiredOverlay
          onDismiss={() => setShowTrialExpired(false)}
          onUpgradeClick={handleUpgradeClick}
        />
      )}
    </div>
  );
}
