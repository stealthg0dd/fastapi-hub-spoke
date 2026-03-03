import { useState, useEffect } from 'react';
import { ShieldAlert, Clock } from 'lucide-react';
import { motion } from 'motion/react';

interface EmotionalBreakerProps {
  riskScore: number;
  onActivate: () => void;
  isActive: boolean;
  remainingTime: number; // in seconds
}

export function EmotionalBreaker({ riskScore, onActivate, isActive, remainingTime }: EmotionalBreakerProps) {
  const shouldGlow = riskScore >= 9.0 && !isActive;
  const minutes = Math.floor(remainingTime / 60);
  const seconds = remainingTime % 60;

  return (
    <div className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <ShieldAlert className="w-4 h-4 text-[#FF3B69]" />
        <span className="text-xs font-mono text-gray-400 uppercase tracking-wider">Emotional Breaker</span>
      </div>

      <button
        onClick={onActivate}
        disabled={isActive}
        className={`w-full py-3 rounded-lg font-mono text-sm transition-all relative overflow-hidden ${
          isActive
            ? 'bg-[#1A1D23] text-gray-600 cursor-not-allowed'
            : shouldGlow
            ? 'bg-[#FF3B69] text-white hover:bg-[#FF3B69]/90 shadow-lg shadow-[#FF3B69]/50'
            : 'bg-[#0B0E11] border border-[#1A1D23] text-gray-400 hover:bg-white/5'
        }`}
      >
        {shouldGlow && !isActive && (
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
            animate={{
              x: ['-100%', '100%'],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        )}
        
        {isActive ? (
          <div className="flex items-center justify-center gap-2">
            <Clock className="w-4 h-4" />
            <span>FROZEN: {minutes}:{seconds.toString().padStart(2, '0')}</span>
          </div>
        ) : (
          <span>ACTIVATE KILL SWITCH</span>
        )}
      </button>

      {isActive && (
        <p className="text-[10px] font-mono text-gray-500 mt-2 text-center">
          Trading UI locked for discipline
        </p>
      )}

      {shouldGlow && !isActive && (
        <motion.p
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="text-[10px] font-mono text-[#FF3B69] mt-2 text-center"
        >
          ⚠ CRITICAL RISK LEVEL DETECTED
        </motion.p>
      )}

      {!isActive && !shouldGlow && (
        <p className="text-[10px] font-mono text-gray-600 mt-2 text-center">
          Activates at Risk Score ≥ 9.0
        </p>
      )}
    </div>
  );
}
