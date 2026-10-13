# Administrator two-factor authentication

Administrator tools require an authenticator code. Sign-in does not, so the
admin created at boot, and any admin already in the database, can enrol
without being locked out.

## First sign-in (including the boot admin)

1. Sign in at `/login` with the administrator email and password. No code is
   asked for yet.
2. Open **Security** (`/security`). The page explains that administrator tools
   stay closed until two-factor authentication is on.
3. Choose **Set up MFA**, add the secret to an authenticator app, and enter
   the current 6-digit code.
4. Open **Admin** again. The dashboard and the other administrator routes
   work from this point.
5. The next password sign-in asks for the authenticator code. Google sign-in
   for that same verified email asks for it too.

Until step 3 is done, `GET /api/v1/admin/...` answers 403 with
"Set up two-factor authentication before using administrator tools."
`/auth/me`, MFA setup, and sign-out keep working.

The boot row is created in `app/services/bootstrap.py` with
`email_verified` set and MFA left off, only when that email does not already
exist. Deploying again does not reset an admin who has already enrolled.

## After enrolment

An administrator cannot turn two-factor authentication off. `POST /auth/mfa/disable`
answers 403 for that role. A candidate account can still disable it.

Password sign-in and Google sign-in both ask for the current code once MFA is
on. A password reset does not remove that requirement. If the authenticator
is lost, someone with access to the database has to set `mfa_enabled` off and
clear `mfa_secret` on that user, then the owner signs in with the password
and enrols again from Security. There is no second break-glass code in the app.
