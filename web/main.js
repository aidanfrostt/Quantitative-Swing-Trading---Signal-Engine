(function () {
  const base = (window.__API_BASE__ || "").replace(/\/$/, "");

  function url(path) {
    return base + path;
  }

  function setState(el, text) {
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

  async function load() {
    const container = document.querySelector("[data-live-body]");
    if (!container) return;

    setState(null, "loading…");
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
        setState(null, "error");
        return;
      }

      if (!res.ok) {
        renderError(container, res.status, data);
        setState(null, "error");
        return;
      }

      setState(null, "ok · " + (data.generated_at || "").replace("T", " ").slice(0, 19) + " UTC");

      const mc = data.market_context || {};
      const ms = data.market_session || {};
      let meta =
        "Universe " +
        escapeHtml(String(data.universe_version || "—")) +
        " · NYSE date " +
        escapeHtml(String(ms.nyse_calendar_date || "—")) +
        " · trading_day=" +
        String(ms.nyse_trading_day) +
        "<br>SPY 5d " +
        fmtNum(mc.spy_return_5d, 4) +
        " · QQQ 5d " +
        fmtNum(mc.qqq_return_5d, 4) +
        " · VIX " +
        fmtNum(mc.vix_close, 2);

      const signals = data.signals || [];
      const sectors = data.sector_context || [];

      let html = '<div class="meta-row">' + meta + "</div>";

      html += '<p class="subhead">Top by |conviction|</p>';
      if (signals.length === 0) {
        html += '<p class="live-error">No signal rows (empty universe or missing technical_features).</p>';
      } else {
        html +=
          '<table class="data"><thead><tr><th>Ticker</th><th>Action</th><th>Intent</th><th>Conv</th><th>Tech</th><th>Sent</th></tr></thead><tbody>';
        for (let i = 0; i < Math.min(signals.length, 15); i++) {
          html += rowSignal(signals[i]);
        }
        html += "</tbody></table>";
      }

      html += '<p class="subhead">Sector context</p>';
      if (sectors.length === 0) {
        html += '<p class="live-error">No sector snapshot (run sector_sentiment_job after NLP and prices).</p>';
      } else {
        html +=
          '<table class="data"><thead><tr><th>Sector</th><th>ETF</th><th>Sent avg</th><th>ETF 5d</th><th>Div</th></tr></thead><tbody>';
        for (let j = 0; j < Math.min(sectors.length, 12); j++) {
          html += rowSector(sectors[j]);
        }
        html += "</tbody></table>";
      }

      html +=
        '<p class="meta-row" style="margin-top:1rem">' +
        escapeHtml(data.disclaimer || "") +
        "</p>";

      container.innerHTML = html;
    } catch (e) {
      container.innerHTML =
        '<p class="live-error">Network error: ' + escapeHtml(String(e && e.message ? e.message : e)) + "</p>";
      setState(null, "error");
    }
  }

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
