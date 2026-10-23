#!/bin/bash
set -e

mkdir -p staticfiles

echo "=== Preparing Python 3.12 Environment ==="
if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 .venv || uv venv .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
else
    python3 -m pip install --break-system-packages -r requirements.txt || python -m pip install --break-system-packages -r requirements.txt || pip install -r requirements.txt
fi

echo "=== Collecting Static Files ==="
python manage.py collectstatic --noinput

if [ -n "$DATABASE_URL" ]; then
    echo "=== Running Database Migrations on Neon ==="
    python manage.py migrate --noinput
fi

echo "=== Build Finished Successfully ==="

