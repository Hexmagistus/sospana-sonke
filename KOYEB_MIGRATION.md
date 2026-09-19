# Migrating the backend from Render to Koyeb (free → free)

Why: Render's free tier sleeps after ~15 min idle and takes ~30–50s to wake up.
Koyeb's free tier sleeps after **1 hour** idle and wakes in **1–5 seconds** — same
cost (R0), noticeably less "Failed to fetch" pain. This does **not** touch the
database (Neon) or the frontend (Vercel) — only where the FastAPI backend runs.

This is a **parallel cutover**, not a delete-and-recreate: Koyeb points at the
*same* Neon database the whole time, so nothing is lost if you decide to abandon
it partway through — Render just keeps running until you switch the frontend over
in Step 5.

---

## Before you start

Open your current **Render ▸ sospana-sonke-api ▸ Environment** tab in one browser
tab — you'll copy several values from it below. Nothing here asks you to paste a
secret into chat; copy directly from one dashboard to the other.

---

## Step 1 — Create the Koyeb service

1. Go to **koyeb.com** and sign in (or sign up with GitHub if you haven't).
   Koyeb asks for a card on file for fraud verification — **you are not charged
   on the free plan.**
2. Click **Create Web Service ▸ GitHub**, pick the **`sospana-sonke`** repo,
   branch **`main`**.
3. **Builder:** choose **Dockerfile** (not buildpack).
4. **Work directory:** `backend` (this tells Koyeb the app + `Dockerfile` live in
   the `backend/` subfolder, not the repo root — same idea as Render's `rootDir`
   and Vercel's Root Directory).
5. **Instance:** Free (Eco / Nano — 0.1 vCPU, 512MB RAM).
6. **Region:** **Frankfurt** (lower latency from South Africa than the other free
   option, Washington D.C.).
7. **Port:** `8000` (matches the Dockerfile's `EXPOSE`; this commit made the
   container actually respect Koyeb's injected `$PORT` too, so it's correct
   either way — see "What this session changed" below).
8. **Health check path:** `/health`.
9. Leave **Autodeploy on push** on, same as Render.

Don't click deploy yet — add the environment variables first (next step), since
the first deploy will crash-loop without `DATABASE_URL`/`SECRET_KEY`.

---

## Step 2 — Environment variables

Add each of these in Koyeb's **Environment variables** section. Where it says
"copy from Render," open your Render tab and copy that exact value across —
these are the values you already chose when you first deployed, `sync: false`
in `render.yaml` meaning Render never stored them in the repo either.

| Key | Value |
|---|---|
| `ENV` | `production` |
| `SECRET_KEY` | **A new random string** — do not reuse Render's. Generate one yourself (e.g. in a terminal: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`), or ask me to generate one and I'll hand you the string to paste in — either way it's a fresh value, not read from anywhere. |
| `AUTO_SEED` | `true` |
| `PAYMENT_PROVIDER` | copy from Render (`mock` unless you've since switched to `paystack`) |
| `DATABASE_URL` | copy from Render — **the same Neon connection string**, unchanged. Koyeb and Render will point at the identical database. |
| `CORS_ORIGINS` | copy from Render (your Vercel URL) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | copy from Render (harmless either way — the admin user already exists in the shared DB, `AUTO_SEED` only creates it if missing) |
| `EMAIL_PROVIDER` | `smtp` |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` / `SMTP_PASSWORD` / `EMAIL_FROM` | copy from Render |
| `NOTIFY_EMAILS` | copy from Render |
| `PUBLIC_API_URL` | **leave blank for now** — Koyeb only shows you the final `https://<name>-<org>.koyeb.app` URL after the first deploy. Come back and set this once you have it (Step 4). |
| `CRON_SECRET` | **A new random string**, same idea as `SECRET_KEY` above — don't try to read Render's old one. You'll also update the GitHub repo secret to match (Step 6), same as when this was first set up on Render. |
| `JS_RENDER_ENABLED` | `false` (unchanged — still an open item, see the project status doc) |
| `GOOGLE_CLIENT_ID` | copy from Render, if set (enables the "Sign in with Google" button) |
| `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` | copy from Render, if set (donations use these regardless of `PAYMENT_PROVIDER`) |
| `DONATION_RETURN_URL` / `PAYMENT_CALLBACK_URL` | copy from Render (these point at the frontend, unaffected by the backend move) |

Click **Deploy**.

---

## Step 3 — Verify it works

1. Wait for the build to go **Healthy** (a few minutes for the first build).
2. Copy the service URL Koyeb gives you (something like
   `https://sospana-sonke-api-<yourorg>.koyeb.app`).
3. Open `<that URL>/health` — should show `{"status":"ok","app":"Sospana Sonke",...}`.
4. Open `<that URL>/docs` (FastAPI's interactive docs) and try `GET /companies`
   with a real token, or just confirm the page loads — this is reading the
   *same* database Render is currently serving, so any data changes are shared.

If this fails, Render is completely untouched and still serving your live site —
nothing to roll back.

---

## Step 4 — Point the backend at itself

Now that you have the real Koyeb URL:

1. Koyeb ▸ Environment variables ▸ set `PUBLIC_API_URL` to `<your Koyeb URL>`
   (this is what gets embedded in email links like account verification).
2. Redeploy (Koyeb does this automatically on an env var change, or click
   **Redeploy**).

---

## Step 5 — Cut the frontend over

1. **Vercel ▸ your project ▸ Settings ▸ Environment Variables.**
2. Edit `NEXT_PUBLIC_API_URL` to `<your Koyeb URL>/api/v1` (same pattern as the
   Render value, just a new host).
3. Save, then **redeploy** the frontend (Vercel ▸ Deployments ▸ ⋯ ▸ Redeploy) so
   the new value actually takes effect — an env var change alone doesn't
   redeploy.
4. Load your live site and do a real end-to-end check: log in, view Companies,
   check a notification — all now hitting Koyeb instead of Render.

---

## Step 6 — Move the scheduled jobs over

Two GitHub Actions workflows currently call the **Render** URL directly:
`.github/workflows/scan.yml` (the vacancy scanner, every 3h) and
`.github/workflows/keep-backend-warm.yml` (the `/health` pinger, every 10 min).

1. **Update the `CRON_SECRET` GitHub repo secret** (Settings ▸ Secrets and
   variables ▸ Actions ▸ `CRON_SECRET`) to the **new** value you set on Koyeb in
   Step 2.
2. Send me the new Koyeb URL and I'll update `scan.yml`'s `API_BASE` (and delete
   `keep-backend-warm.yml` — Koyeb's 1–5s wake time makes a 10-minute keep-warm
   ping pointless, one less moving part to babysit) and push both changes.
3. Run `scan.yml` manually once ("Run workflow" in the Actions tab) to confirm
   it reaches Koyeb and succeeds.

**Do this before or right after Step 5, not before Step 3/4** — if both Render
and Koyeb are live and scheduled at once, you risk two separate scan runs
double-processing the same shared database.

---

## Step 7 — Retire Render (once everything above is confirmed working for a day or two)

- Render ▸ your service ▸ **Suspend** (or delete). Free tier costs nothing to
  leave running, so there's no rush — but suspending avoids any confusion about
  which backend a given request actually hit if something looks wrong later.
- If you ever configured a live Paystack webhook pointing at the Render URL,
  update it in your Paystack dashboard to the Koyeb URL
  (`https://<koyeb-url>/api/v1/subscription/webhook`) before retiring Render.
- Cancel/pause the cron-job.org uptime pinger — it existed only to fight
  Render's slow cold start, which no longer applies.

---

## What this session changed (already committed)

- `backend/Dockerfile`'s `CMD` now reads the container's real `$PORT` at
  startup (`--port ${PORT:-8000}`) instead of a hardcoded `8000`. Koyeb (like
  most modern PaaS hosts) injects its own `PORT` value matching whatever port
  you configure in the dashboard, so the app needs to actually listen on it
  rather than assume 8000. Falls back to `8000` when `$PORT` isn't set, so
  local `docker-compose up` (which doesn't set `PORT`) is unaffected.

## Not part of this migration

- **`JS_RENDER_ENABLED`** stays off — Koyeb's free 0.1 vCPU / 512MB instance is
  even smaller than Render's, so it can't run headless Chromium either. That
  decision is unrelated to which host you're on; see the project status doc's
  open threads for the actual tradeoff (upgrading a paid instance somewhere).
- The Neon database itself is untouched — same connection string, same data,
  both backends can safely point at it during the parallel-cutover window.
