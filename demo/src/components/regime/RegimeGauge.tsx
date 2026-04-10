import type { RegimeState } from "../../types";

interface RegimeGaugeProps {
  regime: RegimeState;
}

export function RegimeGauge({ regime }: RegimeGaugeProps) {
  const riskOn = regime.regime_buy_dampening >= 0.95;
  return (
    <div className="rounded-lg border border-line bg-panel/70 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">Regime state</p>
      <p className="mt-1 text-2xl font-semibold text-white">{riskOn ? "Risk-on" : "Risk-off dampening"}</p>
      <div className="mt-4 h-3 w-full rounded bg-slate-700">
        <div
          className={`h-full rounded ${riskOn ? "bg-emerald-400" : "bg-amber-400"}`}
          style={{ width: `${Math.round(regime.regime_buy_dampening * 100)}%` }}
        />
      </div>
      <p className="mt-2 text-sm text-slate-300">Buy dampening factor: {regime.regime_buy_dampening.toFixed(2)}</p>
    </div>
  );
}
