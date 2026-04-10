export type SignalAction = "BUY" | "SELL" | "HOLD";
export type PositionIntent = "long" | "short" | "reduce_long" | "flat";

export interface EvidenceItem {
  label: string;
  value: string | number;
}

export interface MoveAttribution {
  spy_return_5d: number;
  sector_etf: string;
  sector_etf_return_5d: number;
  beta_spy: number;
  market_explained_5d: number;
  sector_component_5d: number;
  residual_5d: number;
  peer_percentile_sector: number;
  narrative: string;
}

export interface SignalRecord {
  ticker: string;
  action: SignalAction;
  position_intent: PositionIntent;
  master_conviction: number;
  technical_score: number;
  sentiment_score: number;
  fundamental_score: number;
  regime_adjustment: number;
  confidence_tier: "high" | "medium" | "low";
  evidence: EvidenceItem[];
  move_attribution: MoveAttribution;
}

export interface SectorRow {
  sector_key: string;
  benchmark_etf: string;
  weighted_sentiment_avg: number;
  etf_return_5d: number;
  sentiment_z_cross_sector: number;
  divergence_flag: boolean;
}

export interface NewsItem {
  id: string;
  ticker: string;
  source: string;
  headline: string;
  score: number;
  is_noise: boolean;
  published_at: string;
}

export interface OhlcvBar {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface RegimeState {
  spy_return_5d: number;
  qqq_return_5d: number;
  vix_close: number;
  regime_buy_dampening: number;
}

export interface PortfolioMetrics {
  sharpe: number;
  sortino: number;
  maxDrawdown: number;
  var95: number;
  grossExposure: number;
  netExposure: number;
}

export interface FactorExposure {
  ticker: string;
  momentum: number;
  value: number;
  quality: number;
  volatility: number;
}

export interface DemoData {
  generatedAt: string;
  universeVersion: string;
  signals: SignalRecord[];
  longCandidates: SignalRecord[];
  shortCandidates: SignalRecord[];
  watchlist: SignalRecord[];
  sectors: SectorRow[];
  news: NewsItem[];
  prices: Record<string, OhlcvBar[]>;
  regime: RegimeState;
  publisherWeights: { name: string; influence: number }[];
  correlationMatrix: { x: string; y: string; value: number }[];
  factorExposures: FactorExposure[];
  alphaDecay: { day: number; conviction: number }[];
  portfolio: PortfolioMetrics;
}
