#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files (Database-free: no migrations needed!)
python manage.py collectstatic --no-input
