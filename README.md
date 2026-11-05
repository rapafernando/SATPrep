# ScorePath

A private SAT practice web app for a small group (family and friends). Installable on
phones from the browser (PWA), with admin approval for new members and an optional,
per-member-switchable ad slot for the future.

- Daily plan from target score, test date and minutes per day
- Practice sessions by skill or a mixed daily set, step-by-step explanations
- Built-in calculator and a pen/finger scratchpad on every question
- Progress charts, streaks, and a score estimate (a simple placeholder model, not an official predictor)
- Parent accounts that can see linked children's progress
- Admin console: approve or remove members, mark members ad-free, ad settings, sign-ups on/off

Stack: Django 5.2, PostgreSQL 16, gunicorn, WhiteNoise, Docker Compose. No JavaScript
build step.

**Install it:** read `INSTALL.md`.
**Look and feel:** `replica/design/tokens.json` (colours, type, spacing, light and dark) and `replica/design/components.md`. After editing the tokens run `python3 tools/build_tokens.py`; it rewrites `static/css/tokens.css` and checks WCAG contrast. Staff can see every component at `/design/`.
**Design and database:** `replica/architecture.md`, `replica/schema.sql`. **Build, test and security notes:** `replica/build-log.md`, `replica/test-plan.md`, `replica/bugs.md`, `replica/backend.md`, `replica/deploy.md`.

Not affiliated with the College Board or any other company. All 24 sample questions
are original. "SAT" is a trademark of the College Board.

## Develop locally

```bash
python -m venv venv && . venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
export DEBUG=True                       # no database setup needed: it uses a local SQLite file
python manage.py migrate && python manage.py createcachetable && python manage.py seed_content
python manage.py createsuperuser && python manage.py runserver
```

## Tests

```bash
python manage.py test                                   # about 100 tests, SQLite or Postgres
pip install -r e2e/requirements.txt && playwright install chromium
E2E_PYTHON=$(which python) python -m pytest e2e         # browser tests; see e2e/README.md
```

GitHub Actions (`.github/workflows/ci.yml`) runs both, a dependency audit and a Docker build on every push.

## Updating the server

`./deploy/update.sh` on the server pulls from GitHub, backs up, rebuilds and checks health.
Details in `INSTALL.md`.

## Files you will not find here

`.env` (your secrets), backups and the database are never committed. Research notes about the app
this one was modelled on are kept out of git on purpose (see `.gitignore`).

Licence: not chosen yet, so by default all rights are reserved. Third-party parts are listed in `NOTICE.md`.
