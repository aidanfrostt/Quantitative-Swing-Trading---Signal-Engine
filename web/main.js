(function () {
  const base = (window.__API_BASE__ || "").replace(/\/$/, "");
  const MAX_TABLE_ROWS = 15;

  function url(path) {
    return base + path;
  }

  function setState(text) {
    const n = document.querySelector("[data-live-state]");
    if (n) n.textContent = text;
  }

  function fmtNum(x, d) {
    if (x == null || Number.isNaN(x)) return "—";
    return Number(x).toFixed(d != null ? d : 2);
  }

  function renderError(container, status, body) {
    let msg = "Request failed.";
    if (status === 404) {
      msg =
        "Public API is disabled (set ENABLE_PUBLIC_SIGNAL_UI=true on the server) or the route was not found.";
    } else if (status === 503) {
      msg = body?.detail || "Service unavailable (e.g. signals only on trading days).";
    } else if (status != null) {
      msg = "HTTP " + status + (body?.detail ? ": " + JSON.stringify(body.detail) : "");
    }
    container.innerHTML = '<p class="live-error">' + escapeHtml(msg) + "</p>";
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function rowSignal(r) {
    return (
      "<tr><td>" +
      escapeHtml(r.ticker) +
      "</td><td>" +
      escapeHtml(String(r.action || "")) +
      "</td><td>" +
      escapeHtml(String(r.position_intent || "")) +
      "</td><td>" +
      fmtNum(r.master_conviction, 3) +
      "</td><td>" +
      fmtNum(r.technical_score, 2) +
      "</td><td>" +
      fmtNum(r.sentiment_score, 2) +
      "</td></tr>"
    );
  }

  function rowSector(r) {
    return (
      "<tr><td>" +
      escapeHtml(r.sector_key) +
      "</td><td>" +
      escapeHtml(r.benchmark_etf || "—") +
      "</td><td>" +
      fmtNum(r.weighted_sentiment_avg, 3) +
      "</td><td>" +
      fmtNum(r.etf_return_5d, 4) +
      "</td><td>" +
      (r.divergence_flag === true ? "1" : r.divergence_flag === false ? "0" : "—") +
      "</td></tr>"
    );
  }

  function tableBlock(title, id, rows) {
    let h =
      '<p class="subhead" id="' +
      escapeHtml(id) +
      '">' +
      escapeHtml(title) +
      "</p>";
    if (!rows || rows.length === 0) {
      h += '<p class="live-muted">No rows.</p>';
      return h;
    }
    h +=
      '<table class="data"><thead><tr><th>Ticker</th><th>Action</th><th>Intent</th><th>Conv</th><th>Tech</th><th>Sent</th></tr></thead><tbody>';
    for (let i = 0; i < Math.min(rows.length, MAX_TABLE_ROWS); i++) {
      h += rowSignal(rows[i]);
    }
    h += "</tbody></table>";
    if (rows.length > MAX_TABLE_ROWS) {
      h += '<p class="live-muted">Showing ' + MAX_TABLE_ROWS + " of " + rows.length + ".</p>";
    }
    return h;
  }

  function emptyPipelineCallout() {
    return (
      '<div class="live-callout">' +
      "<p><strong>No scored symbols yet.</strong> The API reads whatever is already in PostgreSQL; it does not pull market data by itself. " +
      "Rows come from the latest <code>technical_features</code> snapshot (plus OHLCV joins). Run batch jobs in order:</p>" +
      "<ol class=\"live-checklist\">" +
      "<li><code>universe_cron</code> — symbols and filtered universe</li>" +
      "<li><code>price_ingest</code> — daily bars (and benchmarks)</li>" +
      "<li><code>technical_engine</code> — required before any names appear here</li>" +
      "<li>Optional: <code>news_ingest</code> / <code>nlp_worker</code>, <code>fundamentals_ingest</code>, <code>attribution_job</code></li>" +
      "<li>Sector table: <code>sector_sentiment_job</code> after NLP and ETF prices</li>" +
      "</ol>" +
      "<p class=\"live-muted\">Then reload this page. <code>symbols_evaluated</code> above should be &gt; 0 when technicals exist.</p>" +
      "</div>"
    );
  }

  async function load() {
    const container = document.querySelector("[data-live-body]");
    if (!container) return;

    setState("loading…");
    try {
      const res = await fetch(url("/public/v1/signals?limit=25"), {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        renderError(container, res.status, null);
        setState("error");
        return;
      }

      if (!res.ok) {
        renderError(container, res.status, data);
        setState("error");
        return;
      }

      setState("ok · " + (data.generated_at || "").replace("T", " ").slice(0, 19) + " UTC");

      const mc = data.market_context || {};
      const ms = data.market_session || {};
      const longC = data.long_candidates || [];
      const shortC = data.short_candidates || [];
      const watch = data.watchlist || [];
      const signals = data.signals || [];
      const sectors = data.sector_context || [];
      const symEv = typeof data.symbols_evaluated === "number" ? data.symbols_evaluated : null;
      const uv = data.universe_version || "—";

      const countsLine =
        "Long " +
        longC.length +
        " · Short " +
        shortC.length +
        " · Watch " +
        watch.length +
        " · Ranked list " +
        signals.length +
        (sectors.length ? " · Sectors " + sectors.length : " · Sectors 0");

      let html = '<div class="status-counts">' + escapeHtml(countsLine) + "</div>";

      html += '<div class="meta-row">';
      html +=
        "Universe <strong>" +
        escapeHtml(String(uv)) +
        "</strong> · NYSE " +
        escapeHtml(String(ms.nyse_calendar_date || "—")) +
        " · trading_day=" +
        String(ms.nyse_trading_day);
      if (symEv !== null) {
        html +=
          " · <strong>symbols_evaluated</strong> " +
          symEv +
          " <span class=\"live-muted\">(rows from latest technical_features)</span>";
      }
      html += "<br>";
      html +=
        "SPY 5d " +
        fmtNum(mc.spy_return_5d, 4) +
        " · QQQ 5d " +
        fmtNum(mc.qqq_return_5d, 4) +
        " · VIX " +
        fmtNum(mc.vix_close, 2);
      html += "</div>";

      if (uv === "unknown") {
        html +=
          '<p class="live-warn">Universe version is unknown — <code>filtered_universe</code> may be empty. Run <code>universe_cron</code> (and downstream jobs).</p>';
      }

      const allEmpty =
        longC.length === 0 &&
        shortC.length === 0 &&
        watch.length === 0 &&
        signals.length === 0;

      if (allEmpty) {
        html += emptyPipelineCallout();
      } else {
        html += tableBlock("Long (BUY candidates)", "live-long", longC);
        html += tableBlock("Short (SHORT intent)", "live-short", shortC);
        html += tableBlock("Watchlist (HOLD, elevated |conviction|)", "live-watch", watch);
        html +=
          '<p class="subhead" id="live-ranked">Ranked by |conviction| (cross-section, not only BUY)</p>' +
          '<p class="live-muted">Flat list for scanning; long/short/watch above are the actionable groupings.</p>';
        if (signals.length === 0) {
          html += '<p class="live-muted">No ranked rows.</p>';
        } else {
          html +=
            '<table class="data"><thead><tr><th>Ticker</th><th>Action</th><th>Intent</th><th>Conv</th><th>Tech</th><th>Sent</th></tr></thead><tbody>';
          for (let k = 0; k < Math.min(signals.length, MAX_TABLE_ROWS); k++) {
            html += rowSignal(signals[k]);
          }
          html += "</tbody></table>";
        }
      }

      html += '<p class="subhead" id="live-sectors">Sector context</p>';
      if (sectors.length === 0) {
        html +=
          '<p class="live-muted">No sector snapshot — run <code>sector_sentiment_job</code> after NLP and ETF OHLCV exist.</p>';
      } else {
        html +=
          '<table class="data"><thead><tr><th>Sector</th><th>ETF</th><th>Sent avg</th><th>ETF 5d</th><th>Div</th></tr></thead><tbody>';
        for (let j = 0; j < Math.min(sectors.length, 12); j++) {
          html += rowSector(sectors[j]);
        }
        html += "</tbody></table>";
      }

      html +=
        '<p class="meta-row live-disclaimer-foot">' + escapeHtml(data.disclaimer || "") + "</p>";

      container.innerHTML = html;
    } catch (e) {
      container.innerHTML =
        '<p class="live-error">Network error: ' + escapeHtml(String(e && e.message ? e.message : e)) + "</p>";
      setState("error");
    }
  }

  const btn = document.querySelector("[data-refresh-live]");
  if (btn) btn.addEventListener("click", function () {
    load();
  });

  const steps = document.querySelectorAll(".pipeline li");
  if (steps.length && "IntersectionObserver" in window) {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            const id = en.target.getAttribute("data-step");
            steps.forEach((li) => {
              li.setAttribute("data-active", li.getAttribute("data-step") === id ? "true" : "false");
            });
          }
        });
      },
      { rootMargin: "-40% 0px -45% 0px", threshold: 0 }
    );
    steps.forEach((li) => obs.observe(li));
  }

  load();
})();
