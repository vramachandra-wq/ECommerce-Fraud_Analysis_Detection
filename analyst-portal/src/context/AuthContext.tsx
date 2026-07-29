import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, ApiError } from "../api";
import type { AuthSession, PageKey } from "../types";

interface AuthContextValue {
  session: AuthSession | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  completeSsoLogin: () => Promise<void>;
  logout: () => void;
  hasPage: (page: PageKey) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const AUTH_METHOD_KEY = "metro_cart_auth_method";
const PORTAL_BASE_URL = new URL(import.meta.env.BASE_URL, window.location.origin).toString();

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .me()
      .then((me) => {
        setSession({ ...me, token: "" } as AuthSession);
      })
      .catch(() => {
        localStorage.removeItem(AUTH_METHOD_KEY);
        setSession(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await api.login(username, password);
    localStorage.setItem(AUTH_METHOD_KEY, "password");
    setSession({ ...data, token: "" } as AuthSession);
  }, []);

  const completeSsoLogin = useCallback(async () => {
    const data = await api.ssoComplete();
    localStorage.setItem(AUTH_METHOD_KEY, "sso");
    setSession({ ...data, token: "" } as AuthSession);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_METHOD_KEY);
    setSession(null);
    const apiOrigin = import.meta.env.VITE_API_ORIGIN ?? "http://127.0.0.1:8000";
    const returnTo = new URL("login", PORTAL_BASE_URL).toString();
    window.location.href = `${apiOrigin}/auth/sso/logout?return_to=${encodeURIComponent(returnTo)}`;
  }, []);

  const hasPage = useCallback(
    (page: PageKey) => !!session?.granted_pages.includes(page),
    [session],
  );

  const value = useMemo(
    () => ({ session, loading, login, completeSsoLogin, logout, hasPage }),
    [session, loading, login, completeSsoLogin, logout, hasPage],
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
