import { useEffect, useState } from "react";
import { api } from "../api";
import { Alert, Card } from "../components/ui";

export function PowerBIPage() {
  const [embedUrl, setEmbedUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .powerBi()
      .then((data) => setEmbedUrl(data.embed_url))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load Power BI"));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Analytics Dashboards</h1>
        <p className="text-sm text-muted">Embedded Power BI reporting</p>
      </div>

      {error ? <Alert tone="error">{error}</Alert> : null}

      <Card title="Power BI Report">
        {embedUrl ? (
          <div className="aspect-video w-full overflow-hidden rounded-xl border border-border bg-slate-100">
            <iframe title="E-commerce Fraud Analysis" src={embedUrl} className="h-full w-full border-0" allowFullScreen />
          </div>
        ) : (
          <p className="text-sm text-muted">Loading embed...</p>
        )}
      </Card>
    </div>
  );
}
