import type { SignalRecord } from "../../types";

interface PeerPercentileProps {
  record: SignalRecord;
}

export function PeerPercentile({ record }: PeerPercentileProps) {
  const pct = Math.max(0, Math.min(100, record.move_attribution.peer_percentile_sector));
  return (
    <div className="rounded-lg border border-line bg-panel/70 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">Peer percentile</p>
      <p className="mt-1 text-2xl font-semibold text-white">{pct.toFixed(1)}th</p>
      <div className="mt-3 h-3 rounded bg-slate-700">
        <div className="h-full rounded bg-indigo-400" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-2 text-sm text-slate-300">{record.move_attribution.narrative}</p>
    </div>
  );
}
