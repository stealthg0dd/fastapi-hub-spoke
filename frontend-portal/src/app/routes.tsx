import { createBrowserRouter } from "react-router";
import { TradingDashboard } from "./pages/TradingDashboard";
import { Settings } from "./pages/Settings";
import { Analytics } from "./pages/Analytics";
import { Portfolio } from "./pages/Portfolio";

// In production, Vite sets BASE_URL to /portal/ (from vite.config.ts base).
// createBrowserRouter needs this so it strips /portal from the URL before matching routes.
export const router = createBrowserRouter(
  [
    {
      path: "/",
      Component: TradingDashboard,
    },
    {
      path: "/settings",
      Component: Settings,
    },
    {
      path: "/analytics",
      Component: Analytics,
    },
    {
      path: "/portfolio",
      Component: Portfolio,
    },
  ],
  { basename: import.meta.env.BASE_URL },
);
