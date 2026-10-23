#!/bin/bash

echo "=== Installing Dependencies ==="
if command -v uv >/dev/null 2>&1; then
    uv pip install --system -r requirements.txt
else
    python3 -m pip install --break-system-packages -r requirements.txt || python -m pip install --break-system-packages -r requirements.txt || pip install -r requirements.txt
fi

echo "=== Collecting Static Files ==="
python3 manage.py collectstatic --noinput || python manage.py collectstatic --noinput

if [ -n "$DATABASE_URL" ]; then
    echo "=== Running Database Migrations on Neon ==="
    python3 manage.py migrate --noinput || python manage.py migrate --noinput
fi

echo "=== Build Finished Successfully ==="

