# pylint: skip-file

from .base import *

ALLOWED_HOSTS = ["SaravananRamanathan.pythonanywhere.com"]

# default static files settings for PythonAnywhere.
# see https://help.pythonanywhere.com/pages/DjangoStaticFiles for more info
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
MEDIA_ROOT = '/home/SaravananRamanathan/django-gen-ai-examples/django_gen_ai_examples/media'
MEDIA_URL = '/media/'
STATIC_ROOT = '/home/SaravananRamanathan/django-gen-ai-examples/django_gen_ai_examples/static'
STATIC_URL = '/static/'
