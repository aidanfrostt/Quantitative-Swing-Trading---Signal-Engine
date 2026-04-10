import type { DemoData } from "../types";
import { createRng } from "./random";
import { makePrices } from "./mockPrices";
import { makeRegime } from "./mockRegime";
import { makeSignals } from "./mockSignals";
import { makeSectors } from "./mockSectors";
import { makeNews } from "./mockNews";

const tickers = [
  "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "TSLA", "JPM", "BAC", "XOM",
  "UNH", "CAT", "DIS", "CRM", "AVGO", "NFLX", "GS", "LIN", "NEE", "PLD",
];

export function buildDemoData(seed = Date.now()): DemoData {
  const rng = createRng(seed);
  const regime = makeRegime(rng);
  const signals = makeSignals(tickers, rng, regime.regime_buy_dampening);
  const prices = Object.fromEntries(tickers.map((t) => [t, makePrices(t, 120, rng)]));
  const sectors = makeSectors(rng);
  const news = makeNews(tickers, rng);

  const publisherWeights = [
    { name: "Reuters", influence: 1.2 },
    { name: "Bloomberg", influence: 1.15 },
    { name: "WSJ", influence: 1.05 },
    { name: "Financial Times", influence: 1.0 },
    { name: "CNBC", influence: 0.92 },
    { name: "MarketWatch", influence: 0.85 },
  ];

  const corrTickers = tickers.slice(0, 8);
  const correlationMatrix = corrTickers.flatMap((x) =>
    corrTickers.map((y) => ({
      x,
      y,
      value: x === y ? 1 : Number(((rng() - 0.5) * 1.9).toFixed(2)),
    })),
  );

  const factorExposures = signals.slice(0, 10).map((s) => ({
    ticker: s.ticker,
    momentum: Number(((rng() - 0.2) * 2).toFixed(2)),
    value: Number(((rng() - 0.5) * 2).toFixed(2)),
    quality: Number(((rng() - 0.35) * 2).toFixed(2)),
    volatility: Number(((rng() - 0.5) * 2).toFixed(2)),
  }));

  const alphaDecay = [1, 3, 5, 10].map((day, i) => ({
    day,
    conviction: Number((Math.max(0.16, 0.94 - i * 0.18 + (rng() - 0.5) * 0.06)).toFixed(2)),
  }));

  return {
    generatedAt: new Date().toISOString(),
    universeVersion: `uv-${new Date().toISOString().slice(0, 10)}`,
    signals,
    longCandidates: signals.filter((s) => s.action === "BUY").slice(0, 6),
    shortCandidates: signals.filter((s) => s.position_intent === "short").slice(0, 6),
    watchlist: signals.filter((s) => s.action === "HOLD" && Math.abs(s.master_conviction) > 0.4).slice(0, 6),
    sectors,
    news,
    prices,
    regime,
    publisherWeights,
    correlationMatrix,
    factorExposures,
    alphaDecay,
    portfolio: {
      sharpe: Number((0.9 + rng() * 1.1).toFixed(2)),
      sortino: Number((1.1 + rng() * 1.4).toFixed(2)),
      maxDrawdown: Number((-(0.06 + rng() * 0.13)).toFixed(3)),
      var95: Number((0.012 + rng() * 0.028).toFixed(3)),
      grossExposure: Number((1.1 + rng() * 0.8).toFixed(2)),
      netExposure: Number(((rng() - 0.5) * 0.7).toFixed(2)),
    },
  };
}
