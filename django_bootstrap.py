"""
This script sets up the Django environment for Airflow integration.
"""

import os
import sys

import django

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_gen_ai_examples.settings')

django.setup()
