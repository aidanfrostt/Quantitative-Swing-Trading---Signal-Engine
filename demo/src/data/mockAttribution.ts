import type { MoveAttribution } from "../types";

export function makeAttribution(rng: () => number, sectorEtf: string): MoveAttribution {
  const spy = (rng() - 0.5) * 0.05;
  const beta = 0.7 + rng() * 1.1;
  const market = spy * beta;
  const sector = (rng() - 0.5) * 0.03;
  const residual = (rng() - 0.5) * 0.04;
  return {
    spy_return_5d: Number(spy.toFixed(4)),
    sector_etf: sectorEtf,
    sector_etf_return_5d: Number((spy + sector).toFixed(4)),
    beta_spy: Number(beta.toFixed(2)),
    market_explained_5d: Number(market.toFixed(4)),
    sector_component_5d: Number((sector * beta).toFixed(4)),
    residual_5d: Number(residual.toFixed(4)),
    peer_percentile_sector: Number((rng() * 100).toFixed(1)),
    narrative: "5d move decomposes into macro beta, sector spread, and idiosyncratic residual.",
  };
}
