# Database operations

Read on 2026-10-13 from Neon's own docs. This environment has no Neon credentials, so nothing here was executed against the production project. Confirm the project's plan in the Neon console before relying on a window.

## What Neon publishes

- Instant restore (point-in-time restore) uses the history window: [History window](https://neon.com/docs/introduction/history-window) and [Backup & restore](https://neon.com/docs/guides/backup-restore).
- Free plan, as published: 6 hours of history, capped at 1 GB, no charge. One manual snapshot. Automated backup schedules are not on the free plan.
- Launch plan, as published: history up to 7 days. Scale plan: up to 30 days. History storage on those plans is listed at $0.20/GB-month. Automated snapshot schedules are a paid-plan feature.
- Instant restore applies to root branches. A branch created by restoring a snapshot does not itself support point-in-time restore while Neon reports that restore as still ongoing.
- Console path published for the history window: project Settings, then Instant restore or Postgres, then the history-window control, then Save.

## Restore drill without production secrets

`backend/app/services/restore_drill.py` builds two empty SQLite databases, writes one South African directory row, copies it, and reads it back. It does not read `DATABASE_URL`. `tests/test_restore_drill.py` runs that copy.

A production restore is a console action on the root branch: instant restore to a time inside the history window, or a snapshot restore. Do that in the Neon console. This repository cannot start it.

## Scanner freshness

On 2026-10-13 a public `GET /api/v1/jobs?limit=1` returned a role last seen at `2026-10-13T21:01:16.928897Z`. That is evidence the scanner had written a row that day. It is not a substitute for the status check.

`GET /api/v1/status` reports the newest finished scan and counts sources that have already reached the failure threshold of 3. The scanner is stale after 120 minutes, eight runs of the 15-minute `scan_due_companies` cron. The scheduled status workflow fails when that check says the scanner is stale or the database check is down. That route is deployed with the status change; until it is live, the jobs timestamp above is the observation on record.
