import { NavLink, Outlet, Navigate } from "react-router-dom";
import { LogOut, Shield } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { PAGE_LABELS, PAGE_ROUTES, type PageKey } from "../types";
import { Button } from "./ui";

export function AppLayout() {
  const { session, logout, hasPage } = useAuth();

  if (!session) return <Navigate to="/login" replace />;

  const navItems = (Object.keys(PAGE_ROUTES) as PageKey[]).filter((page) => hasPage(page));

  if (!navItems.length) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-md rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <Shield className="mx-auto mb-4 h-10 w-10 text-brand" />
          <h1 className="text-xl font-semibold">No page access</h1>
          <p className="mt-2 text-sm text-muted">
            You are signed in as {session.analyst.employee_name}, but no portal pages are assigned.
            Contact an administrator.
          </p>
          <Button className="mt-6" variant="secondary" onClick={logout}>
            Log out
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
            <p className="text-xl font-bold text-brand">Metro Cart PRO</p>
            <p className="text-sm text-muted">Fraud Analyst Workspace</p>
          </div>
          <div className="text-right text-sm">
            <p className="font-medium">{session.analyst.employee_name}</p>
            <p className="text-muted">{session.analyst.role}</p>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[240px_1fr]">
        <aside className="h-fit rounded-xl border border-border bg-card p-4 shadow-sm">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">Navigation</p>
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
                {PAGE_LABELS[page]}
              </NavLink>
            ))}
          </nav>
          <Button variant="ghost" className="mt-4 w-full justify-start gap-2" onClick={logout}>
            <LogOut className="h-4 w-4" />
            Log out
          </Button>
        </aside>

        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
