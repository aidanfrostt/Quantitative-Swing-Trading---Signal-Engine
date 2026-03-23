# GitHub (public) + Railway — step by step

Follow this once to publish the repo and run the **signal API + public web UI** on Railway.

## Before you start

- **Never commit secrets.** This repo ignores `.env`; only [`.env.example`](../.env.example) belongs in git. Use API keys only in Railway variables or a local `.env`.
- You need accounts: [GitHub](https://github.com), [Railway](https://railway.app).

---

## Part 1 — Push the project to GitHub

1. **Create an empty repository on GitHub**  
   GitHub → **New repository** → name it (e.g. `signal-generation`) → **Public** → do **not** add a README, `.gitignore`, or license (this repo already has those files).

2. **On your machine**, in the project folder:

   ```bash
   cd /path/to/signal-generation
   git init
   git branch -M main
   git add -A
   git status   # confirm .env is NOT listed
   git commit -m "Initial commit: signal generation platform with public UI"
   ```

3. **Connect GitHub and push:**

   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

   Use SSH if you prefer: `git@github.com:YOUR_USERNAME/YOUR_REPO.git`.

4. **Confirm on GitHub** that files appear and **`.env` is not** in the repository (open **Security** tab if you use GitHub Advanced Security, or clone to a temp folder and verify).

---

## Part 2 — Deploy on Railway

The repo includes [`railway.json`](../railway.json) so Railway uses **`Dockerfile.service`** and the **`/health`** check. The Dockerfile defaults to **`SVC=signal_api`** (no extra build arg required).

### 2.1 Create project and database

1. Log in to [Railway](https://railway.app) → **New Project**.
2. **Deploy from GitHub repo** → authorize Railway → select **`YOUR_USERNAME/YOUR_REPO`**.
3. Railway may create a first service from the repo; open it or add a **new service** from the same repo if needed.
4. In the project, click **New** → **Database** → **PostgreSQL**. Wait until it is provisioned.

### 2.2 Link Postgres to the web service

1. Open your **application service** (the one that builds the Docker image).
2. Go to **Variables**.
3. Add **`DATABASE_URL`**:
   - Click **Add Variable** → **Add Reference** (or **Variable Reference**).
   - Choose the **PostgreSQL** service and the **`DATABASE_URL`** (or `POSTGRES_URL`) variable Railway exposes.
   - This keeps the password out of your clipboard and updates if the DB is rotated.

   If your stack does not offer a reference UI, copy the **private** connection string from the Postgres plugin’s **Connect** / **Variables** tab and paste it as `DATABASE_URL` (must be a `postgresql://...` URL compatible with asyncpg).

### 2.3 Build settings (usually automatic)

- **Root directory:** repository root (default).
- **Builder:** Dockerfile — path **`Dockerfile.service`** is set in [`railway.json`](../railway.json).
- **Start command:** leave empty; the image runs `python /app/run.py`.

If the dashboard still picks Railpack, set the builder to **Dockerfile** and **`Dockerfile.service`** manually once; [`railway.json`](../railway.json) should override on the next deploy.

### 2.4 Required environment variables

In the **application service** → **Variables**, set:

| Variable | Example / notes |
|----------|------------------|
| `ENABLE_PUBLIC_SIGNAL_UI` | `true` — required for the browser to load live data from `/public/v1/signals` without an API key. |
| `SIGNAL_API_KEYS` | A long random string (comma-separated if multiple). Used for **`X-API-Key`** on `/v1/signals` and `/v1/sector-sentiment`. |
| `POLYGON_API_KEY` | From [Polygon](https://polygon.io/) — needed for ingestion jobs and a realistic universe in production. |
| `PERIGON_API_KEY` | If you use Perigon news ingest. |

Optional (see [`.env.example`](../.env.example)):

- `KAFKA_BOOTSTRAP_SERVERS` — only if you connect to a broker; local default may not apply on Railway.
- `SIGNALS_ONLY_ON_TRADING_DAYS` — `true` returns **503** for signals on non-NYSE days.
- `CORS_ALLOWED_ORIGINS` — only if the HTML is hosted on **another** domain (e.g. Netlify); use your site origin, comma-separated.

Redeploy after changing variables (**Deploy** or automatic on save).

### 2.5 Public URL

1. Open the application service → **Settings** → **Networking** → **Generate Domain** (or add a custom domain).
2. Open the URL in a browser:
   - **`/`** — static UI (pipeline + live snapshot).
   - **`/health`** — should return `{"status":"ok"}`.
   - **`/public/v1/signals`** — JSON when `ENABLE_PUBLIC_SIGNAL_UI=true`.

Migrations run when the app starts (`run_migrations` in the DB pool). The **first** request may wait for Postgres to be ready; `/ready` checks DB connectivity.

---

## Part 3 — After deploy

1. **Populate data** (optional but needed for non-empty signals): run batch jobs (`universe_cron`, `price_ingest`, …) from your laptop against the same `DATABASE_URL`, or add **additional Railway services** / cron for those jobs. See [SERVICES.md](../docs/SERVICES.md).
2. **GitHub Actions:** pushes to `main` run CI ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)). Fix failures before relying on automation.
3. **Security:** `ENABLE_PUBLIC_SIGNAL_UI=true` exposes the same payload as the keyed API to anyone with the URL. Turn it **off** for private stacks; keep programmatic access behind **`SIGNAL_API_KEYS`**.

---

## Part 4 — Optional: UI on Netlify, API on Railway

1. Deploy the **`web/`** folder on Netlify ([`netlify.toml`](../netlify.toml)).
2. Set a Netlify build env `PUBLIC_API_BASE` to your Railway URL (no trailing slash).
3. Build command example:  
   `printf "window.__API_BASE__='%s';\n" "$PUBLIC_API_BASE" > web/config.js`  
   (run before publish, or maintain `config.js` manually).
4. On Railway, set **`CORS_ALLOWED_ORIGINS`** to your Netlify site origin.

Details: [deploy/railway.md](railway.md) (Netlify subsection).

---

## Troubleshooting

| Symptom | What to check |
|--------|----------------|
| Build fails: `COPY web` | Ensure the `web/` directory is committed (not gitignored). |
| 404 on `/public/v1/signals` | Set `ENABLE_PUBLIC_SIGNAL_UI=true` and redeploy. |
| 503 on signals | `SIGNALS_ONLY_ON_TRADING_DAYS=true` on a non-trading day, or empty/missing DB tables. |
| Health check fails | Increase timeout; confirm app listens on **`PORT`** if Railway injects it (see note below). |

**Port:** Railway injects **`PORT`**. The app reads **`PORT`** or **`API_PORT`** (see [`config.py`](../src/signal_common/config.py) `api_port`) and listens on **`0.0.0.0`**, so you usually do not need to set anything extra.

---

For deeper deployment notes, see [deploy/railway.md](railway.md).
