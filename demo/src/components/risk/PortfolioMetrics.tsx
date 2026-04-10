import type { PortfolioMetrics as PortfolioMetricsType } from "../../types";

interface PortfolioMetricsProps {
  metrics: PortfolioMetricsType;
}

export function PortfolioMetrics({ metrics }: PortfolioMetricsProps) {
  const blocks = [
    ["Sharpe", metrics.sharpe.toFixed(2)],
    ["Sortino", metrics.sortino.toFixed(2)],
    ["Max drawdown", `${(metrics.maxDrawdown * 100).toFixed(1)}%`],
    ["VaR 1d 95%", `${(metrics.var95 * 100).toFixed(1)}%`],
    ["Gross exposure", `${metrics.grossExposure.toFixed(2)}x`],
    ["Net exposure", `${(metrics.netExposure * 100).toFixed(1)}%`],
  ];

  return (
    <div className="grid gap-3 md:grid-cols-3">
      {blocks.map(([k, v]) => (
        <article key={k} className="rounded-lg border border-line bg-panel/70 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">{k}</p>
          <p className="mt-1 text-2xl font-semibold text-white">{v}</p>
        </article>
      ))}
    </div>
  );
}
