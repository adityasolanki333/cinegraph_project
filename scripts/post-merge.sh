#!/bin/bash
set -e
npm install
python manage.py migrate --noinput
