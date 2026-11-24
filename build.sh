#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run database migrations (SQLite or PostgreSQL)
python manage.py migrate --no-input

# Collect static files for production delivery
python manage.py collectstatic --no-input
