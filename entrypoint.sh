#!/bin/sh
# Container entrypoint: migrate, then serve.
#
# set -e: exit immediately on the first failing command. This is what
# makes "the container fails clearly if migration or startup fails"
# true - a failed `alembic upgrade head` stops the script right here
# with a non-zero exit, instead of uvicorn starting against a
# half-migrated database.
set -e

echo "Running database migrations..."
python -m alembic upgrade head
echo "Migrations complete. Starting FastAPI server..."

# exec replaces this shell process with uvicorn instead of running it
# as a child. uvicorn becomes PID 1 and receives SIGTERM directly on
# `docker stop`, for a clean shutdown - without exec, the shell stays
# PID 1, swallows the signal, and Docker has to wait out the full stop
# timeout before force-killing everything.
#
# --workers 1: the project uses SQLite, a single-writer file database.
# More workers would mean multiple processes contending for one file -
# not a supported configuration here.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --access-log