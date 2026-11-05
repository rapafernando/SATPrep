# ScorePath: architecture

Built from `replica/recon.md` and `replica/features.csv` (the Brainblast recon, public sources only).
This is a **web app for a small private group** (the owner's daughter and her friends), installable on
phones as a PWA, run on the owner's home server ("rapamedia"). It does not copy Brainblast's content,
name, art or screens. The 24 sample questions are original; `replica/screens/` is reference only.

## 1. Stack, one line each

| layer | choice | why |
| --- | --- | --- |
| web app | **Django 5.2 LTS** (Python 3.12, server-rendered templates) | login, sessions, forms, CSRF, admin and migrations are built in; the owner needs an admin who approves members, and Django gives that nearly free. Not the Next.js default: no build step to maintain on a home server. |
| styling | one hand-written CSS file with CSS variables, dark mode via `prefers-color-scheme` | no toolchain; tokens can be swapped by `/replica-design` |
| phone "app" | **PWA**: `/manifest.webmanifest`, `/sw.js`, icons, install banner | the "like OpenGym" requirement: Add to Home Screen on iPhone and Android with its own icon, full screen, still just the website. No Expo, no app stores |
| database | **PostgreSQL 16** in Docker | one database, real constraints (check, unique, FK), easy `pg_dump` backups |
| ORM / migrations | Django ORM; migrations are the schema source of truth | |
| auth | Django auth, custom `User` (UUID id), `django-axes` lockout | username + password; no email required (kids may not want to give one) |
| member approval | `User.approval_status` (pending / approved / rejected) checked at login and on every request | the owner approves each sign-up |
| payments | none | free private app. Ads are the only planned income (section 5) |
| email | none | no reset-by-email in v1; admin resets passwords (`changepassword`) |
| jobs | none | everything is computed on request; no background worker to babysit |
| files | none uploaded; static files via WhiteNoise | |
| math | KaTeX vendored in `static/vendor/katex` (no CDN) | works offline and no third-party requests from a kids' app |
| hosting | Docker Compose (`db` + `web`) behind the host's **Caddy** with a new DuckDNS name; gunicorn, WhiteNoise | matches the owner's existing server setup; `web` publishes only on 127.0.0.1 |

No microservices, one repo, one database.

## 2. Schema

Full DDL: `replica/schema.sql` (generated from the migrations with `pg_dump -s`).
**12 tables of our own** (10 entities + 2 Django join tables for user groups/permissions). Framework tables
(sessions, auth permissions, axes, migrations) are extra.

| table | purpose | owner column | notes |
| --- | --- | --- | --- |
| `accounts_user` | a person; role student/parent; `approval_status`; `ad_free`; `approved_at/by` | self | UUID PK; `approved_by` is `SET NULL` |
| `accounts_parentlink` | parent can view child's progress | `parent_id`, `child_id` | unique pair, check parent <> child, both `CASCADE` |
| `core_sitesettings` | single row: `signups_open`, `ads_enabled`, `ad_label`, `ad_html` | – | singleton enforced by unique + check; **ads default OFF** |
| `learn_skill` | a topic (track math / reading-writing, domain, name, slug, lesson text) | – | |
| `learn_question` | multiple choice (A–D) or typed number; explanation; difficulty 1–3 | – | check on difficulty and type; `skill` is `PROTECT`; retire with `is_active=false`, do not delete |
| `learn_goal` | current score, target, test date, minutes/day, optional school | `user_id` (one per user) | `CASCADE` |
| `learn_practicesession` | one run (daily or by skill); ordered `question_ids`; `position`; `finished_at` | `user_id` | `CASCADE` |
| `learn_attempt` | one answer; correct?; seconds | `user_id` | unique per (session, question) so a double submit cannot count twice; `question` is `PROTECT`, `session` is `SET NULL` |
| `learn_skillprogress` | running mastery 0–1 per user and skill | `user_id` | unique (user, skill); check 0–1 |
| `learn_scoreestimate` | daily snapshot of the estimated score | `user_id` | unique (user, date) |

Conventions used: UUID primary keys, `created_at`/`updated_at`, `timestamptz` stored in UTC (display
timezone from `TIME_ZONE`, default America/New_York), foreign-key indexes, status fields as choices with
check constraints. Delete rules are enforced by Django (in Python), not by `ON DELETE` clauses in the DDL.
No money columns: there is nothing to charge.

**Access rules: one authorisation check per query in the data layer, no row-level security** (Django
connects as one database user). Every learner query is filtered by `request.user`; sessions are fetched with
`get_object_or_404(..., user=request.user)`; the only cross-user read is the parent Family page, restricted
through `parentlink`. `/console/*` requires `is_staff`. Tests cover each of these.

## 3. Routes (29 app routes plus Django admin at `ADMIN_URL`)

| method path | what it does | who | flow |
| --- | --- | --- | --- |
| GET/POST `/signup/` | create a *pending* account (honeypot, 5/hour per IP) | anyone | join |
| GET `/signup/done/` | "wait for approval" page | anyone | join |
| GET/POST `/login/` | sign in; pending/rejected get a clear message; lockout after 6 failures | anyone | sign-in |
| POST `/logout/` | sign out | member | sign-in |
| GET `/` | today: streak, questions done today, score estimate, start daily set | approved | home |
| GET/POST `/onboarding/` | set or edit goal (score, target, date, minutes) | approved | onboarding |
| GET `/plan/` | days left, questions per day, pace note | approved | plan |
| GET `/progress/` | score line, 14-day bars, per-skill mastery | approved | progress |
| GET `/family/` | linked children's week at a glance | parent (404 otherwise) | family |
| GET `/skills/<slug>/` | skill lesson + start | approved | learn |
| POST `/skills/<slug>/practice/` | start an 8-question skill session | approved | practice |
| POST `/practice/daily/` | start today's mixed set | approved | practice |
| GET `/practice/<id>/` | show the current question (calculator, scratchpad, timer) | owner | practice |
| POST `/practice/<id>/answer/` | grade and record (idempotent) | owner | practice |
| POST `/practice/<id>/skip/` | record a miss | owner | practice |
| GET `/practice/<id>/review/` | right/wrong and worked explanation | owner | practice |
| POST `/practice/<id>/next/` | advance only after an answer exists; finish at the end | owner | practice |
| GET `/practice/<id>/done/` | session summary | owner | practice |
| GET `/console/` `approvals/` `members/` `settings/` | admin console: counts, pending queue, member list, sign-ups and ad settings | staff | admin |
| POST `/console/users/<id>/action/` | approve, reject, revoke, ad-free on/off (cannot revoke yourself) | staff | admin |
| GET `/manifest.webmanifest`, `/sw.js`, `/offline/`, `/install/` | PWA files and install help | anyone | install |
| GET `/robots.txt`, `/healthz` | disallow all crawlers; health check for Docker | anyone | ops |

Webhooks: none. Background jobs: none. Third-party APIs: none.

## 4. Admin, approval and ads, as built

- **First admin** is created from `DJANGO_SUPERUSER_*` on first start, auto-approved and marked ad-free.
- **Approval:** new accounts are `pending`. Login is refused with "waiting for approval". If an approved
  person is later revoked, `ApprovalMiddleware` signs them out on their next request (covered by a test; this
  test caught a real middleware-ordering bug during the build).
- **Ads:** shown only if (1) `ads_enabled`, (2) ad code pasted, (3) viewer is a signed-in approved member and
  (4) **not** `ad_free`. One function decides: `core/ads.py::ads_visible_for`. Slots exist on home, progress
  and session-summary only, never on a question page. The owner toggles ad-free per member in
  Admin → Members; the master switch is Admin → Settings.

## 5. The parts that bite

1. **Minors' data and ads.** SAT prep users are mostly 15–18, some younger. Collect the minimum (username,
   first name or nickname, optional email, no birth date, no photos). Before turning ads on: a short privacy
   policy; most ad networks treat services used by under-13s or "child-directed" content specially (no
   personalised ads, restricted categories), and in the US the COPPA rule applies to under-13s. Start with
   non-personalised ads, keep the owner's own account and any young members ad-free, and read the chosen
   network's current rules. This is a risk list, not legal advice.
