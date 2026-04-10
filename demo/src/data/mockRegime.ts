import type { RegimeState } from "../types";

export function makeRegime(rng: () => number): RegimeState {
  const vix = 13 + rng() * 18;
  const damp = vix > 22 ? 0.68 : vix > 18 ? 0.82 : 1;
  return {
    spy_return_5d: Number(((rng() - 0.45) * 0.05).toFixed(4)),
    qqq_return_5d: Number(((rng() - 0.4) * 0.06).toFixed(4)),
    vix_close: Number(vix.toFixed(2)),
    regime_buy_dampening: Number(damp.toFixed(2)),
  };
}
