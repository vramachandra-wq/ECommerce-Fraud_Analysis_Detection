import { FormEvent, useEffect, useState } from "react";
import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import type { FraudRule, PageKey, PermissionAnalyst } from "../types";
import { Alert, Button, Card, DataTable, MetricCard } from "../components/ui";
import { DashboardPage } from "./DashboardPage";

const TABS = [
  { label: "Review Queue", tone: "blue" },
  { label: "Entity Blacklists", tone: "rose" },
  { label: "Analyst Permissions", tone: "indigo" },
  { label: "User Management", tone: "teal" },
  { label: "Analytics", tone: "amber" },
  { label: "Rule Management", tone: "navy" },
] as const;

type Tab = (typeof TABS)[number]["label"];

const TAB_TONES: Record<
  Tab,
  { idle: string; active: string; dot: string }
> = {
  "Review Queue": {
    idle: "text-slate-500 hover:bg-blue-50 hover:text-blue-700",
    active: "bg-blue-50 text-blue-700 shadow-[inset_0_-2px_0_#1976d2]",
    dot: "bg-blue-500",
  },
  "Entity Blacklists": {
    idle: "text-slate-500 hover:bg-rose-50 hover:text-rose-700",
    active: "bg-rose-50 text-rose-700 shadow-[inset_0_-2px_0_#e53935]",
    dot: "bg-rose-500",
  },
  "Analyst Permissions": {
    idle: "text-slate-500 hover:bg-indigo-50 hover:text-indigo-700",
    active: "bg-indigo-50 text-indigo-700 shadow-[inset_0_-2px_0_#3949ab]",
    dot: "bg-indigo-500",
  },
  "User Management": {
    idle: "text-slate-500 hover:bg-teal-50 hover:text-teal-700",
    active: "bg-teal-50 text-teal-700 shadow-[inset_0_-2px_0_#00897b]",
    dot: "bg-teal-500",
  },
  Analytics: {
    idle: "text-slate-500 hover:bg-amber-50 hover:text-amber-700",
    active: "bg-amber-50 text-amber-700 shadow-[inset_0_-2px_0_#fb8c00]",
    dot: "bg-amber-500",
  },
  "Rule Management": {
    idle: "text-slate-500 hover:bg-slate-100 hover:text-slate-800",
    active: "bg-slate-100 text-slate-800 shadow-[inset_0_-2px_0_#1a237e]",
    dot: "bg-slate-700",
  },
};

const STATUS_COLORS: Record<string, string> = {
  PENDING_REVIEW: "#f59e0b",
  ON_HOLD: "#3b82f6",
  APPROVED: "#10b981",
  COMPLETED: "#059669",
  REJECTED: "#ef4444",
  CANCELLED: "#94a3b8",
};

const STATUS_LABELS: Record<string, string> = {
  PENDING_REVIEW: "Pending Review",
  ON_HOLD: "On Hold",
  APPROVED: "Approved",
  COMPLETED: "Completed",
  REJECTED: "Rejected",
  CANCELLED: "Cancelled",
};

const STATUS_ORDER = ["APPROVED", "REJECTED", "PENDING_REVIEW", "ON_HOLD", "COMPLETED", "CANCELLED"];

function statusColor(status: string, index: number) {
  if (STATUS_COLORS[status]) return STATUS_COLORS[status];
  const fallback = ["#1a237e", "#00897b", "#5e35b1", "#ec407a", "#6d4c41", "#546e7a"];
  return fallback[index % fallback.length];
}

function statusLabel(status: string) {
  return STATUS_LABELS[status] || status.replaceAll("_", " ");
}

