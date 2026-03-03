/**
 * TrialGuard — wraps any page and injects trial-awareness UI.
 *
 * • trial_active    → renders children + a sticky countdown timer bar at the top
 * • checkout_required → renders the Agentic Interception full-screen overlay
 * • already_subscribed / loading → renders children unchanged
 */
import { Clock, Sparkles } from 'lucide-react';
import { motion } from 'motion/react';
import type { ReactNode } from 'react';
import { useSubscriptionContext } from '../hooks/useSubscription';
import { TrialExpiredOverlay } from './TrialExpiredOverlay';

interface TrialGuardProps {
  children: ReactNode;
}

function TrialCountdownBar() {
  const { daysRemaining, hoursRemaining, checkoutUrl } = useSubscriptionContext();

  const handleUpgrade = () => {
    if (checkoutUrl) window.location.href = checkoutUrl;
  };

  const timeLabel =
    daysRemaining != null && daysRemaining > 0
      ? `${daysRemaining}d ${hoursRemaining ?? 0}h remaining`
      : hoursRemaining != null && hoursRemaining > 0
        ? `${hoursRemaining}h remaining`
        : 'Trial ending soon';

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      className="w-full bg-gradient-to-r from-[#F59E0B]/10 via-[#8B5CF6]/10 to-[#F59E0B]/10 border-b border-[#F59E0B]/20 shrink-0"
    >
      <div className="flex items-center justify-center gap-3 px-6 py-2">
        <motion.div
          animate={{ rotate: [0, 15, -15, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        >
          <Clock className="w-3.5 h-3.5 text-[#F59E0B]" />
        </motion.div>
        <span className="text-xs font-mono text-gray-400">Free trial —</span>
        <span className="text-xs font-mono text-white font-semibold">{timeLabel}</span>
        <span className="text-gray-600 text-xs">·</span>
        <button
          onClick={handleUpgrade}
          className="flex items-center gap-1 text-xs font-mono text-[#F59E0B] hover:text-[#F59E0B]/80 underline underline-offset-2 transition-colors"
        >
          <Sparkles className="w-3 h-3" />
          Upgrade to Pro
        </button>
      </div>
    </motion.div>
  );
}

export function TrialGuard({ children }: TrialGuardProps) {
  const { status, checkoutUrl, opportunitiesCount } = useSubscriptionContext();

  const handleUpgrade = () => {
    if (checkoutUrl) window.location.href = checkoutUrl;
  };

  if (status === 'checkout_required') {
    return (
      <>
        {children}
        <TrialExpiredOverlay
          onUpgradeClick={handleUpgrade}
          opportunitiesCount={opportunitiesCount}
        />
      </>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {status === 'trial_active' && <TrialCountdownBar />}
      {children}
    </div>
  );
}
