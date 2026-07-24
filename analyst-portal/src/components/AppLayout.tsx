import { NavLink, Outlet, Navigate } from "react-router-dom";
import { LogOut, Shield } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { LanguageToggle, PAGE_LABEL_KEYS, useI18n } from "../i18n";
import { PAGE_ROUTES, type PageKey } from "../types";
import { Button } from "./ui";

export function AppLayout() {
  const { session, logout, hasPage } = useAuth();
  const { t } = useI18n();

  if (!session) return <Navigate to="/login" replace />;

  const navItems = (Object.keys(PAGE_ROUTES) as PageKey[]).filter((page) => hasPage(page));

  if (!navItems.length) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-md rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <Shield className="mx-auto mb-4 h-10 w-10 text-brand" />
          <h1 className="text-xl font-semibold">{t("no_page_access")}</h1>
          <p className="mt-2 text-sm text-muted">{t("contact_admin_access")}</p>
          <div className="mt-4 flex justify-center">
            <LanguageToggle />
          </div>
          <Button className="mt-6" variant="secondary" onClick={logout}>
            {t("log_out")}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xl font-bold text-brand">{t("internal_brand")}</p>
            <p className="text-sm text-muted">{t("fraud_analyst_workspace")}</p>
          </div>
          <div className="flex items-center gap-4">
            <LanguageToggle />
            <div className="text-right text-sm">
              <p className="font-medium">{session.analyst.employee_name}</p>
              <p className="text-muted">{session.analyst.role}</p>
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[240px_1fr]">
        <aside className="h-fit rounded-xl border border-border bg-card p-4 shadow-sm">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">{t("nav_title")}</p>
          <nav className="space-y-1">
            {navItems.map((page) => (
              <NavLink
                key={page}
                to={PAGE_ROUTES[page]}
                className={({ isActive }) =>
                  `block rounded-lg px-3 py-2 text-sm font-medium transition ${
                    isActive ? "bg-brand text-white" : "text-slate-700 hover:bg-slate-100"
                  }`
                }
              >
                {t(PAGE_LABEL_KEYS[page])}
              </NavLink>
            ))}
          </nav>
          <Button variant="ghost" className="mt-4 w-full justify-start gap-2" onClick={logout}>
            <LogOut className="h-4 w-4" />
            {t("log_out")}
          </Button>
        </aside>

        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
