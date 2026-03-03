import { Sparkles, X } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';

interface TrialBannerProps {
  onUpgradeClick?: () => void;
  daysRemaining?: number | null;
}

export function TrialBanner({ onUpgradeClick, daysRemaining }: TrialBannerProps) {
  const [isVisible, setIsVisible] = useState(true);

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: 'auto', opacity: 1 }}
        exit={{ height: 0, opacity: 0 }}
        className="bg-gradient-to-r from-[#F59E0B]/10 via-[#8B5CF6]/10 to-[#F59E0B]/10 border-b border-[#F59E0B]/20 shrink-0"
      >
        <div className="flex items-center justify-center gap-3 px-6 py-2 relative">
          <Sparkles className="w-4 h-4 text-[#F59E0B]" />
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-gray-400">Trial ends in</span>
            <span className="text-white font-semibold">
              {daysRemaining != null ? `${daysRemaining} day${daysRemaining !== 1 ? 's' : ''}` : '4 days'}
            </span>
            <span className="text-gray-600">•</span>
            <button
              onClick={onUpgradeClick}
              className="text-[#F59E0B] hover:text-[#F59E0B]/80 underline underline-offset-2 transition-colors"
            >
              Upgrade to Pro
            </button>
            <span className="text-gray-500">to keep your AI Coach</span>
          </div>
          <button
            onClick={() => setIsVisible(false)}
            className="absolute right-4 p-1 hover:bg-white/5 rounded transition-colors"
            title="Dismiss"
          >
            <X className="w-3.5 h-3.5 text-gray-500" />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}