import { motion } from "framer-motion";

const steps = [
  ["01", "universe_cron", "Builds filtered symbols and sector mapping."],
  ["02", "price_ingest", "Pulls OHLCV bars and benchmark ETFs."],
  ["03", "technical_engine", "Computes RSI, MACD, Bollinger, VWAP."],
  ["04", "news_ingest", "Ingests Perigon articles and ticker links."],
  ["05", "nlp_worker", "Runs FinBERT sentiment and noise flags."],
  ["06", "fundamentals_ingest", "Scores ROE, valuation, debt, growth."],
  ["07", "attribution_job", "Decomposes 5d move vs market/sector."],
  ["08", "sector_sentiment_job", "Aggregates sentiment by sector."],
  ["09", "signal_api", "Blends signals and classifies actions."],
  ["10", "cross_correlation_engine", "Rolling Pearson matrix + factor loadings."],
  ["11", "portfolio_optimizer", "Risk-parity weights with VaR guardrails."],
  ["12", "alpha_decay_tracker", "Measures conviction decay over forward windows."],
] as const;

export function PipelineSteps() {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {steps.map((s, idx) => (
        <motion.article
          key={s[1]}
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.25, delay: idx * 0.03 }}
          className="rounded-lg border border-line bg-panel/70 p-4"
        >
          <p className="text-xs text-mint">{s[0]}</p>
          <h3 className="mt-1 text-lg font-semibold text-white">{s[1]}</h3>
          <p className="mt-2 text-sm text-slate-300">{s[2]}</p>
        </motion.article>
      ))}
    </div>
  );
}