export function AdminPage() {
  const { session } = useAuth();
  const [tab, setTab] = useState<Tab>("Analytics");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Admin Control Panel</h1>
          <p className="mt-1 text-sm text-muted">Manage queue, access, rules, and risk entities</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            {session?.analyst.role}
          </span>
          <span className="text-sm text-muted">{session?.analyst.employee_name}</span>
        </div>
      </div>

      {error ? <Alert tone="error">{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}

      <nav className="overflow-x-auto rounded-xl border border-border bg-white p-1 shadow-sm">
        <div className="flex min-w-max gap-1">
          {TABS.map(({ label }) => {
            const tones = TAB_TONES[label];
            const isActive = tab === label;
            return (
              <button
                key={label}
                onClick={() => setTab(label)}
                className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-2.5 text-sm font-semibold transition ${
                  isActive ? tones.active : tones.idle
                }`}
              >
                <span className={`h-2.5 w-2.5 rounded-full ${tones.dot}`} />
                {label}
              </button>
            );
          })}
        </div>
      </nav>

      {tab === "Review Queue" ? <DashboardPage /> : null}

      {tab === "Entity Blacklists" ? (
        <BlacklistTab onError={setError} onSuccess={setSuccess} />
      ) : null}
      {tab === "Analyst Permissions" ? <PermissionsTab onError={setError} onSuccess={setSuccess} /> : null}
      {tab === "User Management" ? <UserManagementTab onError={setError} onSuccess={setSuccess} /> : null}
      {tab === "Analytics" ? <AnalyticsTab /> : null}
      {tab === "Rule Management" ? <RuleManagementTab onError={setError} onSuccess={setSuccess} /> : null}
    </div>
  );
}

function BlacklistTab({
  onError,
  onSuccess,
}: {
  onError: (msg: string) => void;
  onSuccess: (msg: string) => void;
}) {
  const { session } = useAuth();
  const [entityType, setEntityType] = useState<"ip" | "phone" | "email">("ip");
  const [drafts, setDrafts] = useState({ ip: "", phone: "", email: "" });
  const [entry, setEntry] = useState<Record<string, unknown> | null>(null);
  const [reason, setReason] = useState("");
  const [checked, setChecked] = useState(false);
  const value = drafts[entityType];

  function switchEntityType(next: "ip" | "phone" | "email") {
    if (next === entityType) return;
    setEntityType(next);
    setEntry(null);
    setChecked(false);
    setReason("");
  }

  async function lookup() {
    onError("");
    const result = await api.blacklistLookup(entityType, value.trim());
    setEntry(result.entry);
    setChecked(true);
  }

  async function blacklist() {
    const analystId = session!.analyst.analyst_id;
    if (entityType === "ip") {
      await api.blacklistIp({ ip_address: value, reason, blacklisted_by: analystId });
    } else if (entityType === "phone") {
      await api.blacklistPhone({ phone_number: value, reason, blacklisted_by: analystId });
    } else {
      await api.blacklistEmail({ email: value, reason, blacklisted_by: analystId });
    }
    onSuccess(`${value} blacklisted.`);
    await lookup();
  }

  async function whitelist() {
    if (!entry) return;
    const payload = {
      blacklist_id: entry.blacklist_id,
      removed_by: session!.analyst.analyst_id,
      removed_at: new Date().toISOString(),
    };
    if (entityType === "ip") await api.whitelistIp(payload);
    else if (entityType === "phone") await api.whitelistPhone(payload);
    else await api.whitelistEmail(payload);
    onSuccess(`${value} whitelisted.`);
    await lookup();
  }

  return (
    <Card title="Entity Blacklist Management">
      <div className="mb-4 flex gap-2">
        {(["ip", "phone", "email"] as const).map((type) => (
          <Button
            key={type}
            variant={entityType === type ? "primary" : "secondary"}
            onClick={() => switchEntityType(type)}
          >
            {type.toUpperCase()}
          </Button>
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        <input
          className="min-w-[240px] flex-1 rounded-lg border border-border px-3 py-2 text-sm"
          placeholder={`Enter ${entityType}`}
          value={value}
          onChange={(e) =>
            setDrafts((prev) => ({ ...prev, [entityType]: e.target.value }))
          }
        />
        <Button onClick={() => lookup().catch((e) => onError(e.message))}>Check</Button>
      </div>
      {checked ? (
        <div className="mt-4 space-y-3">
          {entry ? (
            <>
              <Alert tone="error">{value} is currently blacklisted.</Alert>
              <p className="text-sm text-muted">
                Reason: {String(entry.reason)} | By: {String(entry.blacklisted_by_name ?? entry.blacklisted_by)}
              </p>
              <Button onClick={() => whitelist().catch((e) => onError(e.message))}>Whitelist</Button>
            </>
          ) : (
            <>
              <Alert tone="success">{value} is safe.</Alert>
              <textarea
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
                placeholder="Blacklist reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
              />
              <Button
                variant="danger"
                disabled={!reason.trim()}
                onClick={() => blacklist().catch((e) => onError(e.message))}
              >
                Blacklist
              </Button>
            </>
          )}
        </div>
      ) : null}
    </Card>
  );
}

function PermissionsTab({
  onError,
  onSuccess,
}: {
  onError: (msg: string) => void;
  onSuccess: (msg: string) => void;
}) {
  const { session } = useAuth();
  const [analysts, setAnalysts] = useState<PermissionAnalyst[]>([]);
  const [pages, setPages] = useState<PageKey[]>([]);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [selectedId, setSelectedId] = useState("");
  const [selections, setSelections] = useState<Record<string, boolean>>({});
  const [confirm, setConfirm] = useState(false);

  useEffect(() => {
    api.permissions().then((data) => {
      setAnalysts(data.analysts);
      setPages(data.all_pages);
      setLabels(data.page_labels);
      if (data.analysts[0]) {
        setSelectedId(data.analysts[0].analyst_id);
        const granted = Object.fromEntries(
          data.all_pages.map((p) => [p, data.analysts[0].granted_pages.includes(p)]),
        );
        setSelections(granted);
      }
    });
  }, []);

  useEffect(() => {
    const analyst = analysts.find((a) => a.analyst_id === selectedId);
    if (!analyst) return;
    setSelections(Object.fromEntries(pages.map((p) => [p, analyst.granted_pages.includes(p)])));
  }, [selectedId, analysts, pages]);

  async function save() {
    if (!confirm) {
      onError("Please confirm permission changes.");
      return;
    }
    await api.updatePermissions({
      analyst_id: selectedId,
      permissions: selections,
      granted_by: session!.analyst.analyst_id,
    });
    onSuccess("Permissions updated.");
    const refreshed = await api.permissions();
    setAnalysts(refreshed.analysts);
  }

  return (
    <Card title="Analyst Page Permissions">
      <select
        className="mb-4 w-full rounded-lg border border-border px-3 py-2 text-sm"
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value)}
      >
        {analysts.map((a) => (
          <option key={a.analyst_id} value={a.analyst_id}>
            {a.employee_name} ({a.username}, {a.role})
          </option>
        ))}
      </select>
      <div className="grid gap-2 md:grid-cols-2">
        {pages.map((page) => (
          <label key={page} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!selections[page]}
              onChange={(e) => setSelections((s) => ({ ...s, [page]: e.target.checked }))}
            />
            {labels[page] ?? page}
          </label>
        ))}
      </div>
      <label className="mt-4 flex items-center gap-2 text-sm">
        <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} />
        I confirm these permission changes.
      </label>
      <Button className="mt-4" onClick={() => save().catch((e) => onError(e.message))}>
        Save Permissions
      </Button>
    </Card>
  );
}

function UserManagementTab({
  onError,
  onSuccess,
}: {
  onError: (msg: string) => void;
  onSuccess: (msg: string) => void;
}) {
  const [form, setForm] = useState({
    analyst_id: "",
    employee_name: "",
    username: "",
    password: "",
    role: "Fraud Analyst",
  });
  const [performance, setPerformance] = useState<Record<string, unknown>[]>([]);
  const [confirm, setConfirm] = useState(false);

  useEffect(() => {
    api.analystPerformance().then((data) => setPerformance(data.analysts as Record<string, unknown>[]));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!confirm) {
      onError("Please confirm analyst creation.");
      return;
    }
    await api.createAnalyst(form);
    onSuccess(`Analyst ${form.employee_name} created.`);
    setForm({ analyst_id: "", employee_name: "", username: "", password: "", role: "Fraud Analyst" });
    const refreshed = await api.analystPerformance();
    setPerformance(refreshed.analysts as Record<string, unknown>[]);
  }

  return (
    <div className="space-y-6">
      <Card title="Create New Analyst">
        <form onSubmit={submit} className="grid gap-3 md:grid-cols-2">
          {(["analyst_id", "employee_name", "username", "password"] as const).map((field) => (
            <input
              key={field}
              className="rounded-lg border border-border px-3 py-2 text-sm"
              placeholder={field.replace("_", " ")}
              value={form[field]}
              onChange={(e) => setForm((s) => ({ ...s, [field]: e.target.value }))}
              type={field === "password" ? "password" : "text"}
              required
            />
          ))}
          <select
            className="rounded-lg border border-border px-3 py-2 text-sm md:col-span-2"
            value={form.role}
            onChange={(e) => setForm((s) => ({ ...s, role: e.target.value }))}
          >
            <option>Fraud Analyst</option>
            <option>Senior Fraud Analyst</option>
            <option>Admin</option>
          </select>
          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} />
            I confirm that I want to create this analyst profile.
          </label>
          <Button type="submit" className="md:col-span-2">
            Create Analyst
          </Button>
        </form>
      </Card>

      <Card title="Analyst Performance">
        <DataTable
          columns={[
            { key: "analyst_id", label: "ID" },
            { key: "employee_name", label: "Name" },
            { key: "role", label: "Role" },
            { key: "orders_reviewed", label: "Reviewed" },
            { key: "orders_rejected", label: "Rejected" },
          ]}
          rows={performance}
        />
      </Card>
    </div>
  );
}

function AnalyticsTab() {
  const [summary, setSummary] = useState<{
    kpis: { total_orders: number; total_fraud: number; fraud_rate: number; status_counts: Record<string, number> };
    recent_orders: Record<string, unknown>[];
    orders_over_time: { order_date: string; order_count: number }[];
  } | null>(null);

  useEffect(() => {
    api.analyticsSummary().then(setSummary);
  }, []);

  if (!summary) return <p className="text-sm text-muted">Loading analytics...</p>;

  const statusEntries = Object.entries(summary.kpis.status_counts || {})
    .map(([status, value]) => ({ status, value: Number(value) || 0 }))
    .filter((e) => e.value > 0)
    .sort((a, b) => {
      const ai = STATUS_ORDER.indexOf(a.status);
      const bi = STATUS_ORDER.indexOf(b.status);
      if (ai === -1 && bi === -1) return b.value - a.value;
      if (ai === -1) return 1;
      if (bi === -1) return -1;
      return ai - bi;
    });

  const totalStatuses = statusEntries.reduce((sum, e) => sum + e.value, 0) || 1;
  const pieData = statusEntries.map((e, index) => ({
    name: statusLabel(e.status),
    value: e.value,
    fill: statusColor(e.status, index),
    pct: (e.value / totalStatuses) * 100,
  }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Total Orders" value={summary.kpis.total_orders.toLocaleString()} />
        <MetricCard label="Total Fraud Orders" value={summary.kpis.total_fraud.toLocaleString()} />
        <MetricCard label="Fraud Rate" value={`${summary.kpis.fraud_rate}%`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Order Status Distribution">
          <p className="mb-4 text-sm text-muted">Share of all orders by current status</p>
          {pieData.length === 0 ? (
            <Alert tone="info">No order status data available.</Alert>
          ) : (
            <div className="grid gap-6 md:grid-cols-[220px_1fr] md:items-center">
              <div className="mx-auto h-56 w-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={58}
                      outerRadius={88}
                      paddingAngle={1.5}
                    >
                      {pieData.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number, name: string) => [
                        `${Number(value).toLocaleString()} (${((Number(value) / totalStatuses) * 100).toFixed(1)}%)`,
                        name,
                      ]}
                    />
                    <Legend verticalAlign="bottom" height={36} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-3">
                {pieData.map((entry) => (
                  <div key={entry.name}>
                    <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block h-3 w-3 rounded-full"
                          style={{ background: entry.fill }}
                        />
                        <span className="font-medium">{entry.name}</span>
                      </div>
                      <div className="flex items-center gap-3 tabular-nums">
                        <span className="font-semibold">{entry.value.toLocaleString()}</span>
                        <span className="w-12 text-right text-muted">{entry.pct.toFixed(1)}%</span>
                      </div>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.max(entry.pct, 0.8)}%`,
                          background: entry.fill,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card title="Daily Order Volume — Current Month">
          <p className="mb-4 text-sm text-muted">Orders placed each day this month</p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={summary.orders_over_time}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="order_date" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Line type="monotone" dataKey="order_count" stroke="#be1e2d" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card title="Recent Orders">
        <DataTable
          columns={[
            { key: "order_id", label: "Order ID" },
            { key: "customer_name", label: "Customer" },
            { key: "product_name", label: "Product" },
            { key: "amount", label: "Amount" },
            { key: "order_status", label: "Status" },
            { key: "order_timestamp", label: "Placed At" },
          ]}
          rows={summary.recent_orders}
        />
      </Card>
    </div>
  );
}

function RuleManagementTab({
  onError,
  onSuccess,
}: {
  onError: (msg: string) => void;
  onSuccess: (msg: string) => void;
}) {
  const [rules, setRules] = useState<FraudRule[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [action, setAction] = useState("HOLD");
  const [threshold, setThreshold] = useState(0);
  const [intervalValue, setIntervalValue] = useState(1);
  const [intervalUnit, setIntervalUnit] = useState("MINUTE");

  useEffect(() => {
    api.rules().then((data) => {
      setRules(data.rules);
      if (data.rules[0]) {
        setSelectedId(data.rules[0].rule_id);
      }
    });
  }, []);

  const selected = rules.find((r) => r.rule_id === selectedId);

  useEffect(() => {
    if (!selected) return;
    setAction(selected.action);
    setThreshold(Number(selected.threshold_value ?? 0));
    setIntervalValue(Number(selected.time_interval_value ?? 1));
    setIntervalUnit(selected.time_interval_unit ?? "MINUTE");
  }, [selected]);

  async function save() {
    if (!selected) return;
    await api.updateRule({
      rule_id: selected.rule_id,
      action,
      threshold_value: selected.rule_type === "STATIC" || selected.rule_name.toLowerCase().includes("blacklist")
        ? null
        : threshold,
      time_interval_value:
        selected.rule_type === "VELOCITY" || selected.rule_type === "BEHAVIORAL" ? intervalValue : null,
      time_interval_unit:
        selected.rule_type === "VELOCITY" || selected.rule_type === "BEHAVIORAL" ? intervalUnit : null,
    });
    onSuccess(`Rule ${selected.rule_id} updated.`);
    const refreshed = await api.rules();
    setRules(refreshed.rules);
  }

  if (!selected) return <p className="text-sm text-muted">No rules found.</p>;

  const isLocked =
    selected.rule_id === "R001" || selected.rule_name.toLowerCase().includes("blacklist");

  return (
    <Card title="Rule Configuration Management">
      <select
        className="mb-4 w-full rounded-lg border border-border px-3 py-2 text-sm"
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value)}
      >
        {rules.map((rule) => (
          <option key={rule.rule_id} value={rule.rule_id}>
            {rule.rule_id} — {rule.rule_name}
          </option>
        ))}
      </select>

      <p className="text-sm text-muted">{selected.rule_description}</p>
      <p className="mt-1 text-sm">
        Type: <span className="font-medium">{selected.rule_type}</span>
      </p>

      {isLocked ? (
        <Alert tone="info">Action is locked for this rule in the Streamlit admin panel as well.</Alert>
      ) : (
        <label className="mt-4 block text-sm">
          Action
          <select
            className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          >
            {["HOLD", "REVIEW", "REJECTED", "PASS"].map((opt) => (
              <option key={opt}>{opt}</option>
            ))}
          </select>
        </label>
      )}

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <label className="text-sm">
          Threshold
          <input
            type="number"
            className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            disabled={selected.rule_type === "STATIC"}
          />
        </label>
        <label className="text-sm">
          Interval
          <input
            type="number"
            className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            value={intervalValue}
            onChange={(e) => setIntervalValue(Number(e.target.value))}
            disabled={!(selected.rule_type === "VELOCITY" || selected.rule_type === "BEHAVIORAL")}
          />
        </label>
        <label className="text-sm">
          Unit
          <select
            className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            value={intervalUnit}
            onChange={(e) => setIntervalUnit(e.target.value)}
            disabled={!(selected.rule_type === "VELOCITY" || selected.rule_type === "BEHAVIORAL")}
          >
            {["MINUTE", "HOUR", "DAY", "WEEK"].map((unit) => (
              <option key={unit}>{unit}</option>
            ))}
          </select>
        </label>
      </div>

      <Button className="mt-4" onClick={() => save().catch((e) => onError(e.message))}>
        Save Rule Changes
      </Button>
    </Card>
  );
}
