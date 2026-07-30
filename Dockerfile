# Single lightweight stage - multi-stage isn't worth the complexity
# for this project's size.
# python:3.14-slim matches the Python version validated by CI
# (see .github/workflows/ci.yml, python-version: "3.14").
FROM python:3.14-slim

WORKDIR /app

# build-essential is here as a safety net for any dependency that
# doesn't ship a prebuilt wheel for this Python version/platform.
# Most of requirements.txt (torch, bcrypt, etc.) already has manylinux
# wheels for cp314, so this may be removable - worth revisiting once
# a real build confirms nothing actually needs it, rather than
# assuming that now.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Dependencies before app code: this layer is only invalidated (and
# only re-runs the slow pip install) when requirements.txt itself
# changes, not on every source edit.
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Explicit copy list, not `COPY . .` - keeps the image to exactly what
# the running app needs. .dockerignore backs this up as a second layer
# of defense, not the only one.
COPY alembic ./alembic
COPY alembic.ini .
COPY app ./app
COPY entrypoint.sh .
# Strip Windows CRLF line endings if present - protects against
# Windows checkouts where core.autocrlf silently reintroduces \r,
# which breaks `set -e` parsing inside the Linux container's sh.
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Non-root user - the app has no reason to run as root inside the
# container.
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Runs migrations, then starts the API - see entrypoint.sh for the
# fail-fast behavior on migration errors.
ENTRYPOINT ["sh", "/app/entrypoint.sh"]