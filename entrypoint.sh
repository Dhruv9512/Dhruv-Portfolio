#!/bin/bash
set -e  # Exit immediately if any command fails

echo "Activating Conda environment..."
conda run --no-capture-output -n portfolioenv python -c "print('Conda environment activated.')"

echo "Waiting for database to be ready..."
while ! conda run --no-capture-output -n portfolioenv python manage.py showmigrations &>/dev/null; do
    echo "Database not ready, waiting..."
    sleep 2
done
echo "Database is ready."

echo "Applying database migrations..."
conda run --no-capture-output -n portfolioenv python manage.py migrate --noinput

echo "Collecting static files..."
conda run --no-capture-output -n portfolioenv python manage.py collectstatic --noinput

PORT=${PORT:-8000}  # Default to 8000 if PORT is not set
echo "Starting Gunicorn server on port ${PORT}..."
exec conda run --no-capture-output -n portfolioenv gunicorn Portfolio.wsgi:application --bind 0.0.0.0:${PORT} --workers 3
