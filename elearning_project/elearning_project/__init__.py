try:
    from .celery import app as celery_app
except Exception as e:  # pragma: no cover - optional dependency at runtime
    print("ERROR:", str(e))
    celery_app = None

__all__ = ("celery_app",)
