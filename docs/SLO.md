# Service levels

Measured from this environment to `https://sospana-sonke-api-fra.onrender.com` on 2026-10-13. One warm-up request per URL, then 15 sequential samples. Every sample returned HTTP 200. The p95 is the nearest-rank value at index `round(0.95 * (n - 1))` of the sorted times (index 13 of 15).

Times are milliseconds.

## `/health`

139.9, 141.5, 144.5, 147.1, 148.0, 151.1, 157.3, 159.4, 161.2, 161.4, 162.3, 163.4, 179.3, 195.5, 224.5

min 139.9, p50 159.4, p95 195.5, max 224.5. The response commit was `51a8195181fe0594408e6e54c9016c3d3b8a358f`. `db_pooled` was true and `db_region` was `eu-central-1`. `/health` does not query the database.

## `GET /api/v1/jobs?limit=10`

206.9, 211.3, 215.1, 218.1, 221.5, 231.4, 232.2, 232.8, 240.7, 243.1, 245.4, 245.9, 258.7, 382.2, 422.3

min 206.9, p50 232.8, p95 382.2, max 422.3.

## `GET /api/v1/companies/stats`

141.9, 145.3, 147.6, 148.2, 160.9, 163.7, 164.6, 168.8, 175.8, 210.1, 314.7, 330.0, 337.3, 337.5, 337.8

min 141.9, p50 168.8, p95 337.5, max 337.8.

## Targets

These targets are the measured p95, rounded up to the next whole millisecond. They are a ceiling for a later sample taken the same way. They are not a promise about a month of traffic.

- `/health` p95 at or under 196 ms
- `GET /api/v1/jobs?limit=10` p95 at or under 383 ms
- `GET /api/v1/companies/stats` p95 at or under 338 ms

Availability in this window was 15 successes and 0 failures on each URL. A longer window was not measured, so this document does not state a monthly percentage. The public status page and the scheduled status check are the ongoing observation: `/health` must return 200, and `/api/v1/status` must report the database check as ok. The scanner is stale when both the newest scan log and the newest successful `scan_due_companies` job run are older than 120 minutes. That window is eight runs of the 15-minute cron in `app/scheduler/registry.py`.

## What the owner sets

Error tracking is already in the API. It stays off until `SENTRY_DSN` is set on the Frankfurt Render service `sospana-sonke-api-fra`. Create a Sentry project on the free plan and paste that project's DSN. Do not put the DSN in the repo. Leave the variable unset to keep the integration off. No browser DSN is required for this step.

Each request logs one JSON object on logger `app.access` with `request_id`, `method`, `path`, `status` and `duration_ms`. The query string is not included. The response header is `X-Request-ID`.
