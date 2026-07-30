import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import type { AuditLogEntry } from "../types";
import { Alert, Button, Card, DataTable } from "../components/ui";

const PAGE_SIZE = 50;

function formatWhen(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function AuditLogTab() {
  const { t } = useI18n();
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [orderFilter, setOrderFilter] = useState("");
  const [appliedOrderId, setAppliedOrderId] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.auditLog({
        limit: PAGE_SIZE,
        offset,
        orderId: appliedOrderId,
      });
      setEntries(data.entries);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("audit_load_failed"));
      setEntries([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [appliedOrderId, offset, t]);

  useEffect(() => {
    void load();
  }, [load]);

  function applyFilter(e: FormEvent) {
    e.preventDefault();
    setOffset(0);
    const trimmed = orderFilter.trim();
    setAppliedOrderId(trimmed || undefined);
  }

  function clearFilter() {
    setOrderFilter("");
    setAppliedOrderId(undefined);
    setOffset(0);
  }

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const tableRows = entries as unknown as Record<string, unknown>[];

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">{t("audit_log_lede")}</p>

      <Card title={t("audit_filter_order")}>
        <form className="flex flex-wrap items-end gap-2" onSubmit={applyFilter}>
          <label className="text-sm">
            <span className="mb-1 block font-medium">{t("audit_filter_order")}</span>
            <input
              className="rounded-lg border border-border px-3 py-2 text-sm"
              value={orderFilter}
              onChange={(e) => setOrderFilter(e.target.value)}
              placeholder="ORD000123"
            />
          </label>
          <Button type="submit" variant="secondary">
            {t("audit_apply_filter")}
          </Button>
          {appliedOrderId ? (
            <Button type="button" variant="ghost" onClick={clearFilter}>
              {t("audit_clear_filter")}
            </Button>
          ) : null}
        </form>
      </Card>

      {error ? <Alert tone="error">{error}</Alert> : null}

      <Card title={t("audit_log_title")}>
        {loading ? (
          <p className="text-sm text-muted">{t("loading_ellipsis")}</p>
        ) : entries.length === 0 ? (
          <p className="text-sm text-muted">{t("audit_empty")}</p>
        ) : (
          <DataTable
            columns={[
              {
                key: "created_at",
                label: t("audit_col_when"),
                render: (row) => formatWhen(String(row.created_at ?? "")),
              },
              { key: "order_id", label: t("audit_col_order") },
              { key: "action", label: t("audit_col_action") },
              {
                key: "analyst_name",
                label: t("audit_col_analyst"),
                render: (row) => String(row.analyst_name || row.analyst_id || "SYSTEM"),
              },
              { key: "reason", label: t("audit_col_reason") },
              {
                key: "rule_name",
                label: t("audit_col_rule"),
                render: (row) => String(row.rule_name || "—"),
              },
              {
                key: "review_comments",
                label: t("audit_col_comments"),
                render: (row) => String(row.review_comments || "—"),
              },
              {
                key: "order_status",
                label: t("audit_col_status"),
                render: (row) => String(row.order_status || "—"),
              },
            ]}
            rows={tableRows}
          />
        )}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4 text-sm">
          <span className="text-muted">
            {t("audit_pagination", { page, totalPages, total })}
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              disabled={offset <= 0 || loading}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              {t("audit_prev")}
            </Button>
            <Button
              variant="secondary"
              disabled={offset + PAGE_SIZE >= total || loading}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              {t("audit_next")}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
