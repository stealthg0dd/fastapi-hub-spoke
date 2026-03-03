import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';

/**
 * CustomerPortal — redirect gate.
 *
 * Dev:  VITE_PORTAL_URL=http://localhost:3001  → hard-navigates to the
 *       Vite dev server running frontend-portal.
 *
 * Prod: VITE_PORTAL_URL is empty → hard-navigates to /customer-portal on
 *       the same origin so Vercel routing serves frontend-portal/dist.
 */
const PORTAL_URL = import.meta.env.VITE_PORTAL_URL || '/customer-portal';

export function CustomerPortal() {
  useEffect(() => {
    window.location.replace(PORTAL_URL);
  }, []);

  return (
    <div className="min-h-screen bg-background dark flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin text-purple-500 mx-auto mb-4" />
        <h2 className="text-2xl mb-2">Loading Customer Portal…</h2>
        <p className="text-muted-foreground">You will be redirected automatically.</p>
      </div>
    </div>
  );
}
