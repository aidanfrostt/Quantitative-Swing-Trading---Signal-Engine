import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { NewsItem } from "../../types";

interface SentimentTimelineProps {
  news: NewsItem[];
}

export function SentimentTimeline({ news }: SentimentTimelineProps) {
  const points = news.slice(0, 40).map((n) => ({
    t: n.published_at.slice(5, 10),
    score: n.score,
  }));

  return (
    <div className="h-60 rounded-lg border border-line bg-panel/60 p-2">
      <p className="mb-1 text-xs text-slate-300">14d rolling sentiment timeline</p>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points.reverse()}>
          <XAxis dataKey="t" hide />
          <YAxis domain={[-1, 1]} stroke="#64748b" />
          <Tooltip />
          <Area type="monotone" dataKey="score" stroke="#818cf8" fill="#818cf855" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
