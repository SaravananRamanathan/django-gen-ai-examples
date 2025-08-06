"""
Django Admin for chat_bot App.
"""

from typing import TYPE_CHECKING

from django.contrib import admin
from django.db import models
from django.db.models import Count
from tinymce.widgets import TinyMCE

from .models import (
    CalendarEvent,
    CalendarEventAttachment,
    CalendarRAGQuery,
    DictionaryWord,
    DictionaryWordMeaning,
    PromptTemplate,
)

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


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


class CalendarEventAttachmentInline(admin.TabularInline):
    """Inline admin for calendar event attachments."""

    model = CalendarEventAttachment
    extra = 0
    fields = ("file_name", "mime_type", "processing_status", "extraction_method", "processing_error")
    readonly_fields = ("processing_status", "extraction_method", "processing_error")
    verbose_name = "Attachment"
    verbose_name_plural = "Attachments"


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    """Admin interface for Calendar Events."""

    list_display = (
        "summary",
        "user",
        "start_datetime",
        "end_datetime",
        "has_embedding",
        "last_synced",
        "get_attachments_count",
    )
    list_filter = ("user", "start_datetime", "last_synced", "status", "all_day")
    search_fields = ("summary", "description", "location", "organizer_email", "user__email")
    readonly_fields = (
        "google_event_id",
        "raw_google_data",
        "combined_text",
        "content_embedding",
        "last_synced",
        "created_at",
        "updated_at",
    )
    inlines = [CalendarEventAttachmentInline]

    fieldsets = (
        ("Basic Information", {"fields": ("user", "google_event_id", "calendar_id", "summary", "description")}),
        ("Time & Location", {"fields": ("start_datetime", "end_datetime", "all_day", "timezone", "location")}),
        ("Participants", {"fields": ("organizer_email", "attendees")}),
        ("Meeting Details", {"fields": ("meeting_url", "recurrence_rule", "status")}),
        ("RAG Processing", {"fields": ("combined_text", "content_embedding", "last_synced"), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("raw_google_data", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("user").prefetch_related("attachments")

    @admin.display(description="Has Embedding", boolean=True)
    def has_embedding(self, obj: "CalendarEvent"):
        return obj.content_embedding is not None

    @admin.display(description="Attachments")
    def get_attachments_count(self, obj: "CalendarEvent"):
        return obj.attachments.count()

    actions = ["regenerate_embeddings", "reprocess_events"]

    def regenerate_embeddings(self, request, queryset: "QuerySet[CalendarEvent]"):
        """Admin action to regenerate embeddings for selected events."""
        from django.utils import timezone

        from chat_bot.services.google_embedding_service import google_embedding_service

        updated = 0
        for event in queryset:
            try:
                event.combined_text = event.generate_combined_text()
                embedding = google_embedding_service.generate_embedding(event.combined_text)
                if embedding:
                    event.content_embedding = embedding
                    event.last_synced = timezone.now()
                    event.save(update_fields=["content_embedding", "last_synced", "combined_text"])
                    updated += 1
            except Exception as e:
                self.message_user(request, f"Error processing {event.summary}: {e}", level="ERROR")

        self.message_user(request, f"Successfully regenerated embeddings for {updated} events.")

    regenerate_embeddings.short_description = "Regenerate embeddings for selected events"

    def reprocess_events(self, request, queryset: "QuerySet[CalendarEvent]"):
        """Admin action to fully reprocess selected events from their raw Google data."""
        from django.utils import timezone

        from chat_bot.services.google_embedding_service import google_embedding_service

        updated = 0
        for event in queryset:
            try:
                # Reprocess the event from raw Google data if available
                if event.raw_google_data:
                    # Extract event details from raw data
                    summary = event.raw_google_data.get("summary", "")
                    description = event.raw_google_data.get("description", "")
                    location = event.raw_google_data.get("location", "")

                    # Update event fields
                    event.summary = summary
                    event.description = description
                    event.location = location

                    # Extract organizer and attendees
                    organizer_data = event.raw_google_data.get("organizer", {})
                    event.organizer_email = organizer_data.get("email", "")

                    attendees_data = event.raw_google_data.get("attendees", [])
                    event.attendees = [
                        {
                            "email": attendee.get("email"),
                            "status": attendee.get("responseStatus"),
                            "optional": attendee.get("optional", False),
                        }
                        for attendee in attendees_data
                    ]

                    # Extract meeting URL
                    from chat_bot.tasks.google_calendar_tasks import _extract_meeting_url

                    event.meeting_url = _extract_meeting_url(event.raw_google_data)

                    # Update status
                    event.status = event.raw_google_data.get("status", "confirmed")

                # Regenerate combined text and embedding
                event.combined_text = event.generate_combined_text()
                embedding = google_embedding_service.generate_embedding(event.combined_text)
                if embedding:
                    event.content_embedding = embedding

                event.last_synced = timezone.now()
                event.save()
                updated += 1

            except Exception as e:
                self.message_user(request, f"Error reprocessing {event.summary}: {e}", level="ERROR")

        self.message_user(request, f"Successfully reprocessed {updated} events.")

    reprocess_events.short_description = "Reprocess events from raw Google data"


@admin.register(CalendarEventAttachment)
class CalendarEventAttachmentAdmin(admin.ModelAdmin):
    """Admin interface for Calendar Event Attachments."""

    list_display = (
        "file_name",
        "event",
        "mime_type",
        "processing_status",
        "extraction_method",
        "has_embedding",
        "processed_at",
    )
    list_filter = ("processing_status", "extraction_method", "mime_type", "processed_at")
    search_fields = ("file_name", "event__summary", "event__user__email", "mime_type")
    readonly_fields = (
        "file_id",
        "extraction_method",
        "processing_status",
        "processing_error",
        "processed_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Basic Information", {"fields": ("event", "file_name", "mime_type", "file_id")}),
        ("File Details", {"fields": ("file_url", "icon_link", "file_size")}),
        ("Processing", {"fields": ("processing_status", "extraction_method", "processing_error", "processed_at")}),
        ("Content", {"fields": ("processed_content",), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Has Embedding", boolean=True)
    def has_embedding(self, obj: "CalendarEventAttachment"):
        return obj.content_embedding is not None

    actions = ["reprocess_attachments"]

    def reprocess_attachments(self, request, queryset: "QuerySet[CalendarEventAttachment]"):
        """Admin action to reprocess selected attachments."""
        from allauth.socialaccount.models import SocialToken
        from django.utils import timezone

        from chat_bot.services.attachment_service import attachment_service

        processed = 0
        for attachment in queryset:
            try:
                # Get user's social token
                social_token = SocialToken.objects.get(account__user=attachment.event.user, account__provider="google")

                # Recreate attachment data structure
                attachment_data = {
                    "fileId": attachment.file_id,
                    "title": attachment.file_name,
                    "mimeType": attachment.mime_type,
                    "fileUrl": attachment.file_url,
                    "iconLink": attachment.icon_link,
                }

                extracted_text, extraction_method = attachment_service.process_attachment(
                    attachment_data, social_token.token, social_token.token_secret
                )

                attachment.processed_content = extracted_text or ""
                attachment.extraction_method = extraction_method
                attachment.processing_status = "completed"
                attachment.processing_error = ""
                attachment.processed_at = timezone.now()

                # Generate embedding for attachment content
                if extracted_text:
                    try:
                        from chat_bot.services.google_embedding_service import google_embedding_service

                        embedding = google_embedding_service.generate_embedding(extracted_text)
                        if embedding:
                            attachment.content_embedding = embedding
                    except Exception as e:
                        self.message_user(
                            request,
                            f"Warning: Could not generate embedding for {attachment.file_name}: {e}",
                            level="WARNING",
                        )

                attachment.save()

                processed += 1

            except Exception as e:
                attachment.processing_status = "failed"
                attachment.processing_error = str(e)
                attachment.save()
                self.message_user(request, f"Error processing {attachment.file_name}: {e}", level="ERROR")

        self.message_user(request, f"Successfully reprocessed {processed} attachments.")

    reprocess_attachments.short_description = "Reprocess selected attachments"


@admin.register(CalendarRAGQuery)
class CalendarRAGQueryAdmin(admin.ModelAdmin):
    """Admin interface for RAG Queries."""

    list_display = ("get_short_query", "user", "events_found", "model_used", "response_time_ms", "created_at")
    list_filter = ("user", "model_used", "created_at", "events_found")
    search_fields = ("query_text", "generated_response", "user__email")
    readonly_fields = ("query_embedding", "similarity_scores", "response_time_ms", "created_at")
    filter_horizontal = ("retrieved_events",)

    fieldsets = (
        ("Query Information", {"fields": ("user", "query_text", "generated_response")}),
        ("Results", {"fields": ("retrieved_events", "events_found", "similarity_scores")}),
        ("Metadata", {"fields": ("model_used", "response_time_ms", "created_at"), "classes": ("collapse",)}),
        ("Technical", {"fields": ("query_embedding",), "classes": ("collapse",)}),
    )

    @admin.display(description="Query")
    def get_short_query(self, obj: "CalendarRAGQuery"):
        return (obj.query_text[:50] + "...") if len(obj.query_text) > 50 else obj.query_text
