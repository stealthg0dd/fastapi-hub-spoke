import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  ArrowLeft, Link2, Upload, PlusCircle, X, RefreshCw,
  TrendingUp, TrendingDown, BarChart2, DollarSign, CheckCircle2
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { usePlaidLink } from 'react-plaid-link';
import { api, type PortfolioHolding } from '../../utils/api';
import { useVenture } from '../../context/venturecontext';
import { UploadPortfolio } from '../../components/UploadPortfolio';

interface Holding {
  ticker: string;
  name: string;
  shares: number;
  avgCost: number;
  currentPrice: number;
  sector: string;
}

type ConnectMethod = 'plaid' | 'csv' | 'manual' | null;

function mapHolding(h: PortfolioHolding): Holding {
  return {
    ticker: h.ticker,
    name: h.ticker,
    shares: h.quantity,
    avgCost: h.avg_price,
    currentPrice: h.avg_price, // real-time price not available; P&L shows cost basis
    sector: h.source === 'plaid' ? 'Plaid Import' : 'CSV Import',
  };
}

export function Portfolio() {
  const navigate = useNavigate();
  const { userId } = useVenture();
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState<ConnectMethod>(null);
  const [connected, setConnected] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [syncTime, setSyncTime] = useState<string | null>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);

  // ── Fetch holdings ─────────────────────────────────────────────────────────
  const fetchHoldings = useCallback(async () => {
    if (!userId) return;
    try {
      const { data } = await api.get<PortfolioHolding[]>(
        `/spokes/neufin/portfolio/holdings?user_id=${userId}`
      );
      setHoldings(data.map(mapHolding));
      if (data.length > 0) {
        setConnected(true);
        setSyncTime('just now');
      }
    } catch {
      setHoldings([]);
    }
  }, [userId]);

  useEffect(() => { fetchHoldings(); }, [fetchHoldings]);

  // ── Plaid Link token ────────────────────────────────────────────────────────
  useEffect(() => {
    if (selectedMethod !== 'plaid' || !userId) return;
    api
      .post<{ link_token: string; expiration: string }>(
        '/spokes/neufin/plaid/create-link-token',
        { user_id: userId }
      )
      .then(({ data }) => setLinkToken(data.link_token))
      .catch(() => setLinkToken(null));
  }, [selectedMethod]);

  const { open: openPlaid, ready: plaidReady } = usePlaidLink({
    token: linkToken ?? '',
    onSuccess: async (publicToken) => {
      try {
        await api.post('/spokes/neufin/plaid/exchange-token', {
          user_id: userId,
          public_token: publicToken,
        });
        setConnected(true);
        setShowConnectModal(false);
        setSelectedMethod(null);
        setLinkToken(null);
        await fetchHoldings();
        setSyncTime('just now');
      } catch {
        // Exchange failed — modal stays open
      }
    },
  });

  // ── CSV upload ──────────────────────────────────────────────────────────────
  const handleCsvChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!userId) return;
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('file', file);
    try {
      await api.post('/spokes/neufin/portfolio/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setConnected(true);
      setShowConnectModal(false);
      setSelectedMethod(null);
      await fetchHoldings();
      setSyncTime('just now');
    } catch {
      // Upload failed silently; user can retry
    }
    // Reset input so same file can be re-uploaded
    e.target.value = '';
  };

  // ── Sync handler ────────────────────────────────────────────────────────────
  const handleSync = async () => {
    setSyncing(true);
    await fetchHoldings();
    setSyncTime('just now');
    setTimeout(() => setSyncing(false), 500);
  };

  // ── Continue button action ──────────────────────────────────────────────────
  const handleContinue = () => {
    if (selectedMethod === 'plaid') {
      if (plaidReady) openPlaid();
    } else if (selectedMethod === 'csv') {
      csvInputRef.current?.click();
    } else if (selectedMethod === 'manual') {
      // Manual entry not yet implemented
      setShowConnectModal(false);
      setSelectedMethod(null);
    }
  };

  // ── Derived stats ──────────────────────────────────────────────────────────
  const totalValue = holdings.reduce((sum, h) => sum + h.shares * h.currentPrice, 0);
  const totalCost  = holdings.reduce((sum, h) => sum + h.shares * h.avgCost, 0);
  const totalPnL   = totalValue - totalCost;
  const totalPnLPct = totalCost > 0 ? (totalPnL / totalCost) * 100 : 0;

  const connectOptions = [
    {
      id: 'plaid' as ConnectMethod,
      icon: Link2,
      title: 'Connect Broker',
      sub: 'via Plaid',
      description: 'Securely link your brokerage account in seconds.',
      color: '#00C087',
    },
    {
      id: 'csv' as ConnectMethod,
      icon: Upload,
      title: 'Upload CSV',
      sub: 'Trade history',
      description: 'Import trades from any broker export file.',
      color: '#F59E0B',
    },
    {
      id: 'manual' as ConnectMethod,
      icon: PlusCircle,
      title: 'Add Manually',
      sub: 'Enter positions',
      description: 'Manually input your current holdings.',
      color: '#7C3AED',
    },
  ];

  return (
    <div className="min-h-screen bg-[#0B0E11] text-white">
      {/* Hidden CSV file input */}
      <input
        ref={csvInputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={handleCsvChange}
      />

      {/* Header */}
      <div className="bg-[#0D1117] border-b border-[#1A1D23] px-6 py-4 sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="p-2 hover:bg-white/5 rounded transition-colors">
              <ArrowLeft className="w-5 h-5 text-gray-400" />
            </button>
            <div>
              <h1 className="text-lg font-mono text-white">Portfolio Manager</h1>
              <p className="text-xs font-mono text-gray-500">Holdings & Performance</p>
            </div>
          </div>
          <button
            onClick={() => setShowConnectModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[#7C3AED]/20 border border-[#7C3AED]/40 rounded-lg text-xs font-mono text-[#7C3AED] hover:bg-[#7C3AED]/30 transition-colors"
          >
            <Link2 className="w-3.5 h-3.5" />
            Connect Portfolio
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-6 space-y-5">

        {/* Portfolio Health Bar */}
        <div className="bg-[#0D1117] border border-[#1A1D23] rounded-xl px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-[#00C087]' : 'bg-gray-600'} ${syncing ? 'animate-pulse' : ''}`} />
            <span className="text-xs font-mono text-gray-400">
              Sync Status:
              <span className="text-white ml-2">
                {syncing ? 'Syncing…' : connected ? `Last synced ${syncTime ?? 'recently'}` : 'Not connected'}
              </span>
            </span>
            {connected && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#00C087]/10 text-[#00C087] border border-[#00C087]/20">
                LIVE
              </span>
            )}
          </div>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-1.5 text-xs font-mono text-gray-500 hover:text-white transition-colors disabled:opacity-40"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-[#0D1117] border border-[#1A1D23] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="w-4 h-4 text-gray-600" />
              <span className="text-xs font-mono text-gray-500">Portfolio Value</span>
            </div>
            <div className="text-xl font-mono text-white">
              ${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div className="bg-[#0D1117] border border-[#1A1D23] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              {totalPnL >= 0
                ? <TrendingUp className="w-4 h-4 text-[#00C087]" />
                : <TrendingDown className="w-4 h-4 text-[#FF3B69]" />}
              <span className="text-xs font-mono text-gray-500">Total P&L</span>
            </div>
            <div className={`text-xl font-mono ${totalPnL >= 0 ? 'text-[#00C087]' : 'text-[#FF3B69]'}`}>
              {totalPnL >= 0 ? '+' : ''}${totalPnL.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              <span className="text-sm ml-2 opacity-70">
                ({totalPnLPct >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}%)
              </span>
            </div>
          </div>
          <div className="bg-[#0D1117] border border-[#1A1D23] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <BarChart2 className="w-4 h-4 text-gray-600" />
              <span className="text-xs font-mono text-gray-500">Positions</span>
            </div>
            <div className="text-xl font-mono text-white">{holdings.length}</div>
          </div>
        </div>

        {/* Holdings Table */}
        <div className="bg-[#0D1117] border border-[#1A1D23] rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-[#1A1D23] flex items-center justify-between">
            <h3 className="text-xs font-mono text-gray-400 tracking-wider">HOLDINGS</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#1A1D23]">
                  {['Ticker', 'Shares', 'Avg Cost', 'Current', 'Market Value', 'P&L', 'Sector'].map((h) => (
                    <th key={h} className="px-5 py-2.5 text-left text-[10px] font-mono text-gray-600 tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {holdings.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-8 text-center text-xs font-mono text-gray-600">
                      No holdings yet — connect your portfolio to get started
                    </td>
                  </tr>
                ) : (
                  holdings.map((holding, i) => {
                    const pnl = (holding.currentPrice - holding.avgCost) * holding.shares;
                    const pnlPct = holding.avgCost > 0
                      ? ((holding.currentPrice - holding.avgCost) / holding.avgCost) * 100
                      : 0;
                    const isPos = pnl >= 0;
                    return (
                      <tr key={`${holding.ticker}-${i}`} className="border-b border-[#1A1D23]/50 hover:bg-white/[0.02] transition-colors">
                        <td className="px-5 py-3">
                          <div className="text-sm font-mono text-white">{holding.ticker}</div>
                          <div className="text-[10px] font-mono text-gray-600">{holding.name}</div>
                        </td>
                        <td className="px-5 py-3 text-sm font-mono text-gray-300">{holding.shares}</td>
                        <td className="px-5 py-3 text-sm font-mono text-gray-300">${holding.avgCost.toFixed(2)}</td>
                        <td className="px-5 py-3 text-sm font-mono text-white">${holding.currentPrice.toFixed(2)}</td>
                        <td className="px-5 py-3 text-sm font-mono text-gray-300">
                          ${(holding.shares * holding.currentPrice).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="px-5 py-3">
                          <div className={`text-sm font-mono ${isPos ? 'text-[#00C087]' : 'text-[#FF3B69]'}`}>
                            {isPos ? '+' : ''}${Math.abs(pnl).toFixed(2)}
                          </div>
                          <div className={`text-[10px] font-mono ${isPos ? 'text-[#00C087]' : 'text-[#FF3B69]'}`}>
                            {isPos ? '+' : ''}{pnlPct.toFixed(2)}%
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1A1D23] text-gray-500">
                            {holding.sector}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Connect Modal */}
      <AnimatePresence>
        {showConnectModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center"
          >
            <div
              className="absolute inset-0 bg-[#0B0E11]/80 backdrop-blur-sm"
              onClick={() => { setShowConnectModal(false); setSelectedMethod(null); }}
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 10 }}
              className="relative bg-[#0D1117] border border-[#1A1D23] rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl"
            >
              <button
                onClick={() => { setShowConnectModal(false); setSelectedMethod(null); }}
                className="absolute top-4 right-4 p-1.5 hover:bg-white/5 rounded-lg transition-colors"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>

              <h2 className="text-base font-mono text-white mb-1">Add Your Portfolio</h2>
              <p className="text-xs font-mono text-gray-500 mb-5">Choose how to connect your holdings</p>

              <div className="space-y-3">
                {connectOptions.map((opt) => {
                  const Icon = opt.icon;
                  const isSelected = selectedMethod === opt.id;
                  return (
                    <button
                      key={opt.id}
                      onClick={() => setSelectedMethod(isSelected ? null : opt.id)}
                      className={`w-full flex items-center gap-4 p-4 rounded-xl border transition-all text-left ${
                        isSelected
                          ? 'border-opacity-60 bg-opacity-10'
                          : 'border-[#1A1D23] hover:border-[#2A2D33] hover:bg-white/[0.02]'
                      }`}
                      style={isSelected ? { borderColor: opt.color, backgroundColor: `${opt.color}12` } : {}}
                    >
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                        style={{ backgroundColor: `${opt.color}18`, border: `1px solid ${opt.color}30` }}
                      >
                        <Icon className="w-5 h-5" style={{ color: opt.color }} />
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-mono text-white">
                          {opt.title}
                          <span className="text-gray-500 ml-1.5">{opt.sub}</span>
                        </div>
                        <div className="text-xs font-mono text-gray-500 mt-0.5">{opt.description}</div>
                      </div>
                      {isSelected && <CheckCircle2 className="w-4 h-4 shrink-0" style={{ color: opt.color }} />}
                    </button>
                  );
                })}
              </div>

              {selectedMethod === 'plaid' && (
                <motion.button
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  onClick={handleContinue}
                  disabled={!plaidReady}
                  className="w-full mt-4 py-3 rounded-xl font-mono text-sm text-white transition-colors disabled:opacity-50"
                  style={{
                    backgroundColor: connectOptions.find(o => o.id === selectedMethod)?.color,
                  }}
                >
                  {plaidReady ? 'Continue with Plaid' : 'Loading…'}
                </motion.button>
              )}

              {selectedMethod === 'csv' && (
                <div className="mt-4">
                  <UploadPortfolio />
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
