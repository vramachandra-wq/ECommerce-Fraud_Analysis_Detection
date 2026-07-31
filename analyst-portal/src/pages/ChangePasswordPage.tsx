import { FormEvent, useState } from "react";
import { api, ApiError } from "../api";
import { useI18n } from "../i18n";
import { Alert, Button, Card } from "../components/ui";

export function ChangePasswordPage() {
  const { t } = useI18n();
  const isSsoSession =
    typeof window !== "undefined" &&
    window.localStorage.getItem("metro_cart_auth_method") === "sso";
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setSuccess(t("password_change_success"));
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("password_change_failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card title={t("change_password")}>
      <p className="mb-4 text-sm text-muted">{t("password_change_login_hint")}</p>
      {isSsoSession ? (
        <Alert tone="info">
          You are signed in with SSO. This change updates both the local Metro Cart analyst password and the
          matching SSO account password.
        </Alert>
      ) : null}
      {error ? <Alert tone="error">{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}
      <form onSubmit={handleSubmit} className="mt-4 max-w-md space-y-4">
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
        <Button type="submit" disabled={loading}>
          {loading ? t("processing") : t("update_password")}
        </Button>
      </form>
    </Card>
  );
}
