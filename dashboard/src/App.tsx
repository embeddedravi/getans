import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { HomePage } from "./pages/HomePage";
import { PublicIndexPage } from "./pages/PublicIndexPage";
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
import { AdminPublishersPage } from "./pages/AdminPublishersPage";
import { AdminSlotsPage } from "./pages/AdminSlotsPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { LiveEventsPage } from "./pages/LiveEventsPage";
import { MediaLibraryPage } from "./pages/MediaLibraryPage";
import { PublisherHelpPage } from "./pages/PublisherHelpPage";
import { AdvertiserWalletPage } from "./pages/AdvertiserWalletPage";
import { PublisherEarningsPage } from "./pages/PublisherEarningsPage";
import { ProfilePage } from "./pages/ProfilePage";
import { PublisherInventoryPage } from "./pages/PublisherInventoryPage";
import { SupportPage } from "./pages/SupportPage";
import { CreativesPage } from "./pages/CreativesPage";
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
  if (isAdmin === null) return <div className="p-6 text-sm ">Checking access…</div>;
  return isAdmin ? children : <Navigate to="/home" replace />;
}

function RequireAdvertiserOrPublisher({ children }: { children: JSX.Element }) {
  const [allowed, setAllowed] = useState<boolean | null>(null);
  useEffect(() => {
    api.me().then((user) => {
      const role = (user as { role?: string }).role;
      setAllowed(role === "advertiser" || role === "publisher");
    }).catch(() => setAllowed(false));
  }, []);
  if (allowed === null) return <div className="p-6 text-sm">Checking access…</div>;
  return allowed ? children : <Navigate to="/home" replace />;
}

function RequireAdvertiser({ children }: { children: JSX.Element }) {
  const [isAdvertiser, setIsAdvertiser] = useState<boolean | null>(null);
  useEffect(() => {
    api.me().then((user) => setIsAdvertiser((user as { role?: string }).role === "advertiser")).catch(() => setIsAdvertiser(false));
  }, []);
  if (isAdvertiser === null) return <div className="p-6 text-sm">Checking access…</div>;
  return isAdvertiser ? children : <Navigate to="/home" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/verify" element={<VerifyMobilePage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/media" element={<RequireAuth><MediaLibraryPage /></RequireAuth>} />
        <Route path="/creatives" element={<RequireAuth><CreativesPage /></RequireAuth>} />
        <Route path="/profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
        <Route path="/help" element={<RequireAuth><PublisherHelpPage /></RequireAuth>} />
        <Route path="/" element={<PublicIndexPage />} />
        <Route path="/home" element={<RequireAuth><HomePage /></RequireAuth>} />
        <Route path="/analytics" element={<RequireAuth><AnalyticsPage /></RequireAuth>} />
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
        <Route path="/adslots" element={<RequireAuth><PublishersPage view="adslots" /></RequireAuth>} />
        <Route path="/approvals" element={<RequireAuth><ApprovalsPage /></RequireAuth>} />
        <Route path="/payments" element={<RequireAuth><AdvertiserPaymentsPage /></RequireAuth>} />
        <Route path="/wallet" element={<RequireAuth><AdvertiserWalletPage /></RequireAuth>} />
        <Route path="/earnings" element={<RequireAuth><PublisherEarningsPage /></RequireAuth>} />
        <Route path="/payouts" element={<RequireAuth><PaymentsPage /></RequireAuth>} />
        <Route path="/manage-advertiser" element={<RequireAuth><RequireAdmin><AdminAdvertisersPage /></RequireAdmin></RequireAuth>} />
        <Route path="/manage-publisher" element={<RequireAuth><RequireAdmin><AdminPublishersPage /></RequireAdmin></RequireAuth>} />
        <Route path="/manage-campaign" element={<RequireAuth><RequireAdmin><CampaignsPage /></RequireAdmin></RequireAuth>} />
        <Route path="/manage-slots" element={<RequireAuth><RequireAdmin><AdminSlotsPage /></RequireAdmin></RequireAuth>} />
        <Route path="/manage-users" element={<RequireAuth><RequireAdmin><AdminUsersPage /></RequireAdmin></RequireAuth>} />
        <Route path="/live-events" element={<RequireAuth><RequireAdmin><LiveEventsPage /></RequireAdmin></RequireAuth>} />
        <Route path="/my-live-events" element={<RequireAuth><RequireAdvertiserOrPublisher><LiveEventsPage own /></RequireAdvertiserOrPublisher></RequireAuth>} />
        <Route path="/publisher-inventory" element={<RequireAuth><RequireAdvertiser><PublisherInventoryPage /></RequireAdvertiser></RequireAuth>} />
        <Route path="/support" element={<RequireAuth><SupportPage /></RequireAuth>} />
      </Routes>
    </BrowserRouter>
  );
}
