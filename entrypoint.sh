#!/bin/bash
set -e  # Exit if any command fails

echo "Setting up Conda shell..."
eval "$(conda shell.bash hook)"

echo "Activating Conda environment: portfolioenv"
conda activate portfolioenv
echo "Conda environment activated."

echo "Waiting for database to be ready..."
python <<EOF
import socket
import time
import os

host = os.getenv("POSTGRES_HOST", "localhost")
port = int(os.getenv("POSTGRES_PORT", 5432))

while True:
    try:
        with socket.create_connection((host, port), timeout=5):
            print("Database is ready.")
            break
    except (socket.timeout, ConnectionRefusedError):
        print("Waiting for database...")
        time.sleep(1)
EOF

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

PORT=${PORT:-8000}  # Use Render's provided port or fallback to 8000
echo "Starting Gunicorn server on port ${PORT}..."
exec gunicorn --bind 0.0.0.0:${PORT} --workers=1 --threads=2 --timeout 120 Portfolio.wsgi:application
