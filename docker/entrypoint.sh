#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d $POSTGRES_DB -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is up - running migrations..."
alembic upgrade head

echo "Starting FastAPI application..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 "$@"
