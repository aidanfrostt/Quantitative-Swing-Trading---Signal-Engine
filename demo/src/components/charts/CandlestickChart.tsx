import { useEffect, useRef } from "react";
import { CandlestickSeries, ColorType, createChart, type IChartApi } from "lightweight-charts";
import type { OhlcvBar } from "../../types";

interface CandlestickChartProps {
  bars: OhlcvBar[];
}

export function CandlestickChart({ bars }: CandlestickChartProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      layout: { background: { type: ColorType.Solid, color: "#0f152c" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#1d2747" }, horzLines: { color: "#1d2747" } },
      width: ref.current.clientWidth,
      height: 300,
      timeScale: { borderColor: "#334155" },
      rightPriceScale: { borderColor: "#334155" },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#3ee6cf",
      downColor: "#ff5f8f",
      borderVisible: false,
      wickUpColor: "#3ee6cf",
      wickDownColor: "#ff5f8f",
    });

    series.setData(
      bars.map((b) => ({
        time: b.ts.slice(0, 10),
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    );

    chart.timeScale().fitContent();
    chartRef.current = chart;

    const onResize = () => {
      if (!ref.current || !chartRef.current) return;
      chartRef.current.applyOptions({ width: ref.current.clientWidth });
    };

    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [bars]);

  return <div ref={ref} className="w-full overflow-hidden rounded-lg border border-line" />;
}
