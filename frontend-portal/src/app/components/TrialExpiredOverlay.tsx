import { Sparkles, Brain, TrendingUp, BarChart3, Zap } from 'lucide-react';
import { motion } from 'motion/react';

interface TrialExpiredOverlayProps {
  onUpgradeClick?: () => void;
  opportunitiesCount?: number;
}

export function TrialExpiredOverlay({
  onUpgradeClick,
  opportunitiesCount = 7,
}: TrialExpiredOverlayProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Animated blurred backdrop */}
      <motion.div
        className="absolute inset-0 bg-[#0B0E11]/85 backdrop-blur-md"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4 }}
      />

      {/* Card */}
      <motion.div
        className="relative bg-[#0D1117] border border-[#7C3AED]/40 rounded-2xl p-8 w-full max-w-lg mx-4 shadow-2xl shadow-[#7C3AED]/20"
        initial={{ opacity: 0, scale: 0.92, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        {/* Neural Twin icon with pulse */}
        <div className="flex justify-center mb-5">
          <motion.div
            className="w-16 h-16 rounded-full bg-[#7C3AED]/15 border border-[#7C3AED]/40 flex items-center justify-center"
            animate={{ boxShadow: ['0 0 0px #7C3AED44', '0 0 24px #7C3AED66', '0 0 0px #7C3AED44'] }}
            transition={{ duration: 2.5, repeat: Infinity }}
          >
            <Brain className="w-7 h-7 text-[#7C3AED]" />
          </motion.div>
        </div>

        {/* Neufin Twin message */}
        <div className="text-center mb-6">
          <p className="text-xs font-mono text-[#7C3AED] uppercase tracking-widest mb-2">
            Neufin Neural Twin · Agentic Interception
          </p>
          <h2 className="text-xl font-mono text-white mb-4 leading-snug">
            I have analyzed your first 7 days of data and identified{' '}
            <motion.span
              className="text-[#7C3AED]"
              animate={{ opacity: [1, 0.6, 1] }}
              transition={{ duration: 1.8, repeat: Infinity }}
            >
              {opportunitiesCount} optimization opportunities.
            </motion.span>
          </h2>
          <p className="text-sm font-mono text-gray-400 leading-relaxed">
            To continue our partnership and execute these strategies, please activate your
            premium access. Your Neural Twin is ready to deploy.
          </p>
        </div>

        {/* Features */}
        <div className="bg-[#0B0E11] border border-[#1A1D23] rounded-xl p-4 mb-6 space-y-2.5">
          {[
            { icon: Zap,        label: 'Unlimited AI Behavioral Coach insights' },
            { icon: TrendingUp, label: 'Real-time bias detection & nudges' },
            { icon: BarChart3,  label: 'Emotional Breaker kill switch' },
            { icon: Sparkles,   label: 'Advanced PnL & alpha analytics' },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-2.5">
              <Icon className="w-3.5 h-3.5 text-[#7C3AED] shrink-0" />
              <span className="text-xs font-mono text-gray-300">{label}</span>
            </div>
          ))}
        </div>

        {/* CTA */}
        <motion.button
          onClick={onUpgradeClick}
          className="w-full py-3.5 rounded-xl font-mono text-sm text-white bg-[#7C3AED] hover:bg-[#6D28D9] transition-colors flex items-center justify-center gap-2 shadow-lg shadow-[#7C3AED]/30"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Sparkles className="w-4 h-4" />
          Activate Premium Access
        </motion.button>

        <p className="text-center text-[10px] font-mono text-gray-600 mt-3">
          Cancel anytime · Secure checkout via Stripe
        </p>
      </motion.div>
    </div>
  );
}
