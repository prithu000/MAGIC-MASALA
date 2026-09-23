web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
worker: celery -A config.celery_app worker --loglevel=info --concurrency 2
beat: celery -A config.celery_app beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
