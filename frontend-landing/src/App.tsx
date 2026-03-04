import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { HelmetProvider } from 'react-helmet-async';
import { Layout } from "./components/Layout";
import { PerformanceOptimizer } from "./components/PerformanceOptimizer";
import { Home } from "./pages/Home";
import { Dashboard } from "./pages/Dashboard";
import { About } from "./pages/About";
import { Pricing } from "./pages/Pricing";
import { UserJourney } from "./pages/UserJourney";
import { Login } from "./pages/Login";
import { Signup } from "./pages/Signup";
import { AuthCallback } from "./pages/AuthCallback";
import { PortfolioSetup } from "./pages/PortfolioSetup";
import { UserDashboard } from "./pages/UserDashboard";
import { AuthFeatures } from "./pages/AuthFeatures";
import { Demo } from "./pages/Demo";
import { ApiLanding } from "./pages/ApiLanding";
import { CustomerPortal } from "./pages/CustomerPortal";
import { CustomerPane } from "./pages/CustomerPane";
import { CustomerAuthCallback } from "./pages/CustomerAuthCallback";
import { Toaster } from "./components/ui/sonner";

export default function App() {
  return (
    <HelmetProvider>
      <Toaster richColors position="top-right" />
      <PerformanceOptimizer />
      <Router>
        <Routes>
        {/* Public routes without layout */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/auth/callback" element={<AuthCallback />} />

        {/* Customer Portal Routes */}
        <Route path="/customer-portal" element={<CustomerPortal />} />
        <Route path="/customer-auth-callback" element={<CustomerAuthCallback />} />
        <Route path="/customer-pane" element={<CustomerPane />} />

        {/* Protected routes without layout */}
        <Route path="/portfolio-setup" element={<PortfolioSetup />} />
        <Route path="/user-dashboard" element={<UserDashboard />} />

        {/* Main public routes with layout */}
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/demo" element={<Demo />} />
          <Route path="/api" element={<ApiLanding />} />
        </Route>

        {/* Redirect any unknown routes to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
    </HelmetProvider>
  );
}