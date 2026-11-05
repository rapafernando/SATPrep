# Deploy: ScorePath (GitHub, then rapamedia)

Date: 2026-11-05. Route: push to a private GitHub repository, then `git pull` on rapamedia (`./deploy/update.sh`).
Nothing was pushed or started by Claude. The GitHub and server steps are yours.

## Preflight

| check | result |
| --- | --- |
| Django tests (101) on Python 3.13, and on Python 3.12 (the Docker image's version) three times in a row | pass |
| Browser tests (68 cases, production-like server) | pass (run on 3.13) |
| `makemigrations --check` | no changes pending |
| Design tokens up to date, WCAG AA | 21 pairs, 0 failing |
| `pip-audit -r requirements.txt` | no known vulnerabilities (2026-11-05) |
| `manage.py check --deploy` | 3 warnings, all expected: HSTS (set `HSTS_SECONDS` later), SSL redirect (Caddy does it), key length only on short test keys |
| Must-have parity (`features.csv`) | 9 of 13 yes, 4 partial. Partial: lesson path, daily session blocks, segmented progress bar, question bank size |
| Open S1 / S2 bugs | none (`bugs.md`: six S3/S4, all fixed) |
| Rebrand sweep (code, templates, static, deploy, root docs) | clean: no name, text or asset from the original |
| Secret scan (keys, tokens, private keys, hard-coded passwords) | clean. `.env` ignored, only `.env.example` tracked |
| Personal data in the repo | none. A home LAN address in the docs was replaced with an example one |
| Privacy page, account deletion, own icon and titles | live in the app: `/privacy/`, Me, Delete my account |
| `docker compose config` with `.env.example` | valid |
| Docker image build, and a real start on rapamedia | **not run**: no Docker daemon here. First run happens on your server |
| GitHub Actions workflow | written, **not run** (needs the repo on GitHub). First push will show |

Left out of git on purpose (`.gitignore`): `replica/screens/` (screenshots of the original app), `replica/reviews.csv`,
`replica/recon.md`, `replica/feedback.md`, `replica/fixes.md` (public reviews and notes about the original), `.env`,
databases, backups, and the dark and wide screenshot sets. They stay in your zip and on your computer.
`features.csv` and `architecture.md` still name the original app, because they are the parity matrix; that is fine for a private repository.
**Make the GitHub repository private.** Public would also be possible, but then remove those two mentions first and pick a licence.

## Step 1: GitHub (you)

1. github.com, New repository, name `scorepath`, **Private**, do not add a README or licence (the folder has them).
2. On your computer, in the project folder (it already has a first commit on branch `main`):
   ```bash
   git remote add origin git@github.com:YOURNAME/scorepath.git
   git push -u origin main
   ```
   (HTTPS works too; GitHub will ask you to sign in.)
3. Open the **Actions** tab. The `CI` workflow runs four jobs: tests on Postgres, dependency audit, browser tests,
   Docker build. If one fails, send me its log.
4. Optional: Settings, Branches, protect `main` so a failing CI blocks merges.

## Step 2: rapamedia (you)

Follow `INSTALL.md` from the top. In short: add a read-only **deploy key** (steps in INSTALL.md section 1), `git clone`,
`cp .env.example .env` and fill it in, `docker compose up -d --build`, add the Caddy block, create the DuckDNS name.

Check from the server: `curl http://127.0.0.1:8010/healthz` prints `{"status": "ok"}`.

## Step 3: every update after that

On your computer: change, `git commit`, `git push`. On rapamedia: `./deploy/update.sh`
(backs up, pulls, rebuilds, waits for health, prints the rollback command if it fails).

## Before sharing the link

1. Sign in as admin, change nothing else, open `/console/` and `/privacy/`.
2. Make a test member from your phone, approve it, run one practice set, install it to the home screen.
3. Set `ADMIN_URL` in `.env` to something private (for example `manage-7f3k/`), then `docker compose up -d`.
4. Add the nightly backup line from INSTALL.md to `crontab -e`, and run `./deploy/backup.sh` once by hand.
5. After a few days of using https without problems, set `HSTS_SECONDS=31536000` and `docker compose up -d`.

## Watch in the first week

- `docker compose logs --tail 100 web` after the first real sign-ups: look for 500s.
- Uptime: a free monitor (for example UptimeRobot) on `https://YOUR-NAME.duckdns.org/healthz`, alert to your phone.
- DuckDNS: confirm the updater still refreshes your IP, and that the certificate renews (Caddy does it by itself).
- Backup file appears every night and is bigger than a few KB.
- Disk space: `df -h` on the media drive, since backups and Docker images both use it.
