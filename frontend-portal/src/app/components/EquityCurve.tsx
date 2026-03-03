import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, Activity } from 'lucide-react';
import type { Trade } from '../types/trading';

interface EquityCurveProps {
  trades: Trade[];
}

export function EquityCurve({ trades }: EquityCurveProps) {
  // Generate equity curve data from trades
  const generateEquityData = () => {
    if (trades.length === 0) {
      // Return mock data if no trades
      return [
        { timestamp: Date.now() - 86400000 * 30, balance: 10000, biasScore: 3.2 },
        { timestamp: Date.now() - 86400000 * 25, balance: 10500, biasScore: 4.1 },
        { timestamp: Date.now() - 86400000 * 20, balance: 11200, biasScore: 5.8 },
        { timestamp: Date.now() - 86400000 * 15, balance: 10800, biasScore: 7.2 },
        { timestamp: Date.now() - 86400000 * 10, balance: 11800, biasScore: 3.9 },
        { timestamp: Date.now() - 86400000 * 5, balance: 12400, biasScore: 4.5 },
        { timestamp: Date.now(), balance: 13100, biasScore: 5.1 },
      ];
    }

    let balance = 10000;
    const sortedTrades = [...trades].sort((a, b) => a.timestamp - b.timestamp);

    return sortedTrades.map((trade) => {
      // Simulate P&L
      const pnl = trade.side === 'BUY'
        ? (Math.random() - 0.4) * 500
        : (Math.random() - 0.4) * 500;

      balance += pnl;

      // Calculate bias score from sentiment (inverse correlation)
      const biasScore = trade.sentiment * 10;

      return {
        timestamp: trade.timestamp,
        balance: Math.round(balance),
        biasScore: parseFloat(biasScore.toFixed(1)),
        date: new Date(trade.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      };
    });
  };

  const data = generateEquityData();

  // Calculate correlation insight
  const calculateCorrelation = () => {
    if (data.length < 2) return null;

    const avgBias = data.reduce((sum, d) => sum + d.biasScore, 0) / data.length;
    const balanceChange = ((data[data.length - 1].balance - data[0].balance) / data[0].balance) * 100;

    return {
      avgBias: avgBias.toFixed(1),
      balanceChange: balanceChange.toFixed(1),
      correlation: avgBias > 6 && balanceChange < 0 ? 'NEGATIVE' : avgBias < 4 && balanceChange > 0 ? 'POSITIVE' : 'NEUTRAL'
    };
  };

  const correlation = calculateCorrelation();

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-3 shadow-xl">
          <p className="text-[10px] font-mono text-gray-500 mb-2">{payload[0].payload.date}</p>
          <div className="space-y-1">
            <p className="text-xs font-mono text-white">
              Balance: <span className="text-[#00C087]">${payload[0].value.toLocaleString()}</span>
            </p>
            <p className="text-xs font-mono text-white">
              Bias Score: <span className="text-[#F59E0B]">{payload[1].value}</span>
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-[#0D1117] rounded-lg border border-[#1A1D23] p-4 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#F59E0B]" />
          <h3 className="text-xs font-mono text-gray-400 tracking-wider">EQUITY CURVE & BIAS OVERLAY</h3>
        </div>
        
        {correlation && (
          <div className="flex items-center gap-2 text-[10px] font-mono">
            <span className="text-gray-600">Correlation:</span>
            <span className={`px-2 py-0.5 rounded ${
              correlation.correlation === 'NEGATIVE' 
                ? 'bg-[#FF3B69]/20 text-[#FF3B69] border border-[#FF3B69]'
                : correlation.correlation === 'POSITIVE'
                ? 'bg-[#00C087]/20 text-[#00C087] border border-[#00C087]'
                : 'bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]'
            }`}>
              {correlation.correlation}
            </span>
          </div>
        )}
      </div>

      {/* Insight Box */}
      {correlation && (
        <div className="mb-4 bg-[#0B0E11] border border-[#1A1D23] rounded p-3">
          <div className="flex items-start gap-2">
            <TrendingUp className="w-4 h-4 text-[#F59E0B] mt-0.5 shrink-0" />
            <p className="text-xs font-mono text-gray-300 leading-relaxed">
              When your <span className="text-[#F59E0B]">Average Bias Score</span> is{' '}
              <span className="text-[#F59E0B] font-semibold">{correlation.avgBias}</span>, your profit is{' '}
              <span className={parseFloat(correlation.balanceChange) >= 0 ? 'text-[#00C087]' : 'text-[#FF3B69]'}>
                {parseFloat(correlation.balanceChange) >= 0 ? '+' : ''}{correlation.balanceChange}%
              </span>
              {parseFloat(correlation.avgBias) > 6 && parseFloat(correlation.balanceChange) < 0 && (
                <span className="text-[#FF3B69]"> ⚠️ High bias correlates with losses</span>
              )}
            </p>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A1D23" />
            <XAxis
              dataKey="date"
              stroke="#6B7280"
              style={{ fontSize: '10px', fontFamily: 'monospace' }}
              tick={{ fill: '#6B7280' }}
            />
            <YAxis
              yAxisId="left"
              stroke="#00C087"
              style={{ fontSize: '10px', fontFamily: 'monospace' }}
              tick={{ fill: '#00C087' }}
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#F59E0B"
              style={{ fontSize: '10px', fontFamily: 'monospace' }}
              tick={{ fill: '#F59E0B' }}
              domain={[0, 10]}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace' }}
              iconType="line"
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="balance"
              stroke="#00C087"
              strokeWidth={2}
              dot={{ r: 3, fill: '#00C087' }}
              name="Account Balance"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="biasScore"
              stroke="#F59E0B"
              strokeWidth={2}
              dot={{ r: 3, fill: '#F59E0B' }}
              strokeDasharray="5 5"
              name="Avg Bias Score"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Stats Footer */}
      <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-[#1A1D23]">
        <div>
          <div className="text-[10px] font-mono text-gray-600 mb-0.5">STARTING</div>
          <div className="text-sm font-mono text-white">${data[0]?.balance.toLocaleString() || '10,000'}</div>
        </div>
        <div>
          <div className="text-[10px] font-mono text-gray-600 mb-0.5">CURRENT</div>
          <div className="text-sm font-mono text-[#00C087]">
            ${data[data.length - 1]?.balance.toLocaleString() || '10,000'}
          </div>
        </div>
        <div>
          <div className="text-[10px] font-mono text-gray-600 mb-0.5">P&L</div>
          <div className={`text-sm font-mono ${correlation && parseFloat(correlation.balanceChange) >= 0 ? 'text-[#00C087]' : 'text-[#FF3B69]'}`}>
            {correlation ? (parseFloat(correlation.balanceChange) >= 0 ? '+' : '') + correlation.balanceChange + '%' : '0%'}
          </div>
        </div>
      </div>
    </div>
  );
}
