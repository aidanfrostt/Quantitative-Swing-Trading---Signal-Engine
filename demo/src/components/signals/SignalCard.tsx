import type { SignalRecord } from "../../types";
import { ConvictionBreakdown } from "./ConvictionBreakdown";

interface SignalCardProps {
  record: SignalRecord;
}

export function SignalCard({ record }: SignalCardProps) {
  const conv = Math.round(record.master_conviction * 100);
  const color = record.master_conviction >= 0 ? "text-mint" : "text-rose";

  return (
    <article className="rounded-lg border border-line bg-panel/70 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold text-white">{record.ticker}</h3>
        <span className={`text-xs font-semibold uppercase ${color}`}>{record.action}</span>
      </div>
      <p className="mt-1 text-sm text-slate-300">intent: {record.position_intent}</p>
      <p className={`mt-2 text-3xl font-semibold ${color}`}>{conv}%</p>
      <p className="text-xs text-slate-400">master conviction</p>
      <div className="mt-3">
        <ConvictionBreakdown
          technical={record.technical_score}
          sentiment={record.sentiment_score}
          fundamental={record.fundamental_score}
          regimeAdjust={record.regime_adjustment}
        />
      </div>
      <div className="mt-3 flex flex-wrap gap-1 text-xs">
        {record.evidence.map((e) => (
          <span key={e.label} className="rounded border border-line px-2 py-1 text-slate-300">
            {e.label}: {e.value}
          </span>
        ))}
      </div>
    </article>
  );
}
