# Sospana Sonke — Frontend (Next.js)

The candidate + admin web app for the Sospana Sonke platform, wired to the FastAPI
backend in `../backend`. Built with Next.js (App Router), TypeScript and Tailwind CSS.

## What's here

Candidate journey: register / login, dashboard, profile (with skills & education),
CV upload + AI extraction → import to profile, vacancy matches + explainable detail
(generate tailored CV / cover letter, prepare application), applications with the
status lifecycle + answers + audit trail, subscription (checkout / cancel), and
notifications.

Admin: business dashboard (users, MRR, source health, applications) and the company
database (CSV import + per-company "scan now").

## Run it

```bash
cd frontend
npm install
cp .env.example .env.local        # point NEXT_PUBLIC_API_URL at the backend
npm run dev                        # http://localhost:3000
```

The backend must be running (see `../backend`). Default API URL is
`http://127.0.0.1:8000/api/v1`.

## Build / typecheck

```bash
npm run build       # production build (also type-checks)
npm run typecheck   # types only
```

## Notes

- Auth uses JWT access/refresh tokens stored in `localStorage`; the API client in
  `src/lib/api.ts` attaches the bearer token and centralises error handling.
- Paid features (matching, document generation, applications) require an active
  subscription — the UI surfaces the 402 as a prompt to subscribe. In development the
  Subscription page has a "Simulate payment" button (backend mock provider).
