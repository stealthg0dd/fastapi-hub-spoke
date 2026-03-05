import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../../utils/api';
import { useVenture } from '../../context/venturecontext';

export interface SubscriptionState {
  status: 'loading' | 'trial_active' | 'checkout_required' | 'already_subscribed';
  trialEndsAt: Date | null;
  checkoutUrl: string | null;
  daysRemaining: number | null;
  hoursRemaining: number | null;
  opportunitiesCount: number;
}

const defaultState: SubscriptionState = {
  status: 'loading',
  trialEndsAt: null,
  checkoutUrl: null,
  daysRemaining: null,
  hoursRemaining: null,
  opportunitiesCount: 0,
};

export const SubscriptionContext = createContext<SubscriptionState>(defaultState);

interface TrialStatusResponse {
  status: 'trial_active' | 'checkout_required' | 'already_subscribed';
  trial_ends_at?: string;
  days_remaining?: number;
  hours_remaining?: number;
  opportunities_count?: number;
}

interface CheckoutResponse {
  status: string;
  checkout_url?: string;
}

const STRIPE_BILLING_URL = 'https://billing.stripe.com/p/login/test_eVq3cvbpM9p5dhp8mg9k400';

export function useSubscription(): SubscriptionState {
  const [state, setState] = useState<SubscriptionState>(defaultState);
  const { userId } = useVenture();

  useEffect(() => {
    let cancelled = false;

    async function fetchStatus() {
      try {
        if (!userId) {
          return;
        }

        // Step 1: fast read-only status check — no Stripe session created
        const { data } = await api.get<TrialStatusResponse>(
          '/spokes/neufin/trial-status',
          { params: { user_id: userId } },
        );

        if (cancelled) return;

        const trialEndsAt = data.trial_ends_at ? new Date(data.trial_ends_at) : null;

        if (data.status === 'already_subscribed') {
          setState({ ...defaultState, status: 'already_subscribed', trialEndsAt });
          return;
        }

        if (data.status === 'trial_active') {
          setState({
            status: 'trial_active',
            trialEndsAt,
            checkoutUrl: STRIPE_BILLING_URL,
            daysRemaining: data.days_remaining ?? null,
            hoursRemaining: data.hours_remaining ?? null,
            opportunitiesCount: data.opportunities_count ?? 0,
          });
          return;
        }

        // Trial expired — get a live Stripe checkout URL
        let checkoutUrl = STRIPE_BILLING_URL;
        try {
          const { data: checkoutData } = await api.post<CheckoutResponse>(
            '/spokes/neufin/billing/create-checkout-session',
            {
              user_id: userId,
              success_url: `${window.location.origin}/billing/success`,
              cancel_url: `${window.location.origin}/billing/cancel`,
            },
          );
          if (checkoutData.checkout_url) checkoutUrl = checkoutData.checkout_url;
        } catch {
          // Fall back to the Stripe billing portal URL
        }

        if (!cancelled) {
          setState({
            status: 'checkout_required',
            trialEndsAt,
            checkoutUrl,
            daysRemaining: 0,
            hoursRemaining: 0,
            opportunitiesCount: data.opportunities_count ?? 0,
          });
        }
      } catch {
        // Network error — fail open so users are never hard-blocked
        if (!cancelled) setState({ ...defaultState, status: 'trial_active' });
      }
    }

    fetchStatus();
    return () => { cancelled = true; };
  }, []);

  return state;
}

export function useSubscriptionContext(): SubscriptionState {
  return useContext(SubscriptionContext);
}
