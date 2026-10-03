# Daily digest ("Your daily updates")

One email per opted-in user per day, 08:00 South Africa time. It is the only email
that carries opportunities. Verification, password reset and the other account mail
stay immediate.

## Why it exists

On 3 Oct 2026 one account received 161 "New strong job match" emails in about a minute
(10:58-10:59 UTC = 04:58 UTC-6), and another 89 at 23:00-23:04 UTC. `run_match_for_user`
called `notify_strong_match` once per match, and each call emailed. Every email-capable
opportunity notice now goes through `create_notification`, which refuses to email the
types in `DIGEST_ONLY_TYPES`; the digest collects them instead.

## Cron entry (cron-job.org)

| Field | Value |
| --- | --- |
| URL | `https://sospana-sonke-api-fra.onrender.com/api/v1/cron/run/send_daily_digest` |
| Method | `POST` |
| Schedule | every day at 06:00 UTC (08:00 SAST) |
| Header | `X-Cron-Secret: <the CRON_SECRET value set on Render>` |
| Timeout | as long as the plan allows. The job is idempotent, so a timed-out caller is safe |

Optional catch-up at 06:15 UTC with the same URL: a second call the same day only sends to
users not yet done (a run stops after about 90 seconds and the next call continues).

## Rollout

1. Deploy with `DIGEST_DRY_RUN=true`, call the endpoint once. `detail` shows
   `would_send`, `empty`, `capped` and a short preview (user ids and counts, no addresses).
2. Set `DIGEST_DRY_RUN=false` (or remove it) before the next 06:00 UTC run.

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `DIGEST_DAILY_SEND_CAP` | 250 | All email in a rolling 24h (digests + notification mail + preference notices). Brevo free plan: 300/day |
| `DIGEST_DRY_RUN` | false | Report what would be sent; send and record nothing |
| `DIGEST_MAX_ITEMS` | 25 | Items listed per email; the rest is a "see more" line |
| `DIGEST_LOOKBACK_HOURS` | 24 | Window when the user has no earlier digest |

## Rules

* Idempotent: `digest_log` has UNIQUE (user_id, digest_date) where the date is the SAST day.
  The row is inserted before the send. A definite send failure deletes it (retry later the
  same day); a crash leaves it (no duplicate, the user waits until tomorrow).
* Never empty: a user with nothing new is skipped, no log row.
* Opt-in: active candidate, verified email, not deleted, not unsubscribed, and an explicit yes.
  Alerts yes -> new openings (profile country, or everywhere when willing to relocate, plus the
  user's watches; preferred post type), strong matches and daily-agent briefings. Tagging yes ->
  posts tagged by the team. An active page watch -> "careers page changed" notices.
* Every email carries a preferences link, a one-click unsubscribe link (GET shows a confirm
  page, POST unsubscribes) and the privacy link. Unsubscribing sets `notify_opportunity_alerts`
  to false and `digest_unsubscribed_at`; choosing alerts or tagging again turns it back on.
* Order: South Africa, rest of SADC, rest of Africa, other regions; users are served in the same
  order when the cap bites.

## What sends email today

| Email | Code | When | After this change |
| --- | --- | --- | --- |
| Daily digest | `daily_digest.run_daily_digest` | cron `send_daily_digest`, 06:00 UTC | new |
| Verification | `routes_auth.register` | on sign-up | immediate (unchanged) |
| Password reset | `routes_auth.password_reset_request` | on request, 5/hour | immediate (unchanged) |
| Owner login alert | `login_alert.send_login_alert` | every sign-in, to the owner address only | unchanged |
| Admin sign-in digest | `admin_login_alerts.send_login_digest` | job `send_admin_login_digest` 05:30 UTC, end of `run_daily_agent`, admin button; opted-in admins | unchanged |
| Preference service notice | `preference_mail.send_preference_emails` | admin button, <=50 per click, once per user, 250/24h cap | unchanged |
| Application needs action | `notify_action_required` | when an application needs the candidate | unchanged (NOTIFY_EMAILS) |
| Report ready | `notify_report_ready` | when a report is generated | unchanged (NOTIFY_EMAILS) |
| Strong job match | `notify_strong_match` | each match from "run matching", nightly `match_all_candidates`, `run_daily_agent` | in-app only; in the digest |
| New jobs broadcast | `notify_new_jobs_broadcast` | after `scan_all_companies` / `scan_south_africa` | in-app only; openings in the digest |
| Daily agent briefing | `notify_daily_agent_briefing` | `run_daily_agent` 03:00 UTC | in-app only; in the digest |
| Admin tag / suggestion | `notify_admin_suggestion` | admin sends a tag | in-app only; in the digest (tagging yes) |
| Watched page changed | `notify_watchers_of_change` | job `check_link_changes` every 6h | in-app only; in the digest |

SMS and push (`NOTIFY_SMS`, `NOTIFY_PUSH`) are off by default and not changed here.
