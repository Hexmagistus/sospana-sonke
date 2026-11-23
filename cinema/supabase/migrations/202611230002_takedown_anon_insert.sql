-- Let the public complaint form insert a takedown request with the anon key.
-- Visitors can only insert the four form fields. Status always starts as
-- 'received' (the column default), and visitors still cannot read, change or
-- delete any complaint. The table's check constraints validate the email and
-- the reason length. The Next.js server also validates and rate-limits first.

grant insert (claimant_name, contact_email, content_id, reason)
  on public.takedown_requests to anon;

drop policy if exists takedown_public_insert on public.takedown_requests;
create policy takedown_public_insert on public.takedown_requests
  for insert to anon
  with check (
    status = 'received'
    and char_length(claimant_name) between 2 and 200
    and char_length(content_id) between 1 and 200
  );
