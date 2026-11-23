-- Supabase gives anon and authenticated every privilege on new public tables
-- by default. Row level security already blocks their writes, but keep the
-- grants to what the app uses: read the catalogue, and (from 0002) insert the
-- four complaint-form columns. TRUNCATE is not covered by RLS, so it must go.

revoke insert, update, delete, truncate, references, trigger
  on public.content_sources, public.categories, public.movies,
     public.movie_categories, public.streaming_sources, public.content_reviews,
     public.public_catalog
  from anon, authenticated;

revoke all on public.takedown_requests from authenticated;
revoke select, update, delete, truncate, references, trigger
  on public.takedown_requests from anon;
grant insert (claimant_name, contact_email, content_id, reason)
  on public.takedown_requests to anon;

grant select on public.content_sources, public.categories, public.movies,
  public.movie_categories, public.streaming_sources, public.content_reviews,
  public.public_catalog
  to anon, authenticated;
