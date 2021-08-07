#!/usr/bin/env bash

set -e
cd /app
gunicorn wsgi:app --bind 0.0.0.0:8080 --log-level=info --workers=2
