from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
]
CORS_ALLOW_CREDENTIALS = True  # needed so the httpOnly refresh-token cookie is sent/received

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
