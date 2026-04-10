import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface FactorExposureProps {
  rows: { ticker: string; momentum: number; value: number; quality: number; volatility: number }[];
}

export function FactorExposure({ rows }: FactorExposureProps) {
  return (
    <div className="h-72 rounded-lg border border-line bg-panel/60 p-2">
      <p className="mb-1 text-xs text-slate-300">Factor exposures (top names)</p>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="ticker" stroke="#64748b" />
          <YAxis stroke="#64748b" />
          <Tooltip />
          <Bar dataKey="momentum" fill="#22d3ee" />
          <Bar dataKey="value" fill="#a78bfa" />
          <Bar dataKey="quality" fill="#34d399" />
          <Bar dataKey="volatility" fill="#fb7185" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
