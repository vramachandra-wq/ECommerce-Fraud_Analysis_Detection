import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import type { OrderDetail, QueueOrder } from "../types";
import { Alert, Button, Card, DataTable, MetricCard, StatusBadge } from "../components/ui";

export function DashboardPage() {
  const { session } = useAuth();
  const [orders, setOrders] = useState<QueueOrder[]>([]);
  const [metrics, setMetrics] = useState({ total: 0, pending_review: 0, on_hold: 0 });
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
      setMetrics(data.metrics);
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

  function toggleAll() {
    setSelected(allSelected ? [] : orders.map((o) => o.order_id));
  }

  async function approve(orderId: string) {
    await api.approveOrder({
      order_id: orderId,
      approved_at: new Date().toISOString(),
      reviewed_by: session!.analyst.analyst_id,
      review_comments: comments || null,
    });
    setComments("");
    await loadQueue();
  }

  async function reject(orderId: string, isFraud = true) {
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
      review_comments: batchComments || null,
    });
    setSelected([]);
    setBatchComments("");
    await loadQueue();
  }

  async function batchReject(isFraud = true) {
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
    const order = detail.order;
    const analystId = session!.analyst.analyst_id;
    if (entity === "ip") {
      await api.blacklistIp({
        ip_address: order.ip_address,
        reason: blacklistReason.ip,
        blacklisted_by: analystId,
      });
    } else if (entity === "phone") {
      await api.blacklistPhone({
        phone_number: order.phone_number,
        reason: blacklistReason.phone,
        blacklisted_by: analystId,
      });
    } else {
      await api.blacklistEmail({
        email: order.email,
        reason: blacklistReason.email,
        blacklisted_by: analystId,
      });
    }
    const refreshed = await api.orderDetail(activeOrderId);
    setDetail(refreshed);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Fraud Analyst Workspace</h1>
        <p className="text-sm text-muted">Logged in as {session?.analyst.employee_name}</p>
      </div>

      {notice ? <Alert tone="info">{notice}</Alert> : null}
      {error ? <Alert tone="error">{error}</Alert> : null}

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Total in Queue" value={metrics.total} />
        <MetricCard label="Pending Review" value={metrics.pending_review} />
        <MetricCard label="On Hold" value={metrics.on_hold} />
      </div>

      <Card title="Review Queue">
        {loading ? (
          <p className="text-sm text-muted">Loading queue...</p>
        ) : orders.length === 0 ? (
          <Alert tone="success">Queue is clear. No orders pending review.</Alert>
        ) : (
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
              { key: "product_name", label: "Product" },
              {
                key: "amount",
                label: "Amount",
                render: (row) => `₹ ${Number(row.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,
              },
              {
                key: "order_status",
                label: "Status",
                render: (row) => <StatusBadge status={String(row.order_status)} />,
              },
              { key: "order_timestamp", label: "Placed At" },
            ]}
            rows={orders as unknown as Record<string, unknown>[]}
          />
        )}
      </Card>

      {selected.length > 0 ? (
        <Card title={`Batch Actions (${selected.length} selected)`}>
          <textarea
            className="mb-3 w-full rounded-lg border border-border px-3 py-2 text-sm"
            placeholder="Batch review comments (required for rejection)"
            value={batchComments}
            onChange={(e) => setBatchComments(e.target.value)}
            rows={3}
          />
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => batchApprove().catch((e) => setError(e.message))}>Approve Selected</Button>
            <Button variant="danger" onClick={() => batchReject().catch((e) => setError(e.message))}>
              Reject Selected
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

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg bg-slate-50 p-4 text-sm">
                  <p className="mb-2 font-semibold">Customer Details</p>
                  <p>
                    {String(detail.order.customer_name)} ({String(detail.order.user_id)})
                  </p>
                  <p>
                    Email: {String(detail.order.email)}
                    {detail.blacklists.email ? " (blacklisted)" : ""}
                  </p>
                  <p>
                    Phone: {String(detail.order.phone_number)}
                    {detail.blacklists.phone ? " (blacklisted)" : ""}
                  </p>
                  <p>Address: {String(detail.order.address)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-4 text-sm">
                  <p className="mb-2 font-semibold">Order Details</p>
                  <p>
                    Product: {String(detail.order.product_name)} x{String(detail.order.quantity)}
                  </p>
                  <p>Amount: ₹ {Number(detail.order.amount).toLocaleString("en-IN")}</p>
                  <p>
                    IP: {String(detail.order.ip_address)}
                    {detail.blacklists.ip ? " (blacklisted)" : ""}
                  </p>
                  <p>Device: {String(detail.order.device_id)}</p>
                  <p>Placed At: {String(detail.order.order_timestamp)}</p>
                </div>
              </div>

              <Alert tone="warning">Flagged reason: {String(detail.order.flagged_reason)}</Alert>

              {!detail.blacklists.ip ? (
                <div className="rounded-lg border border-border p-4">
                  <p className="mb-2 text-sm font-medium">Blacklist IP {String(detail.order.ip_address)}</p>
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

              <div className="rounded-lg border border-border p-4">
                <p className="mb-2 text-sm font-medium">Analyst Decision</p>
                <textarea
                  className="mb-3 w-full rounded-lg border border-border px-3 py-2 text-sm"
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Review comments (required for rejection)"
                  rows={3}
                />
                <div className="flex gap-3">
                  <Button onClick={() => approve(activeOrderId).catch((e) => setError(e.message))}>
                    Approve Order
                  </Button>
                  <Button variant="danger" onClick={() => reject(activeOrderId).catch((e) => setError(e.message))}>
                    Reject Order
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
