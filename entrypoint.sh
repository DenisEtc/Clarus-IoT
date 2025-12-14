#!/bin/sh
set -e

# Запускаем миграции только для API (uvicorn).
# Для worker (python -u -m app.worker) — пропускаем.
if echo "$*" | grep -q "uvicorn"; then
  echo "[entrypoint] Running migrations..."
  i=1
  while [ $i -le 30 ]; do
    if alembic -c /app/alembic.ini upgrade head; then
      echo "[entrypoint] Migrations applied."
      break
    fi
    echo "[entrypoint] Alembic failed (attempt $i/30). Retrying in 1s..."
    i=$((i+1))
    sleep 1
  done
fi

exec "$@"
