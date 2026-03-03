import { createBrowserRouter } from "react-router";
import { TradingDashboard } from "./pages/TradingDashboard";
import { Settings } from "./pages/Settings";
import { Analytics } from "./pages/Analytics";
import { Portfolio } from "./pages/Portfolio";

export const router = createBrowserRouter([
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
]);