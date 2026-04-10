import type { SignalRecord } from "../types";
import { clamp } from "./random";
import { makeFundamentalScore } from "./mockFundamentals";
import { makeAttribution } from "./mockAttribution";

const sectorByTicker: Record<string, string> = {
  AAPL: "XLK",
  MSFT: "XLK",
  NVDA: "SOXX",
  AMD: "SOXX",
  META: "XLC",
  AMZN: "XLY",
  TSLA: "XLY",
  JPM: "XLF",
  BAC: "XLF",
  XOM: "XLE",
  UNH: "XLV",
  CAT: "XLI",
  DIS: "XLC",
  CRM: "XLK",
  AVGO: "SOXX",
  NFLX: "XLC",
  GS: "XLF",
  LIN: "XLB",
  NEE: "XLU",
  PLD: "XLRE",
};

export function makeSignals(tickers: string[], rng: () => number, dampening: number): SignalRecord[] {
  const records = tickers.map((ticker, idx) => {
    let technical = Number(((rng() - 0.5) * 2).toFixed(3));
    let sentiment = Number(((rng() - 0.5) * 2).toFixed(3));
    const fundamental = makeFundamentalScore(rng);

    if (idx < 3) {
      technical = Math.abs(technical) * 0.4 + 0.55;
      sentiment = Math.abs(sentiment) * 0.3 + 0.5;
    } else if (idx >= 3 && idx < 6) {
      technical = -(Math.abs(technical) * 0.4 + 0.55);
      sentiment = -(Math.abs(sentiment) * 0.3 + 0.45);
    }

    const blended = technical * 0.45 + sentiment * 0.35 + fundamental * 0.2;
    const adjusted = blended > 0 ? blended * dampening : blended;
    const conviction = Number(clamp(adjusted, -1, 1).toFixed(3));

    let action: SignalRecord["action"] = "HOLD";
    let position_intent: SignalRecord["position_intent"] = "flat";
    if (conviction >= 0.55) {
      action = "BUY";
      position_intent = "long";
    } else if (conviction <= -0.55) {
      action = "SELL";
      position_intent = "short";
    } else if (conviction <= -0.3) {
      action = "SELL";
      position_intent = "reduce_long";
    }

    const abs = Math.abs(conviction);
    const confidence_tier: SignalRecord["confidence_tier"] =
      abs > 0.7 ? "high" : abs > 0.4 ? "medium" : "low";

    return {
      ticker,
      action,
      position_intent,
      master_conviction: conviction,
      technical_score: technical,
      sentiment_score: sentiment,
      fundamental_score: fundamental,
      regime_adjustment: Number((conviction - blended).toFixed(4)),
      confidence_tier,
      evidence: [
        { label: "RSI", value: Number((30 + rng() * 40).toFixed(1)) },
        { label: "MACD", value: Number(((rng() - 0.5) * 3).toFixed(2)) },
        { label: "14d sentiment", value: sentiment },
      ],
      move_attribution: makeAttribution(rng, sectorByTicker[ticker] || "SPY"),
    };
  });

  return records.sort((a, b) => Math.abs(b.master_conviction) - Math.abs(a.master_conviction));
}
