"""
Django Admin for chat_bot App.
"""

from django.contrib import admin
from django.db import models
from tinymce.widgets import TinyMCE

from .models import PromptTemplate


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    "PromptTemplate Model Django Admin"

    list_display = ("name", "lookup_key")
    search_fields = ("name", "lookup_key", "prompt_template")
    prepopulated_fields = {"lookup_key": ("name",)}

    formfield_overrides = {
        models.TextField: {"widget": TinyMCE(attrs={"cols": 80, "rows": 60})},
    }