2. **Question content.** The app is only as good as its bank. The 24 sample questions are original; real
   College Board / Khan / Bluebook items and Brainblast's content must not be copied. The score estimate is a
   placeholder (blend of self-reported score and difficulty-weighted accuracy), not a predictor, and the UI says so.
   Adding hundreds of original, correct questions with worked solutions is the main long-term work.
3. **Home-server exposure.** Real visitors reach the owner's LAN gateway. Mitigations in place: port bound to
   127.0.0.1, HTTPS via Caddy with HSTS, secure cookies, CSRF trusted origins, lockout on logins, sign-up rate
   limit and honeypot, approval gate, `robots.txt` disallow, nothing public until approved. Remaining risks: the
   sign-up rate limit uses the in-process cache, so with 3 gunicorn workers the real limit is up to 15/hour per
   IP; a leaked `.env`; a VPN kill switch blocking Docker or inbound traffic (see INSTALL.md); no off-site backup
   unless the owner copies `/mnt/media/backups` elsewhere.
4. **Time zones.** Streaks and "today" use `TIME_ZONE` (default America/New_York) and local midnight; a
   member travelling sees days roll over on the server's clock, not theirs.
5. **Idempotency and races.** Double taps and retries on phones are common: attempts are unique per
   (session, question) and `record_attempt` returns the first one; mastery rows are locked with
   `select_for_update`. Tested.
6. **Service worker caching.** The worker caches only public static files and the offline page, never signed-in
   pages, so one member's data cannot be served to another on a shared device. After a deploy, bump
   `APP_VERSION` to refresh phones. iOS limits: no install prompt (manual Add to Home Screen), and web push is not
   included.
7. **Offline.** Practice needs the network (answers are graded on the server). Offline shows a friendly page.
8. **Not verified in this build:** `docker compose up` itself (no Docker daemon was available where it was
   written). The Dockerfile, entrypoint and compose file are straightforward but untested; the same code was
   verified on Postgres 16 and SQLite (61 tests), with gunicorn and the production static-file pipeline.

## 6. Build order

| step | scope | screens / tables / routes | status |
| --- | --- | --- | --- |
| 1. Vertical slice | sign up → approve → onboarding → daily set → answer → review → progress | users, goal, skill, question, session, attempt, progress; 17 routes | **built, tested** |
| 2. Install + admin | PWA, install help, console, ad-free, sign-ups switch, parent link | sitesettings, parentlink; 12 routes | **built, tested** |
| 3. Content | grow the bank: more skills and 200+ original questions with explanations; admin import via `seed_content --file` | question, skill | next |
| 4. Should-haves | diagnostic test (mixed set that sets starting mastery), review mistakes list, bookmarked questions, timed full-section mode, richer lessons | + `learn_bookmark`, `learn_diagnostic` fields | later |
| 5. Could-haves | password reset by admin from the console, per-skill streak badges, weekly parent email (needs an email service) | | later |
| 6. Fixes from user reviews | thin sample (4 reviews); revisit `replica/fixes.md` once more reviews are gathered | | later |
| 7. Monetise | choose an ad network, write the privacy policy, switch on non-personalised ads, keep ad-free members | no schema change | when it grows |

Next step: **`/replica-design`** (screens, tokens and the look of the app).
