import type { SectorRow } from "../types";

const sectors = [
  ["technology", "XLK"],
  ["semiconductors", "SOXX"],
  ["financials", "XLF"],
  ["healthcare", "XLV"],
  ["industrials", "XLI"],
  ["consumer_discretionary", "XLY"],
  ["communication_services", "XLC"],
  ["utilities", "XLU"],
  ["energy", "XLE"],
  ["materials", "XLB"],
  ["real_estate", "XLRE"],
] as const;

export function makeSectors(rng: () => number): SectorRow[] {
  return sectors.map(([sector_key, benchmark_etf]) => {
    const weighted_sentiment_avg = Number(((rng() - 0.5) * 1.6).toFixed(3));
    const etf_return_5d = Number(((rng() - 0.5) * 0.08).toFixed(4));
    return {
      sector_key,
      benchmark_etf,
      weighted_sentiment_avg,
      etf_return_5d,
      sentiment_z_cross_sector: Number(((rng() - 0.5) * 3).toFixed(3)),
      divergence_flag:
        Math.sign(weighted_sentiment_avg) !== Math.sign(etf_return_5d) && Math.abs(weighted_sentiment_avg) > 0.25,
    };
  });
}
