import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Shield } from "lucide-react";
import { ApiError } from "../api";
import { useAuth } from "../context/AuthContext";
import { LanguageToggle, useI18n } from "../i18n";
import { PAGE_ROUTES } from "../types";
import { Alert, Button } from "../components/ui";

export function LoginPage() {
  const { session, login } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (session) {
    const firstPage = session.granted_pages[0];
    return <Navigate to={firstPage ? PAGE_ROUTES[firstPage] : "/login"} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("invalid_login_analyst"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <div className="absolute right-4 top-4">
        <LanguageToggle />
      </div>
      <div className="w-full max-w-md rounded-2xl border border-border bg-white p-8 shadow-lg">
        <div className="mb-6 text-center">
          <Shield className="mx-auto mb-3 h-10 w-10 text-brand" />
          <h1 className="text-2xl font-bold text-brand">{t("internal_brand")}</h1>
          <p className="mt-1 text-sm text-muted">{t("employee_login")}</p>
        </div>

        {error ? <Alert tone="error">{error}</Alert> : null}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("username")}</span>
            <input
              className="w-full rounded-lg border border-border px-3 py-2 outline-none ring-brand focus:ring-2"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t("password")}</span>
            <input
              type="password"
              className="w-full rounded-lg border border-border px-3 py-2 outline-none ring-brand focus:ring-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? t("processing") : t("log_in")}
          </Button>
        </form>
      </div>
    </div>
  );
}
