# SOSPANA CINEMA

Free Entertainment. Everywhere.

Sospana Cinema is a separate Next.js app in this repository. It does not replace the Sospana Sonke jobs platform. Viewers do not register, pay, or sign in. An admin sign-in exists only for the people who look after the catalogue.

The simplicity it aims at is Tubi: open the site, browse, and press play when a title is actually allowed to play.

## What is real in the demonstration catalogue

`data/catalog.json` holds 264 titles, all checked on 23 November 2026. Every title comes from one of two kinds of source:

1. **Internet Archive items (151 titles: 35 original + 116 added).** The item's own metadata `licenseurl` must be a public-domain mark, CC0 or CC BY/BY-SA. Non-commercial and no-derivatives licences are refused. Playback uses the item's embed player plus a direct file on the same item. The licence evidence URL is the deed named on the item. The 116 additions are Chaplin shorts and classic features, Sita Sings the Blues, the Fleischer Superman cartoons, Popeye and Betty Boop, other public-domain cartoons, nature and NASA documentaries, and classic TV episodes (The Beverly Hillbillies, The Lucy Show, Bonanza, Sherlock Holmes (1954) and others).
2. **Official rights-holder YouTube embeds (113 titles).** Only full titles that the rights holder uploaded to its own channel are used, and the channel URL is the licence evidence. Each video was checked live: oEmbed returned 200, the watch page reported playable and `playableInEmbed`, and the uploading channel id matched the rights holder's channel. Playback is `https://www.youtube-nocookie.com/embed/<id>`. Nothing is downloaded or rehosted. The rights holders are Heartlines, Shuga Global (MTV Shuga), Triggerfish, Amerley Productions (An African City), KAP Stream (Kunle Afolayan), Omoni Oboli TV, Ramon Film Productions (Wakaliwood), Ubongo (Ubongo Kids, Akili and Me), Tinga Tinga Tales, Bino and Fino, Supa Strikas, Netflix (Our Planet), Bandai Namco Filmworks (GUNDAM CHANNEL INTL) and Blender Studio/Blender Foundation. Region limits are read from the watch page. Only the Gundam episodes are limited (89 countries, South Africa included).

The South African (40), African (91), TV Series (99), Anime (5) and Nature and Wildlife (17) shelves are now filled from those sources. Per-row evidence is in `data/additions-evidence.json`.

Children's titles from Ubongo, Akili and Me, Tinga Tinga Tales, Bino and Fino, Supa Strikas and the older public-domain cartoons are recorded as **pending manual review**. They play on general shelves, but they are not placed on any Kids Cinema shelf until a person approves them. Kids Cinema still shows only the original approved titles.

Titles that were deliberately left out: Superman "Japoteurs" and "Jungle Drums" and the Betty Boop shorts "Bamboo Isle" and "I'll Be Glad When You're Dead You Rascal You" (racist caricature), an age-restricted An African City episode, an Internet Archive item falsely tagged CC0, a Shuga Naija upload that was not on the official channel, and SA indie or archive channels whose ownership of the films could not be confirmed. Movira, Moviera and Movirea sites are never used.

Watch now is rendered only when a source is marked rights-verified and has an https playback URL.

To add titles, put candidate rows in `scripts/additions.py`, check them live, then regenerate the JSON and `supabase/seed.sql`:

```bash
python3 scripts/verify_additions.py      # writes data/additions-evidence.json (needs network; pycountry)
python3 scripts/build_catalog.py         # merges only rows whose evidence is ok
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
2. Run every file in `supabase/migrations/` in order, in the SQL editor or with `supabase db push`:
   - `0001_cinema`: tables, indexes and RLS.
   - `0002_takedown_anon_insert`: the public complaint form can insert with the anon key.
   - `0003_fix_rls_recursion`: replaces the 0001 read policies, which referenced each other and made Postgres fail with `infinite recursion detected in policy for relation "movies"` (42P17).
   - `0004_revoke_default_writes`: removes the insert, update, delete and truncate rights Supabase gives `anon` by default.
3. Run `supabase/seed.sql` if you want the same demonstration titles in the database. It is about 0.9 MB, so split it if your SQL client limits query size.
4. Copy the project URL, the anon key, and the service role key into the host's environment. Do not put the service role key in `NEXT_PUBLIC_` variables.

Row level security lets the anon key read published movies that have a verified rights row. The anon key can insert a complaint's four form fields, and the status always starts as `received`. It cannot read, change or delete complaints. Admin edits and the complaint list use the service role from the Next.js server.

As soon as `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set, the site reads the catalogue from Supabase and stores complaints there. Without `SUPABASE_SERVICE_ROLE_KEY`, the admin dashboard cannot list complaints, and admin edits return HTTP 503 with that reason. Without Supabase, edits and complaints go to `data/runtime-state.json`. That file cannot be written on Vercel, whose file system is read-only, so on that host the server reports a 503 with the reason.

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
- YouTube embeds depend on the rights holder keeping the video public and embeddable. Run `scripts/verify_additions.py` again before a release and rebuild. A failed row is dropped automatically.
- The Kids Cinema sub-shelves Nursery Rhymes, Educational Cartoons, African Children's Stories and Nature for Kids are still empty. Verified candidates exist (Ubongo, Akili and Me, Tinga Tinga Tales), but they wait for a person to review them.
- Anime has only the five official Gundam episodes, because no other anime rights holder publishes full episodes worldwide on an official channel that could be verified.
- TMDB, Mux and Cloudflare Stream are wired as optional environment variables. They are not called without keys.
- The in-memory rate limit resets when the server process restarts and is not shared across many instances.
- Admin edits without Supabase stay in `data/runtime-state.json` on that server. They disappear on a host with an ephemeral disk, and fail on Vercel's read-only disk. Adding a playback source from the dashboard is not yet written to Supabase; the API says so with HTTP 501.
