import type { DemoData } from "../../types";
import { SignalCard } from "./SignalCard";
import { SignalTable } from "./SignalTable";

interface SignalDashboardProps {
  data: DemoData;
}

export function SignalDashboard({ data }: SignalDashboardProps) {
  return (
    <div className="space-y-6">
      <div className="grid gap-3 rounded-lg border border-line bg-panel/70 p-4 text-sm text-slate-200 md:grid-cols-4">
        <Metric label="SPY 5d" value={`${(data.regime.spy_return_5d * 100).toFixed(2)}%`} />
        <Metric label="QQQ 5d" value={`${(data.regime.qqq_return_5d * 100).toFixed(2)}%`} />
        <Metric label="VIX" value={data.regime.vix_close.toFixed(2)} />
        <Metric label="Buy dampening" value={data.regime.regime_buy_dampening.toFixed(2)} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <CardColumn title="Long candidates" rows={data.longCandidates} />
        <CardColumn title="Short candidates" rows={data.shortCandidates} />
        <CardColumn title="Watchlist" rows={data.watchlist} />
      </div>

      <SignalTable rows={data.signals} />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

function CardColumn({ title, rows }: { title: string; rows: DemoData["signals"] }) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm uppercase tracking-[0.12em] text-slate-300">{title}</h3>
      {rows.length === 0 ? <p className="text-sm text-slate-400">No rows in this simulation.</p> : null}
      {rows.slice(0, 3).map((r) => (
        <SignalCard key={`${title}-${r.ticker}`} record={r} />
      ))}
    </div>
  );
}
