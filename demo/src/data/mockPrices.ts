import type { OhlcvBar } from "../types";

export function makePrices(ticker: string, days: number, seedRng: () => number): OhlcvBar[] {
  const bars: OhlcvBar[] = [];
  let close = 40 + seedRng() * 260;
  const now = new Date();

  for (let i = days - 1; i >= 0; i -= 1) {
    const dt = new Date(now);
    dt.setDate(now.getDate() - i);
    const drift = 0.0004;
    const vol = 0.02;
    const shock = (seedRng() - 0.5) * 2;
    const ret = drift + shock * vol;
    const open = close;
    close = Math.max(4, close * (1 + ret));
    const high = Math.max(open, close) * (1 + seedRng() * 0.012);
    const low = Math.min(open, close) * (1 - seedRng() * 0.012);
    bars.push({
      ts: dt.toISOString(),
      open,
      high,
      low,
      close,
      volume: Math.round(800_000 + seedRng() * 6_000_000),
    });
  }

  if (ticker === "NVDA") {
    for (let j = bars.length - 30; j < bars.length; j += 1) {
      bars[j].close *= 1.002;
      bars[j].high *= 1.004;
    }
  }

  return bars;
}
