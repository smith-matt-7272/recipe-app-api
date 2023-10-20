#!/bin/sh

# If any step fails in the script, fail the whole script
set -e

# Make sure database is running first
python manage.py wait_for_db
# Collects static files and puts them in defined directory
python manage.py collectstatic --noinput
# Complete any pending migrations
python manage.py migrate
# Run the uwsgi application on socket 9000
# Run with 4 workers (if more cpus, more load, can increase)
# Set the uwsgi as the master thread of the server
# Enable threads allows multi threading
# Run the app/wsgi.py as the opening application
uwsgi --socket :9000 --workers 4 --master --enable-threads --module app.wsgi