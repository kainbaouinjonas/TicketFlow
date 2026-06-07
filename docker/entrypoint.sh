#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! nc -z ${DB_HOST:-db} ${DB_PORT:-5432}; do
  sleep 0.5
done
echo "PostgreSQL started"

echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
  sleep 0.5
done
echo "Redis started"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "$SEED_DB" = "true" ]; then
    python manage.py seed_db || true
fi

exec "$@"