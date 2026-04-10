import { useMemo, useState } from "react";
import type { SignalRecord } from "../../types";

type SortKey = "ticker" | "master_conviction" | "technical_score" | "sentiment_score";

interface SignalTableProps {
  rows: SignalRecord[];
}

export function SignalTable({ rows }: SignalTableProps) {
  const [key, setKey] = useState<SortKey>("master_conviction");

  const sorted = useMemo(() => {
    return [...rows].sort((a, b) => {
      if (key === "ticker") return a.ticker.localeCompare(b.ticker);
      return Math.abs(b[key]) - Math.abs(a[key]);
    });
  }, [rows, key]);

  return (
    <div className="overflow-auto rounded-lg border border-line">
      <table className="min-w-full text-left text-xs">
        <thead className="bg-[#111a31] text-slate-300">
          <tr>
            {[
              ["ticker", "Ticker"],
              ["master_conviction", "Conviction"],
              ["technical_score", "Tech"],
              ["sentiment_score", "Sentiment"],
            ].map(([k, label]) => (
              <th key={k} className="cursor-pointer px-3 py-2" onClick={() => setKey(k as SortKey)}>
                {label}
              </th>
            ))}
            <th className="px-3 py-2">Action</th>
            <th className="px-3 py-2">Intent</th>
            <th className="px-3 py-2">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.ticker} className="border-t border-line/60 text-slate-200">
              <td className="px-3 py-2 font-medium">{r.ticker}</td>
              <td className="px-3 py-2">{r.master_conviction.toFixed(3)}</td>
              <td className="px-3 py-2">{r.technical_score.toFixed(2)}</td>
              <td className="px-3 py-2">{r.sentiment_score.toFixed(2)}</td>
              <td className="px-3 py-2">{r.action}</td>
              <td className="px-3 py-2">{r.position_intent}</td>
              <td className="px-3 py-2">{r.confidence_tier}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
