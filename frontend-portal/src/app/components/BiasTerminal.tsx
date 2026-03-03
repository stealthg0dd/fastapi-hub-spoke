import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AlertTriangle, TrendingUp, Brain, Activity } from 'lucide-react';
import { RiskGauge } from './RiskGauge';
import type { BiasAlert, CoachNote } from '../types/trading';

interface BiasTerminalProps {
  riskScore: number;
  alerts: BiasAlert[];
  coachNotes: CoachNote[];
}

export function BiasTerminal({ riskScore, alerts, coachNotes }: BiasTerminalProps) {
  const [liveNotes, setLiveNotes] = useState<CoachNote[]>([]);

  useEffect(() => {
    // Simulate live feed by adding notes one by one
    let index = 0;
    const interval = setInterval(() => {
      if (index < coachNotes.length) {
        setLiveNotes(prev => [coachNotes[index], ...prev]);
        index++;
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [coachNotes]);

  const getBiasIcon = (type: BiasAlert['type']) => {
    switch (type) {
      case 'ANCHORING': return '⚓';
      case 'FOMO': return '🔥';
      case 'LOSS_AVERSION': return '🛡️';
      case 'CONFIRMATION': return '✓';
      case 'RECENCY': return '⏱️';
    }
  };

  const getBiasColor = (severity: BiasAlert['severity']) => {
    switch (severity) {
      case 'HIGH': return { bg: 'bg-[#FF3B69]/10', border: 'border-[#FF3B69]', text: 'text-[#FF3B69]' };
      case 'MEDIUM': return { bg: 'bg-[#F59E0B]/10', border: 'border-[#F59E0B]', text: 'text-[#F59E0B]' };
      case 'LOW': return { bg: 'bg-[#6B7280]/10', border: 'border-[#6B7280]', text: 'text-[#6B7280]' };
    }
  };

  const getNoteIcon = (type: CoachNote['type']) => {
    switch (type) {
      case 'WARNING': return <AlertTriangle className="w-3 h-3" />;
      case 'INFO': return <Activity className="w-3 h-3" />;
      case 'SUCCESS': return <TrendingUp className="w-3 h-3" />;
    }
  };

  const getNoteColor = (type: CoachNote['type']) => {
    switch (type) {
      case 'WARNING': return 'text-[#F59E0B]';
      case 'INFO': return 'text-[#3B82F6]';
      case 'SUCCESS': return 'text-[#00C087]';
    }
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4 bg-[#0B0E11] border-l border-[#1A1D23]">
      {/* Header */}
      <div className="flex items-center gap-2 pb-2 border-b border-[#1A1D23]">
        <Brain className="w-5 h-5 text-[#F59E0B]" />
        <h2 className="text-sm font-mono text-white tracking-wider">BIAS TERMINAL</h2>
      </div>

      {/* Risk Gauge */}
      <RiskGauge score={riskScore} />

      {/* Active Bias Alerts */}
      <div className="flex flex-col gap-2">
        <div className="text-[10px] font-mono text-gray-500 tracking-wider">ACTIVE ALERTS</div>
        <div className="flex flex-col gap-2 max-h-[200px] overflow-y-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-gray-700">
          <AnimatePresence>
            {alerts.map((alert) => {
              const colors = getBiasColor(alert.severity);
              return (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className={`p-2 rounded border ${colors.bg} ${colors.border} ${colors.text}`}
                >
                  <div className="flex items-start gap-2">
                    <span className="text-base leading-none">{getBiasIcon(alert.type)}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-[10px] font-mono font-bold tracking-wider mb-0.5">
                        {alert.type}
                      </div>
                      <div className="text-[11px] leading-tight">
                        {alert.message}
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>

      {/* AI Coach Stream */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex items-center gap-2 mb-2">
          <div className="text-[10px] font-mono text-gray-500 tracking-wider">AI COACH STREAM</div>
          <motion.div
            className="w-1.5 h-1.5 rounded-full bg-[#00C087]"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        </div>
        <div className="flex-1 bg-[#0D1117] rounded border border-[#1A1D23] overflow-hidden">
          <div className="h-full overflow-y-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-gray-700 p-2 font-mono text-[11px] space-y-1">
            <AnimatePresence>
              {liveNotes.filter(note => note && note.id && note.timestamp).map((note) => (
                <motion.div
                  key={note.id}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="border-b border-[#1A1D23]/50 pb-1"
                >
                  <div className="flex items-start gap-2">
                    <span className="text-gray-600 tabular-nums shrink-0">
                      {new Date(note.timestamp).toLocaleTimeString('en-US', { 
                        hour12: false, 
                        hour: '2-digit', 
                        minute: '2-digit',
                        second: '2-digit'
                      })}
                    </span>
                    <span className={getNoteColor(note.type)}>
                      {getNoteIcon(note.type)}
                    </span>
                    <span className="text-gray-400 leading-tight">{note.note}</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}