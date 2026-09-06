# Sospana Sonke — Authentication System & Google Sign-In Report

**Date:** 6 September 2026 · **Scope:** how sign-in works now, a security audit, and the
manual setup still required. **No secrets are printed here** (and the design uses none in
the frontend).

---

## 1. What authentication Sospana Sonke has now

Sospana Sonke already had a working, secure "Continue with Google" — it did not need to be
built from scratch. It was audited and lightly hardened this pass. The system now offers two
ways in, both ending in the *same* Sospana Sonke session:

**a) Continue with Google (Google Identity Services / ID-token flow).**
The browser loads Google Identity Services, the user authenticates with Google, and Google
returns a signed **ID token** to the page. The page posts that token to the backend
`POST /auth/google`. The **backend** then:
- rejects the request if Google sign-in isn't configured (503);
- verifies the token with Google (`oauth2.googleapis.com/tokeninfo` — signature + expiry);
- checks the **audience** (`aud`) equals our own client ID (so a token minted for another app
  is refused);
- checks the **issuer** (`iss`) is `accounts.google.com` *(added this pass)*;
- requires Google's **`email_verified` = true** (so an unverified/spoofed email is refused);
- finds the user by that Google-verified email, or creates a new **candidate** account;
- refuses disabled/deleted accounts;
- issues Sospana Sonke's own access + refresh tokens, stamped with the role read **from our
  database** — never from Google or the browser.

**Why no client secret:** this flow verifies a signed ID token; it does not exchange an
authorization code, so **no Google client secret exists in the frontend, the backend, or
Git**. That satisfies "don't put secrets in frontend code" by removing the secret entirely.

**b) Email + password, with optional authenticator (TOTP) code.**
The existing form signs in with email + password and, if the account has MFA enabled, prompts
for a 6-digit authenticator code. The MFA endpoints (`/auth/mfa/enable` etc.) are already in
place, so authenticator-app TOTP is live and passkeys/WebAuthn or SMS OTP can be added behind
the same login screen later.

> Note on wording: your brief said "Email + OTP". The app today uses **email + password
> (+ optional TOTP)**, not a passwordless email one-time-code. If you specifically want a
> passwordless email-code login, that's a separate build — tell me and I'll add it.

**Authentication vs authorization are kept separate**, exactly as you asked. Google answers
"who is this person?"; Sospana Sonke's own layer answers "what may they do?" — role, admin
status, and access are all determined server-side from the database on every request.

## 2. Security audit

Code-verified means confirmed by reading the implementation; live-test means it needs a
configured client ID + a browser (I can't run a real Google login from here).

| Test | Result |
|------|--------|
| Successful Google login | Code-verified; needs one live test once the client ID is set |
| Failed login (bad/tampered token) | Code-verified — `tokeninfo` ≠ 200 → 401 |
| Cancelled login | Safe — Google callback never fires, no session created |
| Expired OAuth session (expired ID token) | Code-verified — Google rejects it → 401 |
| Invalid callback | N/A to this flow (no redirect callback); a bad credential → 401 |
| Account linking | Code-verified — links **only** on Google-verified email; role stays `candidate` |
| Duplicate accounts | Code-verified — email is unique; find-or-create by verified email |
| Unauthorized API access | Code-verified — protected routes require a valid Sospana Sonke JWT |
| User A reading User B's data | Code-verified — per-resource ownership (IDOR) checks throughout |
| Administrator authorization | Code-verified — admin is **never** granted via Google; role comes from the DB |
| Logout | Client drops the tokens; access token expires on its own (see caveat) |
| Session expiration | Code-verified — access-token expiry + refresh endpoint |
| Production Vercel deploy | **Needs manual config** (Section 3) |
| Env-var configuration | **Needs manual config** (Section 3) |

**Honest caveats (not blockers, but know them):**
- **Sessions are stateless JWTs.** Logout is client-side and there's no server-side token
  revocation, so a token stays valid until it expires. Keep the access-token TTL short and
  rely on refresh. A server-side revocation/denylist is a future hardening.
- **Account identity is pinned to the verified email, not Google's immutable `sub`.** This is
  safe against email spoofing (we require `email_verified`), but storing Google's `sub` would
  further protect against edge cases (a Google account changing its primary email). That needs
  a small DB column + migration — recommended, not yet done.
- **Token verification uses Google's `tokeninfo` endpoint.** It's correct and secure, but for
  production scale Google recommends *local* verification with the `google-auth` library (no
  per-login external call, no rate limit). Optional upgrade.
- I could not run a live end-to-end Google login from here; the audit above is by code review.

## 3. What you must still configure manually

Nothing in the code needs changing to go live — but Google sign-in stays **hidden and
disabled until you set the client ID in both places.**

### Google Cloud Console
1. **OAuth consent screen** — User type *External*; add app name, your support email, and the
   scopes `openid`, `email`, `profile`; add your production domain under Authorized domains;
   add yourself as a test user (or publish the app).
2. **Credentials → Create credentials → OAuth client ID → Web application.**
3. **Authorized JavaScript origins** (this flow uses *origins*, not redirect URIs):
   - `http://localhost:3000` — local dev
   - `https://<your-production-vercel-domain>` — production
   - Vercel **preview** deployments get random subdomains and Google does **not** allow
     wildcard origins, so Google sign-in won't work on ad-hoc previews unless you add each
     preview URL (or a stable preview alias). Test on localhost + production.
   - **Authorized redirect URIs:** none needed for this flow. (Only if you ever switch to the
     OAuth *code* flow would you add redirect URIs and a client secret.)
4. A client **secret** may be generated — you do **not** need it and must **not** put it
   anywhere. This flow doesn't use it.

### Environment variables
- **Vercel (frontend):** `NEXT_PUBLIC_GOOGLE_CLIENT_ID` = the Web client ID. (This is the
  public client ID, safe to expose — it is *not* a secret.)
- **Render (backend):** `GOOGLE_CLIENT_ID` = **the same** client ID (used to verify the
  token's audience). Must match the frontend value exactly.
- **Render:** confirm `CORS_ORIGINS` includes your Vercel frontend origin, and (for the
  verification emails set up separately) the Gmail SMTP vars.
- **No `GOOGLE_CLIENT_SECRET` anywhere.**

Once both client-ID variables are set and redeployed, the "Continue with Google" button
appears automatically and the backend endpoint activates.

## 4. Recommended next steps (optional)
1. Add a `google_sub` (+ `last_login_at`, optional `avatar_url`) column to the user model and
   link on `sub` as well as email — with a DB migration for the live Postgres.
2. Switch token verification to local `google-auth` validation for production robustness.
3. Build the missing frontend `/verify` and `/reset-password` pages (the email links
   currently hit the API directly).
4. Consider short access-token TTL + refresh-token rotation, and a revocation list if you want
   true server-side logout.

---

*"Continue with Google" answers who someone is. Sospana Sonke's own role/permission checks —
which run on every request and never trust the browser — decide what they can do. Those two
stay separate, by design.*
