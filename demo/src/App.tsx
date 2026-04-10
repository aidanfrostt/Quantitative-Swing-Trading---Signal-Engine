import { useMemo } from "react";
import { Footer } from "./components/layout/Footer";
import { Navbar } from "./components/layout/Navbar";
import { Section } from "./components/layout/Section";
import { Hero } from "./components/hero/Hero";
import { PipelineDiagram } from "./components/architecture/PipelineDiagram";
import { PipelineSteps } from "./components/pipeline/PipelineSteps";
import { SignalDashboard } from "./components/signals/SignalDashboard";
import { CandlestickChart } from "./components/charts/CandlestickChart";
import { IndicatorOverlay } from "./components/charts/IndicatorOverlay";
import { VolumeProfile } from "./components/charts/VolumeProfile";
import { SentimentTimeline } from "./components/sentiment/SentimentTimeline";
import { NewsArticleList } from "./components/sentiment/NewsArticleList";
import { PublisherWeighting } from "./components/sentiment/PublisherWeighting";
import { SectorHeatmap } from "./components/sectors/SectorHeatmap";
import { DivergenceRadar } from "./components/sectors/DivergenceRadar";
import { RegimeGauge } from "./components/regime/RegimeGauge";
import { RegimeTimeline } from "./components/regime/RegimeTimeline";
import { AttributionWaterfall } from "./components/attribution/AttributionWaterfall";
import { PeerPercentile } from "./components/attribution/PeerPercentile";
import { CorrelationMatrix } from "./components/risk/CorrelationMatrix";
import { PortfolioMetrics } from "./components/risk/PortfolioMetrics";
import { FactorExposure } from "./components/multi-factor/FactorExposure";
import { AlphaDecay } from "./components/multi-factor/AlphaDecay";
import { useSimulatedData } from "./hooks/useSimulatedData";

function App() {
  const { data, reseed } = useSimulatedData();
  const focus = useMemo(() => data.signals[0], [data.signals]);
  const focusBars = data.prices[focus.ticker] || [];

  return (
    <div className="min-h-screen bg-ink text-slate-100">
      <Navbar onSimulate={reseed} />
      <Hero />

      <Section
        id="architecture"
        title="Architecture Overview"
        subtitle="Interactive data-flow graph from market/news sources through batch services into storage and API output."
      >
        <PipelineDiagram />
      </Section>

      <Section
        id="pipeline"
        title="Pipeline Deep Dive"
        subtitle="12-step flow including three advanced extensions for correlation, optimization, and alpha decay analytics."
      >
        <PipelineSteps />
      </Section>

      <Section
        id="signals"
        title="Signal Dashboard"
        subtitle={`Simulated payload generated ${data.generatedAt.slice(0, 19).replace("T", " ")} UTC · ${data.universeVersion}`}
      >
        <SignalDashboard data={data} />
      </Section>

      <Section id="charts" title="Technical Analysis" subtitle={`Selected ticker ${focus.ticker} with candlesticks, RSI, MACD, and volume profile.`}>
        <div className="space-y-4">
          <CandlestickChart bars={focusBars} />
          <IndicatorOverlay bars={focusBars} />
          <VolumeProfile bars={focusBars} />
        </div>
      </Section>

      <Section id="sentiment" title="Sentiment Intelligence" subtitle="14-day sentiment wave, raw article stream, and publisher influence weighting.">
        <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr_1fr]">
          <SentimentTimeline news={data.news} />
          <NewsArticleList news={data.news} />
          <PublisherWeighting rows={data.publisherWeights} />
        </div>
      </Section>

      <Section id="sectors" title="Sector Context" subtitle="Heatmap of sector sentiment vs ETF performance with divergence diagnostics.">
        <div className="space-y-4">
          <SectorHeatmap rows={data.sectors} />
          <DivergenceRadar rows={data.sectors} />
        </div>
      </Section>

      <Section id="regime" title="Market Regime" subtitle="Tape-level controls that dampen positive conviction under stressed market conditions.">
        <div className="grid gap-4 lg:grid-cols-2">
          <RegimeGauge regime={data.regime} />
          <RegimeTimeline regime={data.regime} />
        </div>
      </Section>

      <Section id="attribution" title="Move Attribution" subtitle="Explain the latest 5d move across market, sector, and residual components.">
        <div className="grid gap-4 lg:grid-cols-2">
          <AttributionWaterfall record={focus} />
          <PeerPercentile record={focus} />
        </div>
      </Section>

      <Section id="factor" title="Factor Exposure + Alpha Decay" subtitle="Cross-sectional factor loadings and conviction half-life over forward horizons.">
        <div className="grid gap-4 lg:grid-cols-2">
          <FactorExposure rows={data.factorExposures} />
          <AlphaDecay rows={data.alphaDecay} />
        </div>
      </Section>

      <Section id="risk" title="Risk and Portfolio Metrics" subtitle="Correlation surface and portfolio-level risk diagnostics generated from simulated positions.">
        <div className="space-y-4">
          <CorrelationMatrix rows={data.correlationMatrix} />
          <PortfolioMetrics metrics={data.portfolio} />
        </div>
      </Section>

      <Footer />
    </div>
  );
}

export default App;
