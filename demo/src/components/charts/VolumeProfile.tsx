import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { OhlcvBar } from "../../types";

interface VolumeProfileProps {
  bars: OhlcvBar[];
}

export function VolumeProfile({ bars }: VolumeProfileProps) {
  const data = bars.slice(-30).map((b) => ({ t: b.ts.slice(5, 10), v: b.volume }));
  return (
    <div className="h-44 rounded-lg border border-line bg-panel/60 p-2">
      <p className="mb-1 text-xs text-slate-300">Volume profile (30d)</p>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <XAxis dataKey="t" hide />
          <YAxis stroke="#64748b" tickFormatter={(x) => `${Math.round(Number(x) / 1_000_000)}M`} />
          <Tooltip formatter={(v) => Number(v).toLocaleString()} />
          <Bar dataKey="v" fill="#7dd3fc" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
