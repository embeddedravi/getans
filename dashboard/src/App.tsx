import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { CampaignsPage } from "./pages/CampaignsPage";
import { LoginPage } from "./pages/LoginPage";
import { PublishersPage } from "./pages/PublishersPage";

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem("access_token");
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
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
      </Routes>
    </BrowserRouter>
  );
}
