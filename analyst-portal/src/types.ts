export type PageKey =
  | "FRAUD_DASHBOARD"
  | "ADMIN_PANEL"
  | "POWER_BI_DASHBOARD"
  | "AI_CHATBOT";

export interface Analyst {
  analyst_id: string;
  employee_name: string;
  username: string;
  role: string;
}

export interface AuthSession {
  analyst: Analyst;
  granted_pages: PageKey[];
  is_admin: boolean;
  token: string;
}

export interface QueueOrder {
  order_id: string;
  user_id: string;
  customer_name: string;
  product_name: string;
  category?: string;
  quantity?: number;
  amount: number;
  order_status: string;
  flagged_reason: string;
  order_timestamp?: string;
  tagged_timestamp?: string;
  delay_minutes: number;
  rule_name?: string;
  review_deadline?: string;
  minutes_remaining?: number;
  minutes_remaining_display?: number;
  minutes_overdue?: number;
  is_overdue?: boolean;
}

export interface OrderDetail {
  order: Record<string, unknown>;
  timing?: {
    delay_minutes?: number;
    review_deadline?: string | null;
    minutes_remaining?: number | null;
    minutes_remaining_display?: number;
    minutes_overdue?: number;
    is_overdue?: boolean;
    rule_name?: string | null;
  };
  blacklists: {
    ip: Record<string, unknown> | null;
    phone: Record<string, unknown> | null;
    email: Record<string, unknown> | null;
  };
}

export interface FraudRule {
  rule_id: string;
  rule_name: string;
  rule_description: string;
  rule_type: string;
  action: string;
  threshold_value: number | null;
  time_interval_value: number | null;
  time_interval_unit: string | null;
  times_triggered?: number;
}

export interface PermissionAnalyst {
  analyst_id: string;
  employee_name: string;
  username: string;
  role: string;
  granted_pages: PageKey[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  status?: string;
  sql?: string | null;
  rows?: Record<string, unknown>[] | null;
  df?: Record<string, unknown>[] | null;
  chart?: {
    type?: string;
    types?: string[];
    labels?: string[];
    values?: number[];
    value?: number | string;
    label?: string;
    x_label?: string;
    y_label?: string;
  } | null;
  followups?: string[];
  business_advice?: string[];
  insight_title?: string;
}

export interface ChatResponse {
  status: string;
  content: string;
  sql?: string | null;
  rows?: Record<string, unknown>[] | null;
  chart?: ChatMessage["chart"];
  followups?: string[];
  business_advice?: string[];
  insight_title?: string;
}

export const PAGE_ROUTES: Record<PageKey, string> = {
  ADMIN_PANEL: "/admin",
  FRAUD_DASHBOARD: "/dashboard",
  POWER_BI_DASHBOARD: "/analytics",
  AI_CHATBOT: "/chatbot",
};

export const PAGE_LABELS: Record<PageKey, string> = {
  ADMIN_PANEL: "Admin Control Panel",
  FRAUD_DASHBOARD: "Fraud Analyst Dashboard",
  POWER_BI_DASHBOARD: "Analytics Dashboards",
  AI_CHATBOT: "Analytics AI Chatbot",
};
