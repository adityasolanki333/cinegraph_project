#!/bin/bash
set -e

PATH="$HOME/workspace/.pythonlibs/bin:$PATH"
python3 manage.py migrate --noinput
