import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface AlphaDecayProps {
  rows: { day: number; conviction: number }[];
}

export function AlphaDecay({ rows }: AlphaDecayProps) {
  return (
    <div className="h-64 rounded-lg border border-line bg-panel/60 p-2">
      <p className="mb-1 text-xs text-slate-300">Alpha decay curve</p>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows}>
          <XAxis dataKey="day" stroke="#64748b" />
          <YAxis domain={[0, 1]} stroke="#64748b" />
          <Tooltip />
          <Line dataKey="conviction" stroke="#f8c15d" strokeWidth={2.5} dot />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
