import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, ApiError } from "./api";
import type { AuthSession, PageKey } from "./types";

interface AuthContextValue {
  session: AuthSession | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasPage: (page: PageKey) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const STORAGE_KEY = "metro_cart_session";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      setLoading(false);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as AuthSession;
      setSession(parsed);
      api
        .me()
        .then((me) => {
          setSession((prev) =>
            prev
              ? {
                  ...prev,
                  analyst: me.analyst,
                  granted_pages: me.granted_pages,
                  is_admin: me.is_admin,
                }
              : prev,
          );
        })
        .catch(() => {
          localStorage.removeItem(STORAGE_KEY);
          localStorage.removeItem("metro_cart_token");
          setSession(null);
        })
        .finally(() => setLoading(false));
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem("metro_cart_token");
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await api.login(username, password);
    localStorage.setItem("metro_cart_token", data.token);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    setSession(data);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem("metro_cart_token");
    setSession(null);
  }, []);

  const hasPage = useCallback(
    (page: PageKey) => !!session?.granted_pages.includes(page),
    [session],
  );

  const value = useMemo(
    () => ({ session, loading, login, logout, hasPage }),
    [session, loading, login, logout, hasPage],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function useRequireAuth() {
  const auth = useAuth();
  if (!auth.loading && !auth.session) {
    throw new ApiError("Not authenticated", 401);
  }
  return auth;
}
