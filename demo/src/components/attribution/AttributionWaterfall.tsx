import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SignalRecord } from "../../types";

interface AttributionWaterfallProps {
  record: SignalRecord;
}

export function AttributionWaterfall({ record }: AttributionWaterfallProps) {
  const a = record.move_attribution;
  const rows = [
    { name: "Market", value: a.market_explained_5d },
    { name: "Sector", value: a.sector_component_5d },
    { name: "Residual", value: a.residual_5d },
  ];

  return (
    <div className="h-64 rounded-lg border border-line bg-panel/60 p-2">
      <p className="mb-1 text-xs text-slate-300">5d move attribution for {record.ticker}</p>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows}>
          <XAxis dataKey="name" stroke="#64748b" />
          <YAxis stroke="#64748b" />
          <Tooltip />
          <Bar dataKey="value">
            {rows.map((r) => (
              <Cell key={r.name} fill={r.value >= 0 ? "#34d399" : "#fb7185"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
