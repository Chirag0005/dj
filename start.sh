#!/usr/bin/env bash
# Exit on error
set -o errexit

# Apply any pending database migrations automatically on startup / wake-up
echo "Applying database migrations..."
python manage.py migrate --no-input

# Start Gunicorn WSGI server
echo "Starting Gunicorn server..."
exec gunicorn resumecraft.wsgi:application
