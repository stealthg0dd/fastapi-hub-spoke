import { TrendingUp, TrendingDown, DollarSign, BarChart3, Percent, Database } from 'lucide-react';
import { getMarketStatus } from '../utils/mockData';

interface MarketStatsProps {
  className?: string;
  ticker?: string;
  currentPrice?: number;
}

export function MarketStats({ className = '', ticker = 'AAPL', currentPrice = 178.52 }: MarketStatsProps) {
  const marketStatus = getMarketStatus();
  
  // Mock data - in production this would come from API
  const stats = [
    {
      label: 'DAY HIGH',
      value: `$${(currentPrice * 1.018).toFixed(2)}`,
      icon: TrendingUp,
      color: 'text-[#00C087]'
    },
    {
      label: 'DAY LOW',
      value: `$${(currentPrice * 0.992).toFixed(2)}`,
      icon: TrendingDown,
      color: 'text-[#FF3B69]'
    },
    {
      label: 'P/E RATIO',
      value: '28.45',
      icon: BarChart3,
      color: 'text-[#F59E0B]'
    },
    {
      label: 'DIV YIELD',
      value: '0.52%',
      icon: Percent,
      color: 'text-blue-400'
    },
    {
      label: 'DAY VOL',
      value: '52.4M',
      icon: DollarSign,
      color: 'text-purple-400'
    },
    {
      label: 'MKT CAP',
      value: '$2.74T',
      icon: DollarSign,
      color: 'text-emerald-400'
    }
  ];

  const getMarketStatusBadge = () => {
    const badges = {
      OPEN: { text: 'MARKET OPEN', color: 'bg-[#00C087]/20 text-[#00C087] border-[#00C087]' },
      PRE_MARKET: { text: 'PRE-MARKET', color: 'bg-[#F59E0B]/20 text-[#F59E0B] border-[#F59E0B]' },
      POST_MARKET: { text: 'POST-MARKET', color: 'bg-[#8B5CF6]/20 text-[#8B5CF6] border-[#8B5CF6]' },
      CLOSED: { text: 'MARKET CLOSED', color: 'bg-[#6B7280]/20 text-[#6B7280] border-[#6B7280]' }
    };
    return badges[marketStatus];
  };

  const badge = getMarketStatusBadge();

  return (
    <div className={className}>
      {/* Market Status & Data Source */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-mono px-2 py-1 rounded border ${badge.color}`}>
            {badge.text}
          </span>
          {(marketStatus === 'PRE_MARKET' || marketStatus === 'POST_MARKET') && (
            <span className="text-[10px] font-mono px-2 py-1 rounded border bg-[#1A1D23] text-gray-500 border-[#1A1D23]">
              EXTENDED HOURS
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#0D1117] border border-[#1A1D23]">
          <Database className="w-3 h-3 text-gray-500" />
          <span className="text-[9px] font-mono text-gray-500">Data via Finnhub</span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-6 gap-3">
        {stats.map((stat, idx) => (
          <div
            key={idx}
            className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-3 hover:border-[#F59E0B]/30 transition-colors"
          >
            <div className="flex items-center gap-2 mb-1">
              <stat.icon className={`w-3.5 h-3.5 ${stat.color}`} />
              <div className="text-[9px] font-mono text-gray-500 tracking-wider">
                {stat.label}
              </div>
            </div>
            <div className="text-sm font-mono text-white tabular-nums">
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
