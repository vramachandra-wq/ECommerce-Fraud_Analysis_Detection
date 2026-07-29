import { FormEvent, useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Shield } from "lucide-react";
import { api, ApiError, ssoLoginHref } from "../api";
import { useAuth } from "../context/AuthContext";
import { LanguageToggle, useI18n } from "../i18n";
import { PAGE_ROUTES } from "../types";
import { Alert, Button } from "../components/ui";

type LoginMode = "login" | "change_password";

export function LoginPage() {
  const { session, login, completeSsoLogin } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [mode, setMode] = useState<LoginMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [ssoBootstrapping, setSsoBootstrapping] = useState(
    () => searchParams.get("sso") === "1",
  );

  useEffect(() => {
    api
      .ssoConfig()
      .then((cfg) => setSsoEnabled(!!cfg.enabled))
      .catch(() => setSsoEnabled(false));
  }, []);

  useEffect(() => {
    const ssoHandoff = searchParams.get("sso") === "1";
    const ssoError = searchParams.get("sso_error");
    if (!ssoHandoff && !ssoError) return;

    const next = new URLSearchParams(searchParams);
    next.delete("sso");
    next.delete("sso_token");
    next.delete("sso_error");
    setSearchParams(next, { replace: true });

    if (ssoError) {
      setError(`${t("sso_login_failed")}: ${ssoError}`);
      setSsoBootstrapping(false);
      return;
    }

    setSsoBootstrapping(true);
    completeSsoLogin()
      .then(() => navigate("/dashboard", { replace: true }))
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : t("sso_login_failed"));
      })
      .finally(() => setSsoBootstrapping(false));
  }, [searchParams, setSearchParams, completeSsoLogin, navigate, t]);

  if (session) {
    const firstPage = session.granted_pages[0];
    return <Navigate to={firstPage ? PAGE_ROUTES[firstPage] : "/login"} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      if (mode === "change_password") {
        await api.changePassword({
          username,
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        });
        setSuccess(t("password_change_then_login"));
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
        setTimeout(() => setMode("login"), 1200);
        return;
      }
      await login(username, password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : mode === "change_password"
            ? t("password_change_failed")
            : t("invalid_login_analyst"),
      );
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
          <h1 className="text-2xl font-bold text-brand">
            {mode === "change_password" ? t("change_password") : t("internal_brand")}
          </h1>
          <p className="mt-1 text-sm text-muted">
            {mode === "change_password" ? t("password_change_login_hint") : t("employee_login")}
          </p>
        </div>

        {error ? <Alert tone="error">{error}</Alert> : null}
        {success ? <Alert tone="success">{success}</Alert> : null}
        {ssoBootstrapping ? (
          <p className="text-sm text-muted">{t("processing")}</p>
        ) : null}

        {mode === "login" && ssoEnabled ? (
          <div className="mt-6 space-y-3">
            <Button
              type="button"
              className="w-full"
              variant="secondary"
              disabled={loading || ssoBootstrapping}
              onClick={() => {
                window.location.href = ssoLoginHref();
              }}
            >
              {t("sign_in_sso")}
            </Button>
            <p className="text-center text-xs text-muted">{t("or_continue_with_password")}</p>
          </div>
        ) : null}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
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
          {mode === "login" ? (
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
          ) : (
            <>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">{t("current_password")}</span>
                <input
                  type="password"
                  className="w-full rounded-lg border border-border px-3 py-2 outline-none ring-brand focus:ring-2"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">{t("new_password")}</span>
                <input
                  type="password"
                  className="w-full rounded-lg border border-border px-3 py-2 outline-none ring-brand focus:ring-2"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">{t("confirm_new_password")}</span>
                <input
                  type="password"
                  className="w-full rounded-lg border border-border px-3 py-2 outline-none ring-brand focus:ring-2"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </label>
            </>
          )}
          <Button type="submit" className="w-full" disabled={loading || ssoBootstrapping}>
            {loading
              ? t("processing")
              : mode === "change_password"
                ? t("update_password")
                : t("log_in")}
          </Button>
          {mode === "login" ? (
            <Button
              type="button"
              className="w-full"
              variant="secondary"
              disabled={loading || ssoBootstrapping}
              onClick={() => {
                setError("");
                setSuccess("");
                setMode("change_password");
              }}
            >
              {t("change_password")}
            </Button>
          ) : (
            <Button
              type="button"
              className="w-full"
              variant="secondary"
              disabled={loading}
              onClick={() => {
                setError("");
                setSuccess("");
                setMode("login");
              }}
            >
              {t("back_to_login")}
            </Button>
          )}
        </form>
      </div>
    </div>
  );
}
