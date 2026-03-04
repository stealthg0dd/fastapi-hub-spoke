import { Navigate } from 'react-router-dom';

/**
 * CustomerPortal — entry point for the "Customer Login" nav button.
 *
 * If VITE_PORTAL_URL is set to a separate origin (e.g. http://localhost:3001),
 * hard-navigate there.  Otherwise redirect to /login so the user can sign in
 * with Google OAuth; AuthCallback will forward them to /customer-pane.
 */
const PORTAL_URL = import.meta.env.VITE_PORTAL_URL as string | undefined;

export function CustomerPortal() {
  if (PORTAL_URL) {
    window.location.replace(PORTAL_URL);
    return null;
  }

  return <Navigate to="/login" replace />;
}
