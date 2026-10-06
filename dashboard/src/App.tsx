import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { CampaignsPage } from "./pages/CampaignsPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { PublishersPage } from "./pages/PublishersPage";
import { VerifyMobilePage } from "./pages/VerifyMobilePage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { PaymentsPage } from "./pages/PaymentsPage";
import { AdvertiserPaymentsPage } from "./pages/AdvertiserPaymentsPage";
import { AdminAdvertisersPage } from "./pages/AdminAdvertisersPage";
import { AdminSlotsPage } from "./pages/AdminSlotsPage";
import { api } from "./lib/api";

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem("access_token");
  return token ? children : <Navigate to="/login" replace />;
}

function RequireAdmin({ children }: { children: JSX.Element }) {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  useEffect(() => {
    api.me().then((user) => setIsAdmin((user as { role?: string }).role === "admin")).catch(() => setIsAdmin(false));
  }, []);
  if (isAdmin === null) return <div className="p-6 text-sm text-neutral-content">Checking access…</div>;
  return isAdmin ? children : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/verify" element={<VerifyMobilePage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <AnalyticsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/campaigns"
          element={
            <RequireAuth>
              <CampaignsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/publishers"
          element={
            <RequireAuth>
              <PublishersPage />
            </RequireAuth>
          }
        />
        <Route path="/approvals" element={<RequireAuth><ApprovalsPage /></RequireAuth>} />
        <Route path="/payments" element={<RequireAuth><AdvertiserPaymentsPage /></RequireAuth>} />
        <Route path="/payouts" element={<RequireAuth><PaymentsPage /></RequireAuth>} />
        <Route path="/manage-advertiser" element={<RequireAuth><RequireAdmin><AdminAdvertisersPage /></RequireAdmin></RequireAuth>} />
        <Route path="/manage-publisher" element={<RequireAuth><RequireAdmin><PublishersPage /></RequireAdmin></RequireAuth>} />
        <Route path="/manage-campaign" element={<RequireAuth><RequireAdmin><CampaignsPage /></RequireAdmin></RequireAuth>} />
        <Route path="/manage-slots" element={<RequireAuth><RequireAdmin><AdminSlotsPage /></RequireAdmin></RequireAuth>} />
      </Routes>
    </BrowserRouter>
  );
}
