#!/usr/bin/env bash
# Update the running ScorePath from GitHub.
#   ./deploy/update.sh                 # pull main, back up the database, rebuild, wait until healthy
#   BRANCH=other ./deploy/update.sh     # a different branch
#   SKIP_BACKUP=1 ./deploy/update.sh    # only if you know why
# Your .env is never touched except for APP_VERSION (set to the new commit so phones refresh).
set -euo pipefail

cd "$(dirname "$0")/.."
BRANCH="${BRANCH:-main}"
PORT="${WEB_PORT:-8010}"

[ -f .env ] || { echo "No .env here. Copy .env.example to .env first (see INSTALL.md)." >&2; exit 1; }
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo ".env is tracked by git. Run: git rm --cached .env   and make sure it is in .gitignore." >&2
  exit 1
fi
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "This folder has local changes to tracked files. Undo or stash them first:" >&2
  git status --short >&2
  exit 1
fi

before="$(git rev-parse --short HEAD)"
git fetch --quiet origin "$BRANCH"
if [ "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$BRANCH")" ]; then
  echo "Already up to date at $before."
  exit 0
fi

echo "Changes coming in:"
git --no-pager log --oneline "HEAD..origin/$BRANCH"

if [ -z "${SKIP_BACKUP:-}" ]; then
  echo "Backing up the database first..."
  ./deploy/backup.sh || { echo "Backup failed, so nothing was updated." >&2; exit 1; }
fi

git merge --ff-only "origin/$BRANCH"
after="$(git rev-parse --short HEAD)"

if grep -q '^APP_VERSION=' .env; then
  sed -i "s/^APP_VERSION=.*/APP_VERSION=$after/" .env
else
  printf '\nAPP_VERSION=%s\n' "$after" >> .env
fi

echo "Rebuilding..."
docker compose up -d --build

echo "Waiting for the site to answer..."
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
    echo "ScorePath is up at $after (was $before)."
    docker compose ps
    exit 0
  fi
  sleep 3
done

echo "The site did not answer within 3 minutes." >&2
echo "Look:      docker compose logs --tail 80 web" >&2
echo "Roll back: git checkout $before && docker compose up -d --build" >&2
echo "           (if a database change already ran, restore the backup from INSTALL.md first)" >&2
exit 1
