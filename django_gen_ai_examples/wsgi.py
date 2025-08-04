"""
WSGI config for django_gen_ai_examples project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)

env = os.getenv("ENV")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"django_gen_ai_examples.settings.{env}")

application = get_wsgi_application()
