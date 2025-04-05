#!/bin/bash
set -e  # Exit if any command fails

echo "Setting up Conda shell..."
eval "$(conda shell.bash hook)"

echo "Activating Conda environment: portfolioenv"
conda activate portfolioenv
echo "Conda environment activated."

echo "Waiting for database to be ready..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 1
done
echo "Database is ready."

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

PORT=${PORT:-8000}  # Use Render's provided port or fallback to 8000
echo "Starting Gunicorn server on port ${PORT}..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 3 --timeout 120 Portfolio.wsgi:application
