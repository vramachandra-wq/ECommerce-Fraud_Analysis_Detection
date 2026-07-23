const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  return localStorage.getItem("metro_cart_token");
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(String(detail), response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  login: (username: string, password: string) =>
    apiRequest<import("./types").AuthSession>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ username, password }) },
      false,
    ),
  me: () => apiRequest<Omit<import("./types").AuthSession, "token">>("/auth/me"),
  config: () => apiRequest<{ power_bi_embed_url: string }>("/portal/config"),
  syncHolds: () => apiRequest<{ auto_approved: number }>("/portal/sync-holds", { method: "POST" }),
  queue: () =>
    apiRequest<{
      orders: import("./types").QueueOrder[];
      metrics: { total: number; pending_review: number; on_hold: number };
    }>("/portal/queue"),
  orderDetail: (orderId: string) =>
    apiRequest<import("./types").OrderDetail>(`/portal/orders/${encodeURIComponent(orderId)}`),
  approveOrder: (payload: Record<string, unknown>) =>
    apiRequest("/approve-order", { method: "PUT", body: JSON.stringify(payload) }),
  rejectOrder: (payload: Record<string, unknown>) =>
    apiRequest("/reject-order", { method: "PUT", body: JSON.stringify(payload) }),
  batchApprove: (payload: Record<string, unknown>) =>
    apiRequest("/batch-approve", { method: "PUT", body: JSON.stringify(payload) }),
  batchReject: (payload: Record<string, unknown>) =>
    apiRequest("/batch-reject", { method: "PUT", body: JSON.stringify(payload) }),
  blacklistIp: (payload: Record<string, unknown>) =>
    apiRequest("/blacklist-ip", { method: "POST", body: JSON.stringify(payload) }),
  blacklistPhone: (payload: Record<string, unknown>) =>
    apiRequest("/blacklist-phone", { method: "POST", body: JSON.stringify(payload) }),
  blacklistEmail: (payload: Record<string, unknown>) =>
    apiRequest("/blacklist-email", { method: "POST", body: JSON.stringify(payload) }),
  whitelistIp: (payload: Record<string, unknown>) =>
    apiRequest("/whitelist-ip", { method: "PUT", body: JSON.stringify(payload) }),
  whitelistPhone: (payload: Record<string, unknown>) =>
    apiRequest("/whitelist-phone", { method: "PUT", body: JSON.stringify(payload) }),
  whitelistEmail: (payload: Record<string, unknown>) =>
    apiRequest("/whitelist-email", { method: "PUT", body: JSON.stringify(payload) }),
  blacklistLookup: (entityType: string, value: string) =>
    apiRequest<{ entry: Record<string, unknown> | null }>(
      `/portal/blacklist/${entityType}/${encodeURIComponent(value)}`,
    ),
  analyticsSummary: () => apiRequest("/portal/analytics/summary"),
  ruleStats: () => apiRequest<{ rules: import("./types").FraudRule[] }>("/portal/analytics/rule-stats"),
  analystPerformance: () => apiRequest("/portal/analytics/analyst-performance"),
  permissions: () =>
    apiRequest<{
      analysts: import("./types").PermissionAnalyst[];
      all_pages: import("./types").PageKey[];
      page_labels: Record<string, string>;
    }>("/portal/permissions"),
  updatePermissions: (payload: Record<string, unknown>) =>
    apiRequest("/permissions/bulk", { method: "PUT", body: JSON.stringify(payload) }),
  createAnalyst: (payload: Record<string, unknown>) =>
    apiRequest("/create-analyst", { method: "POST", body: JSON.stringify(payload) }),
  rules: () => apiRequest<{ rules: import("./types").FraudRule[] }>("/portal/rules"),
  updateRule: (payload: Record<string, unknown>) =>
    apiRequest("/update-rule", { method: "PUT", body: JSON.stringify(payload) }),
  powerBi: () => apiRequest<{ embed_url: string }>("/portal/power-bi"),
  chat: (message: string, history: { role: string; content: string }[]) =>
    apiRequest<{ content: string; sql?: string | null; rows?: Record<string, unknown>[] | null }>(
      "/portal/chat",
      { method: "POST", body: JSON.stringify({ message, history }) },
    ),
};
