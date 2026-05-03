release: python manage.py migrate --no-input
web: gunicorn movieflix.wsgi:application --workers 1
