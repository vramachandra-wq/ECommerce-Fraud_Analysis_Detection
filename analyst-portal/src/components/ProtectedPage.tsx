import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { PageKey } from "../types";

export function ProtectedPage({
  page,
  children,
}: {
  page: PageKey;
  children: React.ReactNode;
}) {
  const { session, loading, hasPage } = useAuth();

  if (loading) {
    return <p className="p-6 text-sm text-muted">Loading session...</p>;
  }

  if (!session) return <Navigate to="/login" replace />;
  if (!hasPage(page)) return <Navigate to="/login" replace />;

  return <>{children}</>;
}
