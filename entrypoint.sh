#!/bin/sh
# Runs every time the web container starts. Safe to run repeatedly.
set -e

echo "[entrypoint] waiting for the database..."
python - <<'PY'
import os, sys, time
import dj_database_url
import psycopg

cfg = dj_database_url.parse(os.environ["DATABASE_URL"]) if os.environ.get("DATABASE_URL", "").startswith("postgres") else None
if cfg is None:
    sys.exit(0)  # sqlite: nothing to wait for
for attempt in range(60):
    try:
        psycopg.connect(
            dbname=cfg["NAME"], user=cfg["USER"], password=cfg["PASSWORD"],
            host=cfg["HOST"], port=cfg["PORT"] or 5432, connect_timeout=3,
        ).close()
        print("[entrypoint] database is ready")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] database not ready yet ({exc.__class__.__name__}), retrying...")
        time.sleep(2)
else:
    sys.exit("[entrypoint] database never became ready")
PY

echo "[entrypoint] applying migrations..."
python manage.py migrate --noinput

echo "[entrypoint] preparing the shared cache table and clearing old sessions..."
python manage.py createcachetable
python manage.py clearsessions

echo "[entrypoint] collecting static files..."
python manage.py collectstatic --noinput --verbosity 0

echo "[entrypoint] making sure the admin account exists..."
python manage.py ensure_admin

if [ "${SEED_CONTENT:-1}" = "1" ]; then
    echo "[entrypoint] loading sample questions if the library is empty..."
    python manage.py seed_content --only-if-empty
fi

echo "[entrypoint] starting: $*"
exec "$@"
