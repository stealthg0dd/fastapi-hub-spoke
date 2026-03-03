import { motion } from 'motion/react';

interface RiskGaugeProps {
  score: number; // 0-10
}

export function RiskGauge({ score }: RiskGaugeProps) {
  const percentage = (score / 10) * 100;
  const rotation = (percentage / 100) * 180 - 90; // -90 to 90 degrees
  
  const getColor = () => {
    if (score < 3) return '#00C087';
    if (score < 6) return '#F59E0B';
    if (score < 8) return '#FF8C42';
    return '#FF3B69';
  };

  const getLabel = () => {
    if (score < 3) return 'LOW';
    if (score < 6) return 'MODERATE';
    if (score < 8) return 'ELEVATED';
    return 'HIGH';
  };

  return (
    <div className="flex flex-col items-center gap-3 p-4 bg-[#0D1117] rounded-lg border border-[#1A1D23]">
      <div className="text-[10px] font-mono text-gray-500 tracking-wider">BEHAVIORAL RISK</div>
      
      {/* Gauge Arc */}
      <div className="relative w-32 h-16">
        <svg viewBox="0 0 120 60" className="w-full h-full">
          {/* Background Arc */}
          <path
            d="M 10 55 A 50 50 0 0 1 110 55"
            fill="none"
            stroke="#1A1D23"
            strokeWidth="8"
            strokeLinecap="round"
          />
          
          {/* Colored Arc */}
          <motion.path
            d="M 10 55 A 50 50 0 0 1 110 55"
            fill="none"
            stroke={getColor()}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray="157"
            strokeDashoffset={157 - (157 * percentage) / 100}
            initial={{ strokeDashoffset: 157 }}
            animate={{ strokeDashoffset: 157 - (157 * percentage) / 100 }}
            transition={{ duration: 1, ease: 'easeOut' }}
          />
          
          {/* Needle */}
          <motion.line
            x1="60"
            y1="55"
            x2="60"
            y2="15"
            stroke={getColor()}
            strokeWidth="2"
            strokeLinecap="round"
            initial={{ rotate: -90 }}
            animate={{ rotate: rotation }}
            transition={{ duration: 1, ease: 'easeOut' }}
            style={{ transformOrigin: '60px 55px' }}
          />
          
          {/* Center Dot */}
          <circle cx="60" cy="55" r="3" fill={getColor()} />
        </svg>
      </div>
      
      {/* Score Display */}
      <div className="flex items-baseline gap-2">
        <motion.div 
          className="text-3xl font-mono tabular-nums"
          style={{ color: getColor() }}
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          {score.toFixed(1)}
        </motion.div>
        <div className="text-xs font-mono text-gray-500">/10</div>
      </div>
      
      <div 
        className="text-[11px] font-mono px-3 py-1 rounded"
        style={{ 
          backgroundColor: `${getColor()}20`,
          color: getColor()
        }}
      >
        {getLabel()} RISK
      </div>
    </div>
  );
}
