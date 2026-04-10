import type { NewsItem } from "../../types";

interface NewsArticleListProps {
  news: NewsItem[];
}

export function NewsArticleList({ news }: NewsArticleListProps) {
  return (
    <div className="rounded-lg border border-line bg-panel/60 p-3">
      <p className="mb-2 text-xs text-slate-300">Article stream</p>
      <div className="max-h-72 space-y-2 overflow-auto pr-1 text-sm">
        {news.slice(0, 16).map((n) => (
          <article key={n.id} className={`rounded border px-2 py-2 ${n.is_noise ? "border-slate-700 opacity-60" : "border-line"}`}>
            <div className="flex items-center justify-between gap-2">
              <p className="font-medium text-slate-100">{n.ticker}</p>
              <span className={`text-xs ${n.score >= 0 ? "text-mint" : "text-rose"}`}>{n.score.toFixed(2)}</span>
            </div>
            <p className="mt-1 text-xs text-slate-300">{n.headline}</p>
            <p className="mt-1 text-[11px] text-slate-500">{n.source} • {n.published_at.slice(0, 16).replace("T", " ")}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
