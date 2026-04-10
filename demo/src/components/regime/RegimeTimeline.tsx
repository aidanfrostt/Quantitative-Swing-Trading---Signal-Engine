import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { RegimeState } from "../../types";

interface RegimeTimelineProps {
  regime: RegimeState;
}

export function RegimeTimeline({ regime }: RegimeTimelineProps) {
  const data = Array.from({ length: 18 }, (_, i) => ({
    t: `d-${18 - i}`,
    vix: Math.max(10, regime.vix_close + Math.sin(i / 2.8) * 3.8),
    damp: Math.max(0.6, Math.min(1, regime.regime_buy_dampening + Math.cos(i / 4) * 0.08)),
  }));

  return (
    <div className="space-y-3">
      <div className="h-32 rounded-lg border border-line bg-panel/60 p-2">
        <p className="mb-1 text-xs text-slate-300">VIX level</p>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="t" hide />
            <YAxis domain={["dataMin - 2", "dataMax + 2"]} stroke="#64748b" />
            <Tooltip />
            <Line dataKey="vix" stroke="#f97316" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="h-32 rounded-lg border border-line bg-panel/60 p-2">
        <p className="mb-1 text-xs text-slate-300">Buy dampening factor</p>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="t" hide />
            <YAxis domain={[0.5, 1.05]} stroke="#64748b" />
            <Tooltip />
            <Line dataKey="damp" stroke="#10b981" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
