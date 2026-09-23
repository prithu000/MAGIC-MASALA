"""config/__init__.py — make config a package and set default Celery app."""
from .celery_app import app as celery_app

__all__ = ("celery_app",)
