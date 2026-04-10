interface ConvictionBreakdownProps {
  technical: number;
  sentiment: number;
  fundamental: number;
  regimeAdjust: number;
}

function width(v: number) {
  return `${Math.min(100, Math.abs(v) * 48 + 6)}%`;
}

export function ConvictionBreakdown({ technical, sentiment, fundamental, regimeAdjust }: ConvictionBreakdownProps) {
  return (
    <div className="space-y-1 text-xs">
      <div className="grid grid-cols-[86px_1fr] items-center gap-2">
        <span className="text-slate-300">Tech</span>
        <span className="block h-2 rounded bg-cyan-400/70" style={{ width: width(technical) }} />
      </div>
      <div className="grid grid-cols-[86px_1fr] items-center gap-2">
        <span className="text-slate-300">Sentiment</span>
        <span className="block h-2 rounded bg-indigo-400/80" style={{ width: width(sentiment) }} />
      </div>
      <div className="grid grid-cols-[86px_1fr] items-center gap-2">
        <span className="text-slate-300">Fundamental</span>
        <span className="block h-2 rounded bg-emerald-400/80" style={{ width: width(fundamental) }} />
      </div>
      <div className="grid grid-cols-[86px_1fr] items-center gap-2">
        <span className="text-slate-300">Regime adj</span>
        <span className="block h-2 rounded bg-amber-400/80" style={{ width: width(regimeAdjust) }} />
      </div>
    </div>
  );
}
