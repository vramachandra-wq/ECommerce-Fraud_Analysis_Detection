import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { ProtectedPage } from "./components/ProtectedPage";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { I18nProvider, useI18n } from "./i18n";
import { AdminPage } from "./pages/AdminPage";
import { ChatbotPage } from "./pages/ChatbotPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { PowerBIPage } from "./pages/PowerBIPage";
import { PAGE_ROUTES } from "./types";

function HomeRedirect() {
  const { session, loading } = useAuth();
  const { t } = useI18n();
  if (loading) return <p className="p-6 text-sm text-muted">{t("loading_ellipsis")}</p>;
  if (!session) return <Navigate to="/login" replace />;
  const first = session.granted_pages[0];
  return <Navigate to={first ? PAGE_ROUTES[first] : "/login"} replace />;
}

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<AppLayout />}>
            <Route index element={<HomeRedirect />} />
            <Route path="/change-password" element={<ChangePasswordPage />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedPage page="FRAUD_DASHBOARD">
                  <DashboardPage />
                </ProtectedPage>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedPage page="ADMIN_PANEL">
                  <AdminPage />
                </ProtectedPage>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedPage page="POWER_BI_DASHBOARD">
                  <PowerBIPage />
                </ProtectedPage>
              }
            />
            <Route
              path="/chatbot"
              element={
                <ProtectedPage page="AI_CHATBOT">
                  <ChatbotPage />
                </ProtectedPage>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </I18nProvider>
  );
}
