import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from "recharts";
import type { SectorRow } from "../../types";

interface DivergenceRadarProps {
  rows: SectorRow[];
}

export function DivergenceRadar({ rows }: DivergenceRadarProps) {
  const data = rows.map((r) => ({ sector: r.benchmark_etf, spread: Math.abs(r.weighted_sentiment_avg - r.etf_return_5d * 4) }));
  return (
    <div className="h-72 rounded-lg border border-line bg-panel/60 p-2">
      <p className="mb-1 text-xs text-slate-300">Cross-sector divergence radar</p>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data}>
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis dataKey="sector" stroke="#64748b" />
          <Radar dataKey="spread" stroke="#f8c15d" fill="#f8c15d44" fillOpacity={0.8} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
