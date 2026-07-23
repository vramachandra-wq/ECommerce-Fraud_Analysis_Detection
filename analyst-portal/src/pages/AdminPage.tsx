import { FormEvent, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
  "Review Queue",
  "Entity Blacklists",
  "Analyst Permissions",
  "User Management",
  "Analytics",
  "Rule Management",
] as const;

type Tab = (typeof TABS)[number];

const PIE_COLORS = ["#be1e2d", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"];

export function AdminPage() {
  const { session } = useAuth();
  const [tab, setTab] = useState<Tab>("Analytics");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Admin Control Panel</h1>
        <p className="text-sm text-muted">
          Logged in as {session?.analyst.employee_name} ({session?.analyst.role})
        </p>
      </div>

      {error ? <Alert tone="error">{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}

      <div className="flex flex-wrap gap-2">
        {TABS.map((label) => (
          <button
            key={label}
            onClick={() => setTab(label)}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
              tab === label ? "bg-brand text-white" : "bg-white text-slate-700 ring-1 ring-border hover:bg-slate-50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

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
  const [ruleStats, setRuleStats] = useState<FraudRule[]>([]);

  useEffect(() => {
    api.analyticsSummary().then(setSummary);
    api.ruleStats().then((data) => setRuleStats(data.rules));
  }, []);

  if (!summary) return <p className="text-sm text-muted">Loading analytics...</p>;

  const pieData = Object.entries(summary.kpis.status_counts).map(([name, value]) => ({ name, value }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Total Orders" value={summary.kpis.total_orders.toLocaleString()} />
        <MetricCard label="Total Fraud Orders" value={summary.kpis.total_fraud.toLocaleString()} />
        <MetricCard label="Fraud Rate" value={`${summary.kpis.fraud_rate}%`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Order Status Distribution">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90}>
                  {pieData.map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Daily Order Volume — Current Month">
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

      <Card title="Rule Trigger Stats">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={ruleStats}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="rule_id" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="times_triggered" fill="#1f56ff" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

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
