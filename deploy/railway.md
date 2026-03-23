# Deploy on Railway (signal API + public UI)

One **Docker** service serves the **FastAPI** JSON API, the **static UI** under `/`, and **public read routes** for the browser without `X-API-Key`.

The repo root [`railway.json`](../railway.json) pins the **Dockerfile** to **`Dockerfile.service`** and sets the **health check** to **`/health`**. For a full walkthrough including GitHub, see [GITHUB_AND_RAILWAY_SETUP.md](GITHUB_AND_RAILWAY_SETUP.md).

## 1. Create a Railway project

- **New project** → **Deploy from GitHub** (or empty project + connect repo).

## 2. Add PostgreSQL

- **New** → **Database** → **PostgreSQL**.
- Copy the **private `DATABASE_URL`** (or use Railway’s variable reference). The app expects a standard `postgresql://…` asyncpg URL.

## 3. Web service (API + static `web/`)

- **New** → **GitHub Repo** → select this repository, or add a service that builds from the same repo.

**Settings → Build**

- **Dockerfile path:** `Dockerfile.service`
- **Build argument:** `SVC` = `signal_api`  
  (Railway: *Dockerfile* → *Build Args* → `SVC` = `signal_api`)

**Settings → Deploy**

- **Start command:** leave empty (image `CMD` runs `python /app/run.py`).
- **Health check path:** `/health` (liveness). Use `/ready` if you want the check to fail when the DB is unreachable.

**Settings → Variables** (minimum)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | From the Postgres plugin (same as `PG*` if you use variable reference). |
| `POLYGON_API_KEY` | Price and fundamentals ingestion (required for a populated universe in production). |
| `PERIGON_API_KEY` | News ingest (if you run the news pipeline). |
| `ENABLE_PUBLIC_SIGNAL_UI` | Set to `true` so the browser can call `GET /public/v1/signals` and `GET /public/v1/sector-sentiment` **without** an API key. Same data as `/v1/*`. |
| `SIGNAL_API_KEYS` | Comma-separated keys for **programmatic** access to `/v1/signals` and `/v1/sector-sentiment`. |

Optional:

- `SIGNALS_ONLY_ON_TRADING_DAYS` — if `true`, `/v1/signals` and public signals return **503** on non-NYSE session days.
- `CORS_ALLOWED_ORIGINS` — comma-separated origins (e.g. `https://your-site.netlify.app`) **only** if the HTML is hosted on another domain; same-origin Railway UI does not need CORS.

## 4. First deploy

- Migrations run when the API creates the DB pool (`run_migrations` on startup).
- Open the **Railway public URL** → `/` should load the static UI; `/public/v1/signals` returns JSON when `ENABLE_PUBLIC_SIGNAL_UI=true`.

## 5. Batch jobs

Cron-style jobs (`universe_cron`, `price_ingest`, …) are **separate** processes. To run them on Railway, add **additional services** from the same repo with the same `Dockerfile.service` and `SVC` set to each job name, or use **Railway Cron** / an external scheduler. The live page only needs a **filled database** and a running **`signal_api`**.

## Security note

`ENABLE_PUBLIC_SIGNAL_UI=true` exposes the same signal payload to anyone who can reach the URL. Keep it **off** for private deployments; use **`SIGNAL_API_KEYS`** for authenticated `/v1/*` access.

## Optional: static UI on Netlify + API on Railway

1. Deploy this repo on **Netlify** with root [`netlify.toml`](../netlify.toml) (`publish = "web"`).
2. Before build, inject the API base URL so the browser can reach Railway (example build command):  
   `printf "window.__API_BASE__='%s';\n" "$PUBLIC_API_BASE" > web/config.js`  
   Set `PUBLIC_API_BASE` in Netlify to `https://<your-railway-service>.up.railway.app` (no trailing slash).
3. On Railway, set **`CORS_ALLOWED_ORIGINS`** to your Netlify site origin, e.g. `https://your-site.netlify.app` (comma-separated if multiple).
4. The page calls **`/public/v1/signals`** on that base URL; no API key is sent from the client.
