# Deploying Sospana Sonke for **free** — step by step

You'll use three free services, all of which you can sign into with one GitHub
account. Total cost: **R0**. Time: about **30–45 minutes**. No command line needed.

| Piece | Free host | What it is |
|---|---|---|
| Database | **Neon** (neon.tech) | Free Postgres that stays online |
| Backend API | **Render** (render.com) | Runs the FastAPI app (this repo's `backend/`) |
| Frontend | **Vercel** (vercel.com) | Runs the Next.js app (this repo's `frontend/`) |

Everything you need is already in this project — a `render.yaml` blueprint so Render
configures itself, and auto-seeding so the 367-company database and your admin login
are created on first boot. You mostly click and paste.

---

## Step 1 — Create a GitHub account and upload the code (GUI, no terminal)

1. Go to **github.com** and sign up (free).
2. Download and install **GitHub Desktop** from **desktop.github.com**, then sign in with your new account.
3. **Unzip** the `sospana-sonke-fullstack.zip` I sent you. You'll get a folder called `sospana-sonke`.
4. In GitHub Desktop: **File ▸ Add local repository ▸** choose the `sospana-sonke` folder.
   - It will say "this directory does not appear to be a Git repository" — click **"create a repository"**, then **Create repository**.
5. Click **Publish repository** (top right). You can keep it **Private** — Render and Vercel can still read it because you'll connect them with GitHub. Click **Publish**.

Your code is now on GitHub. ✅

---

## Step 2 — Create the free database (Neon)

1. Go to **neon.tech** and **Sign up** (choose **Continue with GitHub**).
2. Create a new project (any name, e.g. `sospana-sonke`). Pick a region near South Africa if offered (EU is fine).
3. On the project dashboard, find the **Connection string** (starts with `postgresql://`). Click **copy**.
4. Paste it somewhere safe for a moment — you'll need it in Step 3. (It contains your DB password.)

---

## Step 3 — Deploy the backend (Render)

1. Go to **render.com** and **Sign up** with **GitHub**.
2. Click **New ▸ Blueprint**.
3. Choose your `sospana-sonke` repository. Render finds `render.yaml` and shows a service called **sospana-sonke-api**. Click **Apply**.
4. Render will ask you to fill in the values marked "sync:false". Enter:
   - **DATABASE_URL** → paste the Neon connection string from Step 2.
   - **CORS_ORIGINS** → leave blank for now (we set it in Step 5).
   - **ADMIN_EMAIL** → the email you want for the admin login.
   - **ADMIN_PASSWORD** → a strong password for the admin login.
   - (SECRET_KEY, ENV, AUTO_SEED, PAYMENT_PROVIDER are set automatically.)
5. Click **Create / Deploy** and wait for the build to finish (a few minutes).
6. When it's live, copy your backend URL (looks like **`https://sospana-sonke-api.onrender.com`**).
   Test it: open **`https://sospana-sonke-api.onrender.com/health`** — you should see `{"status":"ok",...}`.

The database is seeded with all 367 companies and your admin user automatically on first boot. ✅

---

## Step 4 — Deploy the frontend (Vercel)

1. Go to **vercel.com** and **Sign up** with **GitHub**.
2. Click **Add New… ▸ Project**, and **Import** your `sospana-sonke` repo.
3. Set **Root Directory** to **`frontend`** (click *Edit* next to Root Directory and choose the `frontend` folder).
4. Under **Environment Variables**, add one:
   - **Name:** `NEXT_PUBLIC_API_URL`
   - **Value:** your backend URL **plus `/api/v1`**, e.g. `https://sospana-sonke-api.onrender.com/api/v1`
5. Click **Deploy**. When done, copy your site URL (looks like **`https://sospana-sonke.vercel.app`**).

---

## Step 5 — Connect the two (one paste)

1. Back in **Render ▸ your service ▸ Environment**.
2. Set **CORS_ORIGINS** to your Vercel URL, e.g. `https://sospana-sonke.vercel.app` (no trailing slash).
3. Save — Render redeploys automatically.

**Done.** Open your Vercel URL, register a candidate, or log in with the admin email/password
you chose. It's live and free. 🎉

---

## Good to know (and what to do later)

- **Sleep on free tier:** Render's free backend goes to sleep after ~15 minutes idle; the first
  request after that takes ~30–50 seconds to wake up. Normal for free hosting.
- **Payments:** the site launches in **mock payment** mode — the Subscription page's
  "Simulate payment" activates access instantly, so you can demo the full flow. To take real
  **R100/month** payments later: create a **Paystack** account, and in Render set
  `PAYMENT_PROVIDER=paystack` and `PAYSTACK_SECRET_KEY=...`, then point Paystack's webhook at
  `https://<your-backend>/api/v1/subscription/webhook`.
- **Automated applications & JS-rendered scraping** are **off** by default (they need a headless
  browser and more memory than the free tier). Everything else — matching, tailored CVs, cover
  letters, applications tracking, dashboards, reports, notifications, MFA — works on free hosting.
  Turn automation on later by moving the backend to a small paid instance and setting
  `AUTOMATION_ENABLED=true` / `JS_RENDER_ENABLED=true`.
- **Recurring scans/matching:** trigger them from the **Admin ▸ Run job** buttons for now. For
  automatic scheduling, add a scheduled job later (Render Cron, a paid add-on).
- **Custom domain:** you can add your own domain free in Vercel (frontend) and Render (backend)
  whenever you're ready.
- **Legal before real users:** finalise the documents in `docs/Sospana_Sonke_Legal_Pack.md` with a
  South African attorney before processing real people's personal information (POPIA).
