import { useMemo } from "react";

interface CorrelationMatrixProps {
  rows: { x: string; y: string; value: number }[];
}

function cellBg(v: number) {
  if (v > 0.8) return "rgba(52,211,153,0.7)";
  if (v > 0.4) return "rgba(52,211,153,0.45)";
  if (v > 0.1) return "rgba(52,211,153,0.2)";
  if (v < -0.4) return "rgba(251,113,133,0.55)";
  if (v < -0.1) return "rgba(251,113,133,0.25)";
  return "rgba(100,116,139,0.18)";
}

export function CorrelationMatrix({ rows }: CorrelationMatrixProps) {
  const labels = useMemo(() => [...new Set(rows.map((r) => r.x))], [rows]);
  const lookup = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of rows) m.set(`${r.x}|${r.y}`, r.value);
    return m;
  }, [rows]);

  const cols = labels.length + 1;

  return (
    <div className="overflow-auto rounded-lg border border-line bg-panel/70 p-3">
      <p className="mb-3 text-xs text-slate-300">Rolling Pearson correlation matrix</p>
      <div
        className="grid gap-[3px] text-[10px]"
        style={{ gridTemplateColumns: `64px repeat(${labels.length}, minmax(0,1fr))`, minWidth: cols * 56 }}
      >
        <div />
        {labels.map((l) => (
          <div key={`h-${l}`} className="text-center font-medium text-slate-400">{l}</div>
        ))}
        {labels.map((x) => (
          <div key={x} className="contents">
            <div className="flex items-center text-slate-400 font-medium">{x}</div>
            {labels.map((y) => {
              const v = lookup.get(`${x}|${y}`) ?? 0;
              return (
                <div
                  key={`${x}-${y}`}
                  className="flex items-center justify-center rounded py-1.5 text-white"
                  style={{ background: cellBg(v) }}
                >
                  {v.toFixed(2)}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
