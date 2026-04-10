import type { SectorRow } from "../../types";

interface SectorHeatmapProps {
  rows: SectorRow[];
}

function bg(v: number) {
  if (v > 0.4) return "bg-emerald-500/35";
  if (v > 0.1) return "bg-emerald-500/20";
  if (v < -0.4) return "bg-rose-500/35";
  if (v < -0.1) return "bg-rose-500/20";
  return "bg-slate-700/35";
}

export function SectorHeatmap({ rows }: SectorHeatmapProps) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {rows.map((r) => (
        <article key={r.sector_key} className={`rounded-lg border border-line p-3 ${bg(r.weighted_sentiment_avg)}`}>
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold capitalize text-white">{r.sector_key.replaceAll("_", " ")}</h3>
            <span className="text-xs text-slate-300">{r.benchmark_etf}</span>
          </div>
          <p className="mt-2 text-xs text-slate-200">Sentiment: {r.weighted_sentiment_avg.toFixed(3)}</p>
          <p className="text-xs text-slate-200">ETF 5d: {(r.etf_return_5d * 100).toFixed(2)}%</p>
          <p className="text-xs text-slate-300">z-score: {r.sentiment_z_cross_sector.toFixed(2)}</p>
          {r.divergence_flag ? <p className="mt-2 text-xs text-amber-300">Divergence flagged</p> : null}
        </article>
      ))}
    </div>
  );
}
