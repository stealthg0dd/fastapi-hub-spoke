import { motion } from 'motion/react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import type { Trade } from '../types/trading';
import { calculatePnL } from '../utils/mockData';

interface ExecutionDockProps {
  trades: Trade[];
}

export function ExecutionDock({ trades }: ExecutionDockProps) {
  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getSentimentColor = (sentiment: number) => {
    if (sentiment >= 0.7) return '#FF3B69';
    if (sentiment >= 0.4) return '#F59E0B';
    return '#00C087';
  };

  const getSentimentLabel = (sentiment: number) => {
    if (sentiment >= 0.9) return 'EXTREME GREED';
    if (sentiment >= 0.7) return 'GREED';
    if (sentiment >= 0.4) return 'NEUTRAL';
    if (sentiment >= 0.2) return 'FEAR';
    return 'EXTREME FEAR';
  };

  // Calculate estimated PnL (mock exit price for display)
  const getEstimatedPnL = (trade: Trade) => {
    const mockExitPrice = trade.price + (Math.random() - 0.5) * 5;
    return calculatePnL(trade.quantity, trade.price, mockExitPrice, trade.side);
  };

  return (
    <div className="bg-[#0D1117] rounded-lg border border-[#1A1D23] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-2 border-b border-[#1A1D23] flex items-center justify-between">
        <div className="text-xs font-mono text-gray-400 tracking-wider">EXECUTION HISTORY</div>
        <div className="text-[10px] font-mono text-gray-600">{trades.length} TRADES</div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#1A1D23] text-[10px] font-mono text-gray-500">
              <th className="text-left px-4 py-2 font-normal">TIME</th>
              <th className="text-left px-4 py-2 font-normal">SYMBOL</th>
              <th className="text-left px-4 py-2 font-normal">SIDE</th>
              <th className="text-right px-4 py-2 font-normal">PRICE</th>
              <th className="text-right px-4 py-2 font-normal">SHARES</th>
              <th className="text-right px-4 py-2 font-normal">EST. P&L</th>
              <th className="text-center px-4 py-2 font-normal">SENTIMENT</th>
              <th className="text-left px-4 py-2 font-normal">PRIMARY BIAS</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, idx) => {
              const pnl = getEstimatedPnL(trade);
              const isPnlPositive = pnl > 0;
              
              return (
                <motion.tr
                  key={trade.id}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="border-b border-[#1A1D23]/50 hover:bg-white/5 transition-colors"
                >
                  <td className="px-4 py-2.5 text-[11px] font-mono text-gray-500 tabular-nums">
                    {formatTime(trade.timestamp)}
                  </td>
                  <td className="px-4 py-2.5 text-[11px] font-mono text-white">
                    {trade.asset}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-1.5">
                      {trade.side === 'BUY' ? (
                        <>
                          <ArrowUpRight className="w-3.5 h-3.5 text-[#00C087]" />
                          <span className="text-[11px] font-mono text-[#00C087]">BUY</span>
                        </>
                      ) : (
                        <>
                          <ArrowDownRight className="w-3.5 h-3.5 text-[#FF3B69]" />
                          <span className="text-[11px] font-mono text-[#FF3B69]">SELL</span>
                        </>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-[11px] font-mono text-white text-right tabular-nums">
                    ${trade.price.toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5 text-[11px] font-mono text-gray-400 text-right tabular-nums">
                    {trade.quantity}
                  </td>
                  <td className="px-4 py-2.5 text-[11px] font-mono text-right tabular-nums">
                    <span className={isPnlPositive ? 'text-[#00C087]' : 'text-[#FF3B69]'}>
                      {isPnlPositive ? '+' : ''}${pnl.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-col items-center gap-1">
                      <div 
                        className="text-[10px] font-mono px-2 py-0.5 rounded whitespace-nowrap"
                        style={{
                          backgroundColor: `${getSentimentColor(trade.sentiment)}20`,
                          color: getSentimentColor(trade.sentiment)
                        }}
                      >
                        {getSentimentLabel(trade.sentiment)}
                      </div>
                      <div className="flex items-center gap-0.5">
                        {Array.from({ length: 5 }).map((_, i) => (
                          <div
                            key={i}
                            className="w-1 h-2 rounded-sm"
                            style={{
                              backgroundColor: i < trade.sentiment * 5 
                                ? getSentimentColor(trade.sentiment)
                                : '#1A1D23'
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <span 
                      className="text-[10px] font-mono px-2 py-1 rounded bg-gray-800/50 text-gray-400 border border-gray-700"
                    >
                      {trade.primaryBias}
                    </span>
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}