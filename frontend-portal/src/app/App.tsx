import { RouterProvider } from 'react-router';
import { router } from './routes';
import { SubscriptionContext, useSubscription } from './hooks/useSubscription';
import { TrialExpiredOverlay } from './components/TrialExpiredOverlay';
import { Toaster } from './components/ui/sonner';

function AppWithSubscription() {
  const subscription = useSubscription();

  const handleUpgradeClick = () => {
    if (subscription.checkoutUrl) {
      window.location.href = subscription.checkoutUrl;
    }
  };

  return (
    <SubscriptionContext.Provider value={subscription}>
      <Toaster richColors position="top-right" />
      <RouterProvider router={router} />
      {subscription.status === 'checkout_required' && (
        <TrialExpiredOverlay
          onUpgradeClick={handleUpgradeClick}
          opportunitiesCount={subscription.opportunitiesCount}
        />
      )}
    </SubscriptionContext.Provider>
  );
}

export default function App() {
  return <AppWithSubscription />;
}
