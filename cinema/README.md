# SOSPANA CINEMA

Free Entertainment. Everywhere.

Sospana Cinema is a separate Next.js app in this repository. It does not replace the Sospana Sonke jobs platform. Viewers do not register, pay, or sign in. An admin sign-in exists only for the people who look after the catalogue.

The simplicity it aims at is Tubi: open the site, browse, and press play when a title is actually allowed to play.

## What is real in the demonstration catalogue

`data/catalog.json` was built on 23 November 2026 from Internet Archive items whose own metadata carried a public-domain mark, CC0, or CC BY. Playback URLs are that item's embed player or a file on the same item. Licence evidence URLs are the Creative Commons or public-domain deeds named on those items.

Blender Foundation open movies (Big Buck Bunny, Sintel, Elephants Dream, the two Caminandes shorts, Cosmos Laundromat) and the National Archives copy of NASA's Apollo 11 film are in that set. There is no invented South African film, African feature, or TV series. Those shelves say they are empty.

Watch now is rendered only when a source is marked rights-verified and has an https playback URL.

Regenerate the JSON and `supabase/seed.sql` with:

```bash
python3 scripts/build_catalog.py
```

## Run it

```bash
cd cinema
cp .env.example .env.local
npm install
npm test
npm run dev
```

The site is at http://localhost:3456. Without Supabase keys it uses the demonstration catalogue. Admin sign-in uses `ADMIN_EMAIL`, `ADMIN_PASSWORD` and `ADMIN_SESSION_SECRET` from the environment. If they are missing, the sign-in page reports that, and the public site still works.

Discovery service (optional):

```bash
cd cinema/discovery
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --host 0.0.0.0 --port 8077
```

Set `DISCOVERY_URL` if the admin Discovery page should call it. The service queries the Internet Archive search API and drops items with no allowed licence. It does not download video and it does not use Playwright.

## Environment

See `.env.example`.

| Name | Used for |
| --- | --- |
| `NEXT_PUBLIC_SITE_URL` | Canonical URLs, sitemap, Open Graph |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_SESSION_SECRET` | Admin cookie session |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | Read `public_catalog` |
| `SUPABASE_SERVICE_ROLE_KEY` | Store complaints and admin edits. Server only |
| `TMDB_API_KEY` | Optional metadata. Not called when empty |
| `MUX_TOKEN_ID`, `MUX_TOKEN_SECRET` | Optional hosted video |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_STREAM_TOKEN` | Optional hosted video |
| `DISCOVERY_URL` | Optional Python discovery service |

No secret belongs in source. The values in `.env.example` are demonstration values and must be replaced before any public deploy.

## Deploy

### Supabase

1. Create a project.
2. Run `supabase/migrations/202611230001_cinema.sql` in the SQL editor.
3. Run `supabase/seed.sql` if you want the same demonstration titles in the database.
4. Copy the project URL, the anon key, and the service role key into the host's environment. Do not put the service role key in `NEXT_PUBLIC_` variables.

Row level security lets the anon key read published movies that have a verified rights row. It does not let the anon key read or write copyright complaints. Writes use the service role from the Next.js server.

The column for people in a film is `cast_members` because `CAST` is reserved in SQL.

### Vercel

1. Import the repository. Set the root directory to `cinema`.
2. Framework preset: Next.js.
3. Add the environment variables from `.env.example`, with real values.
4. Deploy. `npm run build` is the production build.

The Python discovery service is not part of the Vercel app. Run it on a small host (for example Render) with `uvicorn app.main:app --host 0.0.0.0 --port $PORT` and set `DISCOVERY_URL` to that origin.

## Architecture

- `src/` is the Next.js App Router UI, search, player, Kids Cinema gate, local library, admin and SEO routes.
- `data/catalog.json` is the demonstration catalogue. `src/lib/store.ts` can overlay edits in `data/runtime-state.json` when Supabase is not configured.
- `supabase/migrations` is the schema: movies, categories, sources, streaming rows, reviews, takedown requests, indexes, foreign keys, checks, and RLS.
- `discovery/` is the Python licence gate.

Country filters list South Africa first, then the other SADC states, then the rest of Africa, then other countries. Alphabetical inside each band.

Kids Cinema shows a title only when `content_reviews.review_status` is `approved` and the age group is preschool, 6–8, 9–12 or family. Sintel is animated and is rejected for that shelf.

Favourites, resume, search history and the chosen country stay in `localStorage`. Clear local data on `/library` removes them.

## Known limitations

- The demonstration files are Internet Archive copies. Some are the archive's smaller MPEG-4 derivative. A few very large items (Metropolis, Safety Last!, The Phantom of the Opera, Charade, Big Buck Bunny) use the archive player only, so resume time cannot be read back from that player.
- Public-domain status is not the same in every country. A worldwide mark on a source record is not legal advice.
- Charade is included because the film is widely treated as public domain in the United States after a defective copyright notice, and the archive item carries a Public Domain Mark. The large file on that item is not rehosted.
- There is no verified South African feature, African feature, anime series, or nature film in this catalogue yet. Those pages are empty on purpose.
- TMDB, Mux and Cloudflare Stream are wired as optional environment variables. They are not called without keys.
- The in-memory rate limit resets when the server process restarts and is not shared across many instances.
- Admin edits without `SUPABASE_SERVICE_ROLE_KEY` stay in `data/runtime-state.json` on that server. They disappear on a host with an ephemeral disk unless Supabase is configured.
