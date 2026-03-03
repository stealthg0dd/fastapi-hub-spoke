import { useNavigate } from 'react-router';
import { ArrowLeft, TrendingUp, AlertTriangle, Activity } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// Mock data for dual-axis chart
const analyticsData = [
  { date: 'Jan 1', pnl: 0, riskScore: 5.2 },
  { date: 'Jan 8', pnl: 1200, riskScore: 6.1 },
  { date: 'Jan 15', pnl: 850, riskScore: 7.3 },
  { date: 'Jan 22', pnl: 2100, riskScore: 8.5 },
  { date: 'Jan 29', pnl: 1650, riskScore: 7.8 },
  { date: 'Feb 5', pnl: 3200, riskScore: 6.2 },
  { date: 'Feb 12', pnl: 2800, riskScore: 5.9 },
  { date: 'Feb 19', pnl: 4100, riskScore: 7.1 },
  { date: 'Feb 26', pnl: 3500, riskScore: 6.5 },
  { date: 'Mar 2', pnl: 4850, riskScore: 7.2 },
];

// Performance metrics
const metrics = [
  { label: 'Total PnL', value: '$4,850', change: '+18.5%', isPositive: true },
  { label: 'Avg Risk Score', value: '6.78', change: '-0.3', isPositive: true },
  { label: 'Win Rate', value: '64.2%', change: '+2.1%', isPositive: true },
  { label: 'Best Trade', value: '$850', change: 'Feb 19', isPositive: true },
];

export function Analytics() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#0B0E11] text-white">
      {/* Header */}
      <div className="bg-[#0D1117] border-b border-[#1A1D23] px-6 py-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-white/5 rounded transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </button>
          <div>
            <h1 className="text-lg font-mono text-white">Analytics Dashboard</h1>
            <p className="text-xs font-mono text-gray-500">Performance & Behavioral Risk Analysis</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto p-6">
        {/* Metrics Grid */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {metrics.map((metric, index) => (
            <div key={index} className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-4">
              <div className="text-xs font-mono text-gray-500 mb-1">{metric.label}</div>
              <div className="text-2xl font-mono text-white mb-1">{metric.value}</div>
              <div className={`text-xs font-mono ${metric.isPositive ? 'text-[#00C087]' : 'text-[#FF3B69]'}`}>
                {metric.change}
              </div>
            </div>
          ))}
        </div>

        {/* Main Chart */}
        <div className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-sm font-mono text-white mb-1">Portfolio PnL vs Behavioral Risk Score</h2>
              <p className="text-xs font-mono text-gray-500">Dual-axis correlation analysis</p>
            </div>
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#00C087]" />
                <span className="text-xs font-mono text-gray-400">Portfolio PnL ($)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#F59E0B]" />
                <span className="text-xs font-mono text-gray-400">Risk Score (0-10)</span>
              </div>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={analyticsData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1A1D23" />
              <XAxis 
                dataKey="date" 
                stroke="#6B7280"
                style={{ fontSize: '11px', fontFamily: 'monospace' }}
              />
              <YAxis 
                yAxisId="left"
                stroke="#00C087"
                style={{ fontSize: '11px', fontFamily: 'monospace' }}
                label={{ value: 'PnL ($)', angle: -90, position: 'insideLeft', style: { fill: '#00C087', fontSize: '11px' } }}
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                stroke="#F59E0B"
                domain={[0, 10]}
                style={{ fontSize: '11px', fontFamily: 'monospace' }}
                label={{ value: 'Risk Score', angle: 90, position: 'insideRight', style: { fill: '#F59E0B', fontSize: '11px' } }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0D1117',
                  border: '1px solid #1A1D23',
                  borderRadius: '8px',
                  fontFamily: 'monospace',
                  fontSize: '12px'
                }}
                labelStyle={{ color: '#9CA3AF' }}
                itemStyle={{ color: '#fff' }}
              />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="pnl" 
                stroke="#00C087" 
                strokeWidth={2}
                dot={{ fill: '#00C087', r: 4 }}
                activeDot={{ r: 6 }}
              />
              <Line 
                yAxisId="right"
                type="monotone" 
                dataKey="riskScore" 
                stroke="#F59E0B" 
                strokeWidth={2}
                dot={{ fill: '#F59E0B', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Insights */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-4">
            <div className="flex items-start gap-3">
              <TrendingUp className="w-5 h-5 text-[#00C087] mt-0.5" />
              <div>
                <h3 className="text-sm font-mono text-white mb-1">Positive Correlation</h3>
                <p className="text-xs font-mono text-gray-400 leading-relaxed">
                  Lower risk scores align with higher PnL periods. Your best trading occurs when behavioral risk is managed.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[#F59E0B] mt-0.5" />
              <div>
                <h3 className="text-sm font-mono text-white mb-1">Risk Spike Alert</h3>
                <p className="text-xs font-mono text-gray-400 leading-relaxed">
                  Jan 22 showed elevated risk (8.5) despite strong PnL. Consider position sizing during high-risk periods.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Activity className="w-5 h-5 text-[#8B5CF6] mt-0.5" />
              <div>
                <h3 className="text-sm font-mono text-white mb-1">Consistency Trend</h3>
                <p className="text-xs font-mono text-gray-400 leading-relaxed">
                  Recent weeks show stabilizing risk scores (6-7 range). Maintain current discipline for optimal results.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
