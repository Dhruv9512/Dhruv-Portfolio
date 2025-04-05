#!/bin/bash
set -e  # Exit if any command fails

echo "Setting up Conda shell..."
eval "$(conda shell.bash hook)"

echo "Activating Conda environment: portfolioenv"
conda activate portfolioenv
echo "Conda environment activated."

echo "Waiting for database to be ready..."
while ! python manage.py showmigrations &>/dev/null; do
    echo "Database not ready, waiting..."
    sleep 2
done
echo "Database is ready."

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

PORT=${PORT:-8000}  # Use Render's provided port or fallback to 8000
echo "Starting Gunicorn server on port ${PORT}..."
exec gunicorn Portfolio.wsgi:application --bind 0.0.0.0:${PORT} --workers 3
