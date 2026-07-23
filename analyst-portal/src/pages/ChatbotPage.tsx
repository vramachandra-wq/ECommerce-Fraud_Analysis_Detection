import { FormEvent, useState } from "react";
import { api } from "../api";
import type { ChatMessage } from "../types";
import { Alert, Button, Card, DataTable } from "../components/ui";

const EXAMPLES = [
  "Total fraudulent orders",
  "Fraud rate by state",
  "Top 10 customers by spending",
  "Revenue by product category",
  "Fraud orders by device type",
];

export function ChatbotPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function sendMessage(text: string) {
    if (!text.trim()) return;
    setError("");
    const userMessage: ChatMessage = { role: "user", content: text.trim() };
    const history = [...messages, userMessage].map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    try {
      const response = await api.chat(text.trim(), history.slice(0, -1));
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.content,
          sql: response.sql,
          rows: response.rows ?? null,
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
        <div className="mb-4 max-h-[480px] space-y-4 overflow-y-auto">
          {messages.length === 0 ? (
            <p className="text-sm text-muted">No messages yet. Ask a question to get started.</p>
          ) : (
            messages.map((message, idx) => (
              <div
                key={idx}
                className={`rounded-xl px-4 py-3 text-sm ${
                  message.role === "user" ? "ml-12 bg-brand text-white" : "mr-12 bg-slate-100 text-slate-900"
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                {message.sql ? (
                  <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                    {message.sql}
                  </pre>
                ) : null}
                {message.rows && message.rows.length > 0 ? (
                  <div className="mt-3">
                    <DataTable
                      columns={Object.keys(message.rows[0]).map((key) => ({ key, label: key }))}
                      rows={message.rows}
                    />
                  </div>
                ) : null}
              </div>
            ))
          )}
        </div>

        <form onSubmit={onSubmit} className="flex gap-3">
          <input
            className="flex-1 rounded-lg border border-border px-3 py-2 text-sm"
            placeholder="Ask about orders, fraud, revenue..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <Button type="submit" disabled={loading}>
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
