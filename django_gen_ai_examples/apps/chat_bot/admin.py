"""
Django Admin for chat_bot App.
"""

from django.contrib import admin
from django.db import models
from django.db.models import Count
from tinymce.widgets import TinyMCE

from .models import DictionaryWord, DictionaryWordMeaning, PromptTemplate


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    "PromptTemplate Model Django Admin"

    list_display = ("name", "lookup_key")
    search_fields = ("name", "lookup_key", "prompt_template")
    prepopulated_fields = {"lookup_key": ("name",)}

    formfield_overrides = {
        models.TextField: {"widget": TinyMCE(attrs={"cols": 80, "rows": 60})},
    }


class DictionaryWordMeaningInline(admin.TabularInline):
    "Inline Admin for DictionaryWordMeaning within DictionaryWord Admin"

    model = DictionaryWordMeaning
    extra = 1
    fields = ("part_of_speech", "definition")
    verbose_name = "Meaning"
    verbose_name_plural = "Meanings"


@admin.register(DictionaryWord)
class DictionaryWordAdmin(admin.ModelAdmin):
    "DictionaryWord Model Django Admin"

    list_display = ("term", "get_synonyms_count", "get_meanings_count")
    search_fields = ("term", "synonyms")
    list_filter = ("meanings__part_of_speech",)
    inlines = [DictionaryWordMeaningInline]
    ordering = ("term",)

    fieldsets = ((None, {"fields": ("term", "synonyms")}),)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("meanings").annotate(meanings_count=Count("meanings"))

    @admin.display(description="Synonyms Count", ordering="synonyms")
    def get_synonyms_count(self, obj: "DictionaryWord"):
        return len(obj.synonyms) if obj.synonyms else 0

    @admin.display(description="Meanings Count", ordering="meanings_count")
    def get_meanings_count(self, obj: "DictionaryWord"):
        return obj.meanings_count  # type: ignore -- added as annotation in get_queryset


@admin.register(DictionaryWordMeaning)
class DictionaryWordMeaningAdmin(admin.ModelAdmin):
    "DictionaryWordMeaning Model Django Admin"

    list_display = ("word", "part_of_speech", "get_short_definition")
    list_filter = ("part_of_speech",)
    search_fields = ("word__term", "definition", "part_of_speech")
    autocomplete_fields = ("word",)

    fieldsets = ((None, {"fields": ("word", "part_of_speech", "definition")}),)

    @admin.display(description="Definition")
    def get_short_definition(self, obj: "DictionaryWordMeaning"):
        return (obj.definition[:75] + "...") if len(obj.definition) > 75 else obj.definition
