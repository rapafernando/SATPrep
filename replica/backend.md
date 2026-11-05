# Backend: ScorePath

Stack: Django 5.2, PostgreSQL 16, gunicorn, WhiteNoise, django-axes, behind Caddy. See `architecture.md`.
The data layer was never fake: every screen reads the real database through the Django ORM. This pass audited it against the replica-backend checklist and closed the gaps.

## What was built

| Area | Status | Where |
| --- | --- | --- |
| Sign up with admin approval | done | `accounts/views.py::signup`, `ApprovalMiddleware` signs out anyone whose approval is withdrawn |
| Sign in, lockout after 6 failures (1 hour, per username + address) | done | django-axes |
| Sessions: http-only, Secure cookie over https, 30 days | done | `settings.py` |
| Sign out | done | Me |
| **Sign out everywhere** | new | `accounts/sessions.py`, `sign_out_everywhere` |
| **Change password** (keeps this phone, ends the others) | new | `PasswordChangeView` |
| **Admin password reset** (shown once, ends their sessions) | new | console Members, `reset_password` |
| **Delete my account** (password confirmed, cascades, last admin protected) | new | `delete_account` |
| Roles: student, parent, staff. Parent sees only linked children | done | `learn/views.py::family`, `core/console.py::staff_required` |
| Database migrations, checked in, run by `entrypoint.sh` | done | `*/migrations/` |
| Check constraints on status and role fields | done | `accounts/models.py`, `learn/models.py` |
| Shared cache for rate limits (was per-process) | new | `CACHES` DatabaseCache, `createcachetable` in entrypoint |
| Sign-up rate limit 5 per hour per address | done | `accounts/views.py` |
| Permissions-Policy header | new | `core/middleware.py` |
| Privacy page naming every processor | new | `/privacy/` |
| Expired sessions cleaned at each start | new | `clearsessions` in entrypoint |
| Seed script, fake data only | done | `seed_content` (24 original sample questions) |
| Backups | done, untested on the server | `deploy/backup.sh` nightly dump, keeps 14 |
| Ads gate (site switch AND per-member ad-free flag) | done | `core/ads.py` |

## Not built, on purpose

- **Payments / Stripe:** a private family app has no billing. Original's passes and App Store subscriptions are marked `skip` in `features.csv`. If ads or paid access ever come, add Stripe Checkout then (test keys first; verify webhook signatures, store event ids, idempotent handlers, one-click cancel).
- **Email (verification, reset links, reminders):** the admin approves every member by hand, so a verified address adds nothing and a mail service would be one more company holding children's data. Password help goes through the admin console instead. If reminders are wanted later: Resend or Postmark from a domain you own, a nightly job, unsubscribe link.
- **OAuth (Google, Apple sign-in):** not needed; no external accounts means no OAuth review. Needed only if a native iOS app ever ships (Apple's rule).
- **Third-party integrations:** none. No Google Calendar, no analytics. Nothing to verify.
- **Background jobs:** none needed. Cleanup runs at startup; the only schedule is the backup cron.

## Security checklist

- [x] secrets only in env vars; `.env` in `.gitignore` and `.dockerignore`; nothing secret in static files. App refuses to start without `SECRET_KEY`.
- [x] input validated on the server: every form is a Django form or ModelForm; answers are length-capped and graded server-side; numeric answers parsed with fractions, never `eval`; calculator is client side and uses a parser.
- [x] authorisation on every read and write, tested with a second user: `SecondUserIsolationTests`, `test_cannot_open_someone_elses_session`, `FamilyTests`, `ConsolePasswordResetTests.test_non_staff_cannot_reset_anyones_password`, sign-out-everywhere only touches the caller.
- [x] rate limits: login (axes), sign-up (5 an hour, shared across workers), the site sends no email or SMS.
- [x] webhooks: none exist.
- [x] uploads: none exist.
- [x] no user data in URLs or logs: ids are UUIDs, no search or query strings carry personal data, no application logging of answers or names.
- [x] dependencies audited: `pip-audit -r requirements.txt` found no known vulnerabilities (2026-11-05). Re-run before each deploy.
- [x] privacy policy lists every processor (own server, DuckDNS, Let's Encrypt, ad network if on): `/privacy/`.
- [x] `manage.py check --deploy`: three warnings, all by design or setting-dependent: HSTS (set `HSTS_SECONDS` once the https address is proven), SSL redirect (Caddy does it), and the key-length check only fires on a short test key (`openssl rand -base64 48` passes).

## Known risks to keep an eye on

1. **Ad code is trusted HTML.** Anything pasted into Ads runs on members' phones, so there can be no strict Content-Security-Policy while ads are on. Paste code only from a network you trust. If members are under 13, check the network's child-directed rules (COPPA) before turning ads on.
2. **The admin password reset message** is shown once on screen and stored in the admin's session flash. Reset only when the person is with you or on a private channel.
3. **Tests ran on SQLite and a throwaway Postgres 16 (89 passing).** Docker Compose itself has not been run on the rapamedia server yet. That is `/replica-deploy`.
4. **`/admin/` path** is guessable; set `ADMIN_URL` to something private in `.env`.

## Env variables

All names are in `.env.example`, none have values. New this pass: `HSTS_SECONDS`.

## Test status

89 tests pass (SQLite and Postgres 16): auth, approval, lockout, sign-up limits, password change, sign-out-everywhere, deletion cascade, console permissions, ads gating, two-user isolation, design-token contrast.
