import type { NewsItem } from "../types";
import { pick } from "./random";

const sources = ["Reuters", "Bloomberg", "WSJ", "Financial Times", "MarketWatch", "CNBC"];
const templates = [
  "{ticker} beats earnings expectations as margins expand",
  "Analysts debate valuation reset in {ticker}",
  "{ticker} announces partnership to scale AI infrastructure",
  "Options activity spikes as traders reprice {ticker}",
  "Sector peers move after guidance update from {ticker}",
  "New product cycle could shift demand for {ticker}",
];

export function makeNews(tickers: string[], rng: () => number): NewsItem[] {
  const items: NewsItem[] = [];
  const now = Date.now();
  for (let i = 0; i < 80; i += 1) {
    const ticker = pick(tickers, rng);
    const headline = pick(templates, rng).replace("{ticker}", ticker);
    const score = Number(((rng() - 0.5) * 2).toFixed(3));
    const msBack = Math.floor(rng() * 1000 * 60 * 60 * 24 * 14);
    items.push({
      id: `news-${i}`,
      ticker,
      source: pick(sources, rng),
      headline,
      score,
      is_noise: rng() < 0.16,
      published_at: new Date(now - msBack).toISOString(),
    });
  }
  return items.sort((a, b) => b.published_at.localeCompare(a.published_at));
}
