import { FormEvent, useMemo, useState } from "react";
import { api } from "../api";
import type { ChatMessage, ChatResponse } from "../types";
import { Alert, Button, Card, DataTable } from "../components/ui";

const EXAMPLES = [
  "Total fraudulent orders",
  "Fraud rate by state",
  "Top 10 customers by spending",
  "Revenue by product category",
  "Fraud orders by device type",
];

function ChartBlock({ chart }: { chart: NonNullable<ChatResponse["chart"]> }) {
  if (chart.type === "metric") {
    return (
      <div className="rounded-xl bg-white px-4 py-3 ring-1 ring-border">
        <p className="text-2xl font-bold">{String(chart.value ?? chart.values?.[0] ?? "—")}</p>
        <p className="text-xs text-muted">{chart.label || chart.y_label || "Result"}</p>
      </div>
    );
  }

  const labels = chart.labels || [];
  const values = (chart.values || []).map(Number);
  const max = Math.max(...values, 1);

  return (
    <div className="space-y-2 rounded-xl bg-white p-3 ring-1 ring-border">
      {labels.slice(0, 8).map((label, idx) => (
        <div key={`${label}-${idx}`}>
          <div className="mb-1 flex justify-between gap-3 text-xs">
            <span className="truncate font-medium">{label}</span>
            <span className="tabular-nums text-muted">{values[idx]?.toLocaleString?.() ?? values[idx]}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-blue-500"
              style={{ width: `${Math.max(((values[idx] || 0) / max) * 100, 2)}%` }}
            />
          </div>
        </div>
      ))}
      {(chart.x_label || chart.y_label) && (
        <p className="pt-1 text-[11px] text-muted">
          {chart.x_label || "X"} vs {chart.y_label || "Y"}
        </p>
      )}
    </div>
  );
}

export function ChatbotPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canSend = useMemo(() => Boolean(input.trim()) && !loading, [input, loading]);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;
    setError("");
    const userMessage: ChatMessage = { role: "user", content: text.trim() };
    const history = messages.map((m) => ({
      role: m.role,
      content: m.content,
      sql: m.sql ?? null,
      df: m.rows ?? m.df ?? null,
    }));
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    try {
      const response = await api.chat(text.trim(), history);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.content,
          status: response.status,
          sql: response.sql,
          rows: response.rows ?? null,
          df: response.rows ?? null,
          chart: response.chart ?? null,
          followups: response.followups ?? [],
          business_advice: response.business_advice ?? [],
          insight_title: response.insight_title ?? "AI Insights",
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">AI Analytics Chatbot</h1>
        <p className="text-sm text-muted">Ask natural-language questions about orders, fraud, and revenue.</p>
      </div>

      <Card title="Example Questions">
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <Button key={example} variant="secondary" onClick={() => sendMessage(example)} disabled={loading}>
              {example}
            </Button>
          ))}
        </div>
      </Card>

      {error ? <Alert tone="error">{error}</Alert> : null}

      <Card title="Conversation">
        <div className="mb-4 max-h-[560px] space-y-4 overflow-y-auto">
          {messages.length === 0 ? (
            <p className="text-sm text-muted">No messages yet. Ask a question to get started.</p>
          ) : (
            messages.map((message, idx) => (
              <div
                key={idx}
                className={`rounded-xl px-4 py-3 text-sm ${
                  message.role === "user" ? "ml-12 bg-brand text-white" : "mr-8 bg-slate-100 text-slate-900"
                }`}
              >
                {message.role === "assistant" && message.insight_title ? (
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {message.insight_title}
                  </p>
                ) : null}
                <p className="whitespace-pre-wrap">{message.content}</p>

                {message.chart ? (
                  <div className="mt-3">
                    <ChartBlock chart={message.chart} />
                  </div>
                ) : null}

                {message.business_advice && message.business_advice.length > 0 ? (
                  <div className="mt-3 rounded-lg bg-white/70 p-3 ring-1 ring-border">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Business Advice
                    </p>
                    <ul className="list-disc space-y-1 pl-4">
                      {message.business_advice.map((tip) => (
                        <li key={tip}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {message.rows && message.rows.length > 0 ? (
                  <div className="mt-3 overflow-x-auto rounded-lg bg-white p-2 ring-1 ring-border">
                    <DataTable
                      columns={Object.keys(message.rows[0]).map((key) => ({ key, label: key }))}
                      rows={message.rows}
                    />
                  </div>
                ) : null}

                {message.followups && message.followups.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {message.followups.map((q) => (
                      <Button
                        key={q}
                        variant="secondary"
                        onClick={() => sendMessage(q)}
                        disabled={loading}
                      >
                        {q}
                      </Button>
                    ))}
                  </div>
                ) : null}
              </div>
            ))
          )}
          {loading ? <p className="text-sm text-muted">Analyzing your question…</p> : null}
        </div>

        <form onSubmit={onSubmit} className="flex gap-3">
          <input
            className="flex-1 rounded-lg border border-border px-3 py-2 text-sm"
            placeholder="Ask about orders, fraud, revenue..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <Button type="submit" disabled={!canSend}>
            {loading ? "Thinking..." : "Send"}
          </Button>
          <Button type="button" variant="secondary" onClick={() => setMessages([])} disabled={loading}>
            Clear
          </Button>
        </form>
      </Card>
    </div>
  );
}
