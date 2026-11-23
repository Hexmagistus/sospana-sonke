-- Fix: the movies read policy looked at streaming_sources, and the
-- streaming_sources and movie_categories policies looked back at movies.
-- Postgres rejects that loop ("infinite recursion detected in policy for
-- relation movies", 42P17), so the anon key could not read public_catalog.
-- The checks now run in SECURITY DEFINER helpers that only return a boolean.
-- They live in a schema PostgREST does not expose, so they are not callable as RPC.

create schema if not exists cinema_private;
revoke all on schema cinema_private from public;
grant usage on schema cinema_private to anon, authenticated;

create or replace function cinema_private.movie_is_published(movie uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (select 1 from public.movies m where m.id = movie and m.published = true);
$$;

create or replace function cinema_private.movie_has_verified_source(movie uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.streaming_sources s
    where s.movie_id = movie
      and s.rights_verified = true
      and char_length(s.licence_evidence_url) > 12
  );
$$;

revoke all on function cinema_private.movie_is_published(uuid) from public;
revoke all on function cinema_private.movie_has_verified_source(uuid) from public;
grant execute on function cinema_private.movie_is_published(uuid) to anon, authenticated;
grant execute on function cinema_private.movie_has_verified_source(uuid) to anon, authenticated;

drop policy if exists movies_public_read on public.movies;
create policy movies_public_read on public.movies
  for select to anon, authenticated
  using (published = true and cinema_private.movie_has_verified_source(id));

drop policy if exists movie_categories_public_read on public.movie_categories;
create policy movie_categories_public_read on public.movie_categories
  for select to anon, authenticated
  using (cinema_private.movie_is_published(movie_id));

drop policy if exists streaming_public_read on public.streaming_sources;
create policy streaming_public_read on public.streaming_sources
  for select to anon, authenticated
  using (rights_verified = true and cinema_private.movie_is_published(movie_id));
