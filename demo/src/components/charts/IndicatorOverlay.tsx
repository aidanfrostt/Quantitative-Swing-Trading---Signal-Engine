import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { OhlcvBar } from "../../types";

interface IndicatorOverlayProps {
  bars: OhlcvBar[];
}

function rsiSeries(bars: OhlcvBar[]) {
  return bars.map((b, i) => ({
    t: b.ts.slice(5, 10),
    rsi: 45 + Math.sin(i / 5) * 18,
    macd: Math.sin(i / 6) * 1.2,
  }));
}

export function IndicatorOverlay({ bars }: IndicatorOverlayProps) {
  const data = rsiSeries(bars);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="h-52 rounded-lg border border-line bg-panel/60 p-2">
        <p className="mb-1 text-xs text-slate-300">RSI(14)</p>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="t" hide />
            <YAxis domain={[0, 100]} stroke="#64748b" />
            <Tooltip />
            <Line dot={false} type="monotone" dataKey="rsi" stroke="#3ee6cf" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="h-52 rounded-lg border border-line bg-panel/60 p-2">
        <p className="mb-1 text-xs text-slate-300">MACD</p>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="t" hide />
            <YAxis stroke="#64748b" />
            <Tooltip />
            <Line dot={false} type="monotone" dataKey="macd" stroke="#f8c15d" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
