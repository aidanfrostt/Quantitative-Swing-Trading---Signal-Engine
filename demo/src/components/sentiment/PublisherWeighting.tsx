import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface PublisherWeightingProps {
  rows: { name: string; influence: number }[];
}

export function PublisherWeighting({ rows }: PublisherWeightingProps) {
  return (
    <div className="h-72 rounded-lg border border-line bg-panel/60 p-2">
      <p className="mb-1 text-xs text-slate-300">Publisher influence weighting</p>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ left: 12 }}>
          <XAxis type="number" stroke="#64748b" domain={[0, 1.4]} />
          <YAxis type="category" width={90} dataKey="name" stroke="#64748b" />
          <Tooltip />
          <Bar dataKey="influence" fill="#34d399" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
