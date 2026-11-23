-- Sospana Cinema schema.
-- Public visitors can read published, rights-verified rows.
-- Writes are for the service role only (it bypasses row level security).
-- There is no viewer account.

create extension if not exists pgcrypto;

create table if not exists public.content_sources (
  id uuid primary key default gen_random_uuid(),
  provider_name text not null,
  website_url text not null,
  provider_type text not null,
  api_status text not null default 'unknown',
  terms_reference text,
  created_at timestamptz not null default now(),
  constraint content_sources_website_https check (website_url ~* '^https://')
);

create table if not exists public.categories (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  description text not null,
  constraint categories_slug_shape check (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$')
);

create table if not exists public.movies (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  slug text not null unique,
  description text not null,
  release_year integer not null,
  runtime_seconds integer not null,
  genres text[] not null default '{}',
  language text not null,
  country text not null,
  director text not null default '',
  -- "cast" is reserved in SQL, so the column is cast_members.
  cast_members text[] not null default '{}',
  content_type text not null,
  age_rating text not null,
  poster_url text,
  backdrop_url text,
  trailer_url text,
  published boolean not null default false,
  featured boolean not null default false,
  catalogue_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint movies_slug_shape check (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  constraint movies_year check (release_year between 1888 and 2100),
  constraint movies_runtime check (runtime_seconds > 0 and runtime_seconds < 86400),
  constraint movies_content_type check (content_type in ('movie', 'short', 'series', 'documentary')),
  constraint movies_age_rating check (age_rating in ('All', '6+', '9+', '13+', '16+', '18+')),
  constraint movies_title_present check (char_length(title) between 1 and 300)
);

create table if not exists public.movie_categories (
  movie_id uuid not null references public.movies (id) on delete cascade,
  category_id uuid not null references public.categories (id) on delete cascade,
  primary key (movie_id, category_id)
);

create table if not exists public.streaming_sources (
  id uuid primary key default gen_random_uuid(),
  movie_id uuid not null references public.movies (id) on delete cascade,
  provider_id uuid not null references public.content_sources (id),
  playback_type text not null,
  -- Authorized playback URL. Embed, HLS and MP4 all live here.
  -- playback_type says which player to use. This is not a download we host.
  authorized_embed_url text not null,
  licence_type text not null,
  licence_evidence_url text not null,
  source_record_url text not null,
  licence_territories text[] not null default '{WORLD}',
  licence_expiry date,
  rights_verified boolean not null default false,
  playback_status text not null default 'unavailable',
  last_verified_at timestamptz,
  rights_holder text not null default '',
  subtitles jsonb not null default '[]'::jsonb,
  quality_note text,
  constraint streaming_playback_type check (playback_type in ('embed', 'mp4', 'hls')),
  constraint streaming_playback_status check (playback_status in ('available', 'unavailable', 'broken')),
  constraint streaming_https check (authorized_embed_url ~* '^https://'),
  constraint streaming_evidence_https check (licence_evidence_url ~* '^https?://'),
  constraint streaming_verified_needs_evidence check (
    rights_verified = false or (
      char_length(licence_evidence_url) > 12
      and char_length(authorized_embed_url) > 12
    )
  )
);

create table if not exists public.content_reviews (
  id uuid primary key default gen_random_uuid(),
  movie_id uuid not null references public.movies (id) on delete cascade,
  review_status text not null,
  age_suitability text not null,
  review_notes text not null,
  reviewed_at date not null,
  constraint content_reviews_status check (review_status in ('pending', 'approved', 'rejected')),
  constraint content_reviews_suitability check (
    age_suitability in ('preschool', '6-8', '9-12', 'family', 'not-for-kids')
  )
);

create table if not exists public.takedown_requests (
  id uuid primary key default gen_random_uuid(),
  claimant_name text not null,
  contact_email text not null,
  content_id text not null,
  reason text not null,
  status text not null default 'received',
  created_at timestamptz not null default now(),
  constraint takedown_status check (status in ('received', 'reviewing', 'removed', 'rejected')),
  constraint takedown_email check (contact_email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  constraint takedown_reason_length check (char_length(reason) between 20 and 5000)
);

create index if not exists movies_country_idx on public.movies (country);
create index if not exists movies_language_idx on public.movies (language);
create index if not exists movies_year_idx on public.movies (release_year);
create index if not exists movies_content_type_idx on public.movies (content_type);
create index if not exists movies_published_created_idx on public.movies (published, created_at desc);
create index if not exists movies_title_lower_idx on public.movies (lower(title));
create index if not exists streaming_sources_movie_idx on public.streaming_sources (movie_id);
create index if not exists streaming_sources_verified_idx on public.streaming_sources (rights_verified, playback_status);
create index if not exists content_reviews_movie_idx on public.content_reviews (movie_id, review_status);
create index if not exists takedown_requests_status_idx on public.takedown_requests (status, created_at desc);
create index if not exists movie_categories_category_idx on public.movie_categories (category_id);

alter table public.content_sources enable row level security;
alter table public.categories enable row level security;
alter table public.movies enable row level security;
alter table public.movie_categories enable row level security;
alter table public.streaming_sources enable row level security;
alter table public.content_reviews enable row level security;
alter table public.takedown_requests enable row level security;

-- Visitors read published movies that have a verified rights record.
drop policy if exists movies_public_read on public.movies;
create policy movies_public_read on public.movies
  for select to anon, authenticated
  using (
    published = true
    and exists (
      select 1 from public.streaming_sources s
      where s.movie_id = movies.id
        and s.rights_verified = true
        and char_length(s.licence_evidence_url) > 12
    )
  );

drop policy if exists categories_public_read on public.categories;
create policy categories_public_read on public.categories
  for select to anon, authenticated
  using (true);

drop policy if exists movie_categories_public_read on public.movie_categories;
create policy movie_categories_public_read on public.movie_categories
  for select to anon, authenticated
  using (
    exists (
      select 1 from public.movies m
      where m.id = movie_categories.movie_id
        and m.published = true
    )
  );

drop policy if exists sources_public_read on public.content_sources;
create policy sources_public_read on public.content_sources
  for select to anon, authenticated
  using (true);

drop policy if exists streaming_public_read on public.streaming_sources;
create policy streaming_public_read on public.streaming_sources
  for select to anon, authenticated
  using (
    rights_verified = true
    and exists (
      select 1 from public.movies m
      where m.id = streaming_sources.movie_id
        and m.published = true
    )
  );

drop policy if exists reviews_public_read on public.content_reviews;
create policy reviews_public_read on public.content_reviews
  for select to anon, authenticated
  using (true);

-- Takedown rows hold a name and an email. Visitors cannot read or write them.
-- The server inserts them with the service role after it checks the form.
revoke all on public.takedown_requests from anon, authenticated;

grant select on public.content_sources, public.categories, public.movies,
  public.movie_categories, public.streaming_sources, public.content_reviews
  to anon, authenticated;

-- One row per published movie, for the anon key. security_invoker keeps RLS on.
create or replace view public.public_catalog
with (security_invoker = true) as
select
  m.id,
  m.title,
  m.slug,
  m.description,
  m.release_year,
  m.runtime_seconds,
  m.genres,
  m.language,
  m.country,
  m.director,
  m.cast_members,
  m.content_type,
  m.age_rating,
  m.poster_url,
  m.backdrop_url,
  m.trailer_url,
  m.featured,
  m.catalogue_note,
  m.created_at,
  m.updated_at,
  coalesce(
    (
      select json_agg(json_build_object(
        'id', s.id,
        'providerId', s.provider_id,
        'playbackType', s.playback_type,
        'url', s.authorized_embed_url,
        'licenceType', s.licence_type,
        'licenceEvidenceUrl', s.licence_evidence_url,
        'sourceRecordUrl', s.source_record_url,
        'licenceTerritories', s.licence_territories,
        'licenceExpiry', s.licence_expiry,
        'rightsVerified', s.rights_verified,
        'playbackStatus', s.playback_status,
        'lastVerifiedAt', s.last_verified_at,
        'rightsHolder', s.rights_holder,
        'subtitles', s.subtitles,
        'qualityNote', s.quality_note
      ))
      from public.streaming_sources s
      where s.movie_id = m.id and s.rights_verified = true
    ),
    '[]'::json
  ) as sources,
  (
    select json_build_object(
      'id', r.id,
      'reviewStatus', r.review_status,
      'ageSuitability', r.age_suitability,
      'reviewNotes', r.review_notes,
      'reviewedAt', r.reviewed_at
    )
    from public.content_reviews r
    where r.movie_id = m.id
    order by r.reviewed_at desc
    limit 1
  ) as review,
  coalesce(
    (
      select json_agg(c.slug)
      from public.movie_categories mc
      join public.categories c on c.id = mc.category_id
      where mc.movie_id = m.id
    ),
    '[]'::json
  ) as category_slugs
from public.movies m
where m.published = true;

grant select on public.public_catalog to anon, authenticated;
