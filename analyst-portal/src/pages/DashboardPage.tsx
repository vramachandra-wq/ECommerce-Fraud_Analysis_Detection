import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import type { OrderDetail, OrderLineItem, QueueOrder } from "../types";
import { Alert, Button, Card, DataTable, MetricCard, StatusBadge } from "../components/ui";
import { displayPii } from "../pii";

function formatMinutes(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const mins = Math.abs(Number(value));
  if (mins < 60) return `${Math.round(mins)}m`;
  const hours = Math.floor(mins / 60);
  const rem = Math.round(mins % 60);
  return rem ? `${hours}h ${rem}m` : `${hours}h`;
}

export function DashboardPage() {
  const { session } = useAuth();
  const [orders, setOrders] = useState<QueueOrder[]>([]);
  const [metrics, setMetrics] = useState({
    total: 0,
    pending_review: 0,
    on_hold: 0,
    backlog: 0,
    max_minutes_overdue: 0,
  });
  const [selected, setSelected] = useState<string[]>([]);
  const [activeOrderId, setActiveOrderId] = useState("");
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const [comments, setComments] = useState("");
  const [batchComments, setBatchComments] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [blacklistReason, setBlacklistReason] = useState({ ip: "", phone: "", email: "" });

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const sync = await api.syncHolds();
      if (sync.auto_approved > 0) {
        setNotice(`${sync.auto_approved} order(s) auto-approved after hold window elapsed.`);
      }
      const data = await api.queue();
      setOrders(data.orders);
      setMetrics({
        total: data.metrics.total,
        pending_review: data.metrics.pending_review,
        on_hold: data.metrics.on_hold,
        backlog: data.metrics.backlog ?? 0,
        max_minutes_overdue: data.metrics.max_minutes_overdue ?? 0,
      });
      if (!activeOrderId && data.orders[0]) setActiveOrderId(data.orders[0].order_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load queue");
    } finally {
      setLoading(false);
    }
  }, [activeOrderId]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  useEffect(() => {
    if (!activeOrderId) {
      setDetail(null);
      return;
    }
    api.orderDetail(activeOrderId).then(setDetail).catch(() => setDetail(null));
  }, [activeOrderId]);

  const allSelected = useMemo(
    () => orders.length > 0 && selected.length === orders.length,
    [orders.length, selected.length],
  );

  const overdueOrders = useMemo(() => orders.filter((o) => o.is_overdue), [orders]);

  function toggleAll() {
    setSelected(allSelected ? [] : orders.map((o) => o.order_id));
  }

  async function approve(orderId: string) {
    await api.approveOrder({
      order_id: orderId,
      approved_at: new Date().toISOString(),
      reviewed_by: session!.analyst.analyst_id,
      review_comments: comments || "",
    });
    setComments("");
    await loadQueue();
  }

  async function reject(orderId: string, isFraud = false) {
    if (!comments.trim()) {
      setError("Review comments are required before rejecting an order.");
      return;
    }
    await api.rejectOrder({
      order_id: orderId,
      rejected_at: new Date().toISOString(),
      reviewed_by: session!.analyst.analyst_id,
      review_comments: comments,
      is_fraud: isFraud,
    });
    setComments("");
    await loadQueue();
  }

  async function batchApprove() {
    await api.batchApprove({
      order_ids: selected,
      approved_at: new Date().toISOString(),
      reviewed_by: session!.analyst.analyst_id,
      review_comments: batchComments || "",
    });
    setSelected([]);
    setBatchComments("");
    await loadQueue();
  }

  async function batchReject(isFraud = false) {
    if (!batchComments.trim()) {
      setError("Batch review comments are required before rejecting.");
      return;
    }
    await api.batchReject({
      order_ids: selected,
      rejected_at: new Date().toISOString(),
      reviewed_by: session!.analyst.analyst_id,
      review_comments: batchComments,
      is_fraud: isFraud,
    });
    setSelected([]);
    setBatchComments("");
    await loadQueue();
  }

  async function blacklist(entity: "ip" | "phone" | "email") {
    if (!detail) return;
    const reason =
      entity === "ip"
        ? blacklistReason.ip
        : entity === "phone"
          ? blacklistReason.phone
          : blacklistReason.email;
    await api.blacklistFromOrder(String(detail.order.order_id), entity, reason);
    const refreshed = await api.orderDetail(activeOrderId);
    setDetail(refreshed);
  }

  const timing = detail?.timing || orders.find((o) => o.order_id === activeOrderId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Fraud Analyst Workspace</h1>
        <p className="text-sm text-muted">Logged in as {session?.analyst.employee_name}</p>
      </div>

      {notice ? <Alert tone="info">{notice}</Alert> : null}
      {error ? <Alert tone="error">{error}</Alert> : null}

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Total in Queue" value={metrics.total} />
        <MetricCard label="Pending Review" value={metrics.pending_review} />
        <MetricCard label="On Hold" value={metrics.on_hold} />
        <MetricCard label="Backlog (Overdue)" value={metrics.backlog} />
      </div>

      {overdueOrders.length > 0 ? (
        <Card title={`Backlog (${overdueOrders.length} overdue)`}>
          <p className="mb-3 text-sm text-muted">
            Orders past their review delay window
            {metrics.max_minutes_overdue
              ? ` · max overdue ${formatMinutes(metrics.max_minutes_overdue)}`
              : ""}
          </p>
          <DataTable
            columns={[
              { key: "order_id", label: "Order ID" },
              {
                key: "order_status",
                label: "Status",
                render: (row) => <StatusBadge status={String(row.order_status)} />,
              },
              { key: "rule_name", label: "Rule" },
              {
                key: "minutes_overdue",
                label: "Overdue",
                render: (row) => formatMinutes(Number(row.minutes_overdue)),
              },
              {
                key: "delay_minutes",
                label: "Delay",
                render: (row) => `${row.delay_minutes ?? "—"}m`,
              },
            ]}
            rows={overdueOrders.slice(0, 8) as unknown as Record<string, unknown>[]}
          />
        </Card>
      ) : null}

      <Card title="Review Queue">
        {loading ? (
          <p className="text-sm text-muted">Loading queue...</p>
        ) : orders.length === 0 ? (
          <Alert tone="success">Queue is clear. No orders pending review.</Alert>
        ) : (
          <>
            <div className="mb-3 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={allSelected} onChange={toggleAll} id="select-all-queue" />
              <label htmlFor="select-all-queue">Select all ({orders.length})</label>
            </div>
            <DataTable
              columns={[
                {
                  key: "select",
                  label: "Select",
                  render: (row) => (
                    <input
                      type="checkbox"
                      checked={selected.includes(String(row.order_id))}
                      onChange={(e) => {
                        const id = String(row.order_id);
                        setSelected((prev) =>
                          e.target.checked ? [...prev, id] : prev.filter((x) => x !== id),
                        );
                      }}
                    />
                  ),
                },
                { key: "order_id", label: "Order ID" },
                { key: "customer_name", label: "Customer" },
                {
                  key: "product_name",
                  label: "Product",
                  render: (row) =>
                    Number(row.item_count) > 1
                      ? `${row.item_count} items · ${row.product_name}`
                      : String(row.product_name || ""),
                },
                {
                  key: "amount",
                  label: "Amount",
                  render: (row) =>
                    `₹ ${Number(row.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,
                },
                {
                  key: "order_status",
                  label: "Status",
                  render: (row) => <StatusBadge status={String(row.order_status)} />,
                },
                {
                  key: "delay_minutes",
                  label: "Delay",
                  render: (row) => `${row.delay_minutes ?? "—"}m`,
                },
                {
                  key: "remaining",
                  label: "Remaining",
                  render: (row) =>
                    row.is_overdue
                      ? `Overdue ${formatMinutes(Number(row.minutes_overdue))}`
                      : formatMinutes(
                          Number(row.minutes_remaining_display ?? row.minutes_remaining),
                        ),
                },
                { key: "rule_name", label: "Rule" },
                {
                  key: "tagged_timestamp",
                  label: "Placed At",
                  render: (row) => String(row.tagged_timestamp || row.order_timestamp || ""),
                },
              ]}
              rows={orders as unknown as Record<string, unknown>[]}
            />
          </>
        )}
      </Card>

      {selected.length > 0 ? (
        <Card title={`Batch Actions (${selected.length} selected)`}>
          <textarea
            className="mb-3 w-full rounded-lg border border-border px-3 py-2 text-sm"
            placeholder="Batch review comments (required for rejection / fraud)"
            value={batchComments}
            onChange={(e) => setBatchComments(e.target.value)}
            rows={3}
          />
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => batchApprove().catch((e) => setError(e.message))}>
              Approve Selected
            </Button>
            <Button variant="secondary" onClick={() => batchReject(false).catch((e) => setError(e.message))}>
              Reject Selected
            </Button>
            <Button variant="danger" onClick={() => batchReject(true).catch((e) => setError(e.message))}>
              Mark as Fraud
            </Button>
          </div>
        </Card>
      ) : null}

      {orders.length > 0 ? (
        <Card title="Single Order Investigation">
          <label className="mb-4 block text-sm">
            <span className="mb-1 block font-medium">Order ID</span>
            <select
              className="w-full rounded-lg border border-border px-3 py-2"
              value={activeOrderId}
              onChange={(e) => setActiveOrderId(e.target.value)}
            >
              {orders.map((o) => (
                <option key={o.order_id} value={o.order_id}>
                  {o.order_id}
                  {o.is_overdue ? " · OVERDUE" : ""}
                </option>
              ))}
            </select>
          </label>

          {detail ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-semibold">{String(detail.order.order_id)}</h3>
                <StatusBadge status={String(detail.order.order_status)} />
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <MetricCard label="Review Delay" value={`${timing?.delay_minutes ?? "—"}m`} />
                <MetricCard
                  label="Time Left"
                  value={
                    timing?.is_overdue
                      ? `Overdue ${formatMinutes(timing?.minutes_overdue)}`
                      : formatMinutes(timing?.minutes_remaining_display ?? timing?.minutes_remaining)
                  }
                />
                <MetricCard label="Triggered Rule" value={String(timing?.rule_name || detail.order.flagged_reason || "—")} />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg bg-slate-50 p-4 text-sm">
                  <p className="mb-2 font-semibold">Customer Details</p>
                  <p>
                    {String(detail.order.customer_name)} ({String(detail.order.user_id)})
                  </p>
                  <p>
                    Email: {displayPii(detail.order.email, "email", session?.analyst)}
                    {detail.blacklists.email ? " (blacklisted)" : ""}
                  </p>
                  <p>
                    Phone: {displayPii(detail.order.phone_number, "phone", session?.analyst)}
                    {detail.blacklists.phone ? " (blacklisted)" : ""}
                  </p>
                  <p>Address: {displayPii(detail.order.address, "address", session?.analyst)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-4 text-sm">
                  <p className="mb-2 font-semibold">Order Details</p>
                  {Array.isArray(detail.order.items) && (detail.order.items as OrderLineItem[]).length > 0 ? (
                    <div className="mb-3 overflow-auto">
                      <p className="mb-1 font-medium">
                        Items: {(detail.order.items as OrderLineItem[]).length}
                      </p>
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="text-slate-500">
                            <th className="py-1 pr-2">#</th>
                            <th className="py-1 pr-2">Product</th>
                            <th className="py-1 pr-2">Qty</th>
                            <th className="py-1 pr-2">Unit</th>
                            <th className="py-1">Line</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(detail.order.items as OrderLineItem[]).map((item) => (
                            <tr key={`${item.product_id}-${item.line_no}`} className="border-t border-slate-200">
                              <td className="py-1 pr-2">{item.line_no}</td>
                              <td className="py-1 pr-2">
                                <div className="font-medium">{item.product_name}</div>
                                <div className="text-slate-500">
                                  {item.category || "—"} · {item.product_id}
                                </div>
                              </td>
                              <td className="py-1 pr-2">{item.quantity}</td>
                              <td className="py-1 pr-2">₹ {Number(item.unit_price).toLocaleString("en-IN")}</td>
                              <td className="py-1">₹ {Number(item.line_amount).toLocaleString("en-IN")}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p>
                      Product: {String(detail.order.product_name)} x{String(detail.order.quantity)}
                    </p>
                  )}
                  <p>Amount: ₹ {Number(detail.order.amount).toLocaleString("en-IN")}</p>
                  <p>
                    IP: {displayPii(detail.order.ip_address, "ip", session?.analyst)}
                    {detail.blacklists.ip ? " (blacklisted)" : ""}
                  </p>
                  <p>Device: {String(detail.order.device_id)}</p>
                  <p>Placed At: {String(detail.order.order_timestamp)}</p>
                </div>
              </div>

              <Alert tone="warning">Flagged reason: {String(detail.order.flagged_reason)}</Alert>

              {!detail.blacklists.ip ? (
                <div className="rounded-lg border border-border p-4">
                  <p className="mb-2 text-sm font-medium">
                    Blacklist IP {displayPii(detail.order.ip_address, "ip", session?.analyst)}
                  </p>
                  <textarea
                    className="mb-2 w-full rounded-lg border border-border px-3 py-2 text-sm"
                    value={blacklistReason.ip}
                    onChange={(e) => setBlacklistReason((s) => ({ ...s, ip: e.target.value }))}
                    placeholder="Reason"
                    rows={2}
                  />
                  <Button
                    variant="secondary"
                    onClick={() => blacklist("ip").catch((e) => setError(e.message))}
                    disabled={!blacklistReason.ip.trim()}
                  >
                    Lock IP
                  </Button>
                </div>
              ) : null}

              {!detail.blacklists.phone ? (
                <div className="rounded-lg border border-border p-4">
                  <p className="mb-2 text-sm font-medium">
                    Blacklist Phone {displayPii(detail.order.phone_number, "phone", session?.analyst)}
                  </p>
                  <textarea
                    className="mb-2 w-full rounded-lg border border-border px-3 py-2 text-sm"
                    value={blacklistReason.phone}
                    onChange={(e) => setBlacklistReason((s) => ({ ...s, phone: e.target.value }))}
                    placeholder="Reason"
                    rows={2}
                  />
                  <Button
                    variant="secondary"
                    onClick={() => blacklist("phone").catch((e) => setError(e.message))}
                    disabled={!blacklistReason.phone.trim()}
                  >
                    Lock Phone
                  </Button>
                </div>
              ) : null}

              {!detail.blacklists.email ? (
                <div className="rounded-lg border border-border p-4">
                  <p className="mb-2 text-sm font-medium">
                    Blacklist Email {displayPii(detail.order.email, "email", session?.analyst)}
                  </p>
                  <textarea
                    className="mb-2 w-full rounded-lg border border-border px-3 py-2 text-sm"
                    value={blacklistReason.email}
                    onChange={(e) => setBlacklistReason((s) => ({ ...s, email: e.target.value }))}
                    placeholder="Reason"
                    rows={2}
                  />
                  <Button
                    variant="secondary"
                    onClick={() => blacklist("email").catch((e) => setError(e.message))}
                    disabled={!blacklistReason.email.trim()}
                  >
                    Lock Email
                  </Button>
                </div>
              ) : null}

              <div className="rounded-lg border border-border p-4">
                <p className="mb-2 text-sm font-medium">Analyst Decision</p>
                <textarea
                  className="mb-3 w-full rounded-lg border border-border px-3 py-2 text-sm"
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Review comments (required for rejection / fraud)"
                  rows={3}
                />
                <div className="flex flex-wrap gap-3">
                  <Button onClick={() => approve(activeOrderId).catch((e) => setError(e.message))}>
                    Approve Order
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => reject(activeOrderId, false).catch((e) => setError(e.message))}
                  >
                    Reject Order
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => reject(activeOrderId, true).catch((e) => setError(e.message))}
                  >
                    Mark as Fraud
                  </Button>
                </div>
              </div>
            </div>
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}
