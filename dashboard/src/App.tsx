import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { CampaignsPage } from "./pages/CampaignsPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { PublishersPage } from "./pages/PublishersPage";
import { VerifyMobilePage } from "./pages/VerifyMobilePage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { PaymentsPage } from "./pages/PaymentsPage";

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem("access_token");
  return token ? children : <Navigate to="/login" replace />;
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
        <Route path="/payments" element={<RequireAuth><PaymentsPage /></RequireAuth>} />
      </Routes>
    </BrowserRouter>
  );
}
