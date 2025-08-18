"""
All models realted to chat_bot App.
"""

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import models
from pgvector.django import VectorField

User = get_user_model()


class PromptTemplate(models.Model):
    """
    Used to save Prompt Templates.
    """

    name = models.CharField(max_length=255)
    lookup_key = models.SlugField(
        max_length=100,
        unique=True,
        help_text="A unique, code-friendly key to look up this prompt (e.g., 'single-prompt').",
    )
    prompt_template = models.TextField(
        help_text=(
            "The prompt content. "
            "Use {{ <var-name> }} for Django context. "
            "Use { <var-name> } for lang chain context."
        )
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.lookup_key}: {self.name}"

    class Meta:
        "Meta overrides for PromptTemplate"

        verbose_name = "Prompt Template"
        verbose_name_plural = "Prompt Templates"


class DictionaryWord(models.Model):
    """
    DictionaryWord represents a single word in english dictionary.
    """

    term = models.CharField(max_length=255, primary_key=True)
    synonyms = models.JSONField(default=list, blank=True, help_text="A list of synonym strings(words).")

    # Vector Field.
    # The more the dimensions, the more accurate the embedding (?) , more features (?)
    # for all-MiniLM-L6-v2 model, word_embedding_dimension is 384, so we can't go beyond that (?)
    embedding = VectorField(dimensions=384, null=True, blank=True)
    # TODO: create embedding when new DictionaryWord is created.

    if TYPE_CHECKING:
        meanings: models.QuerySet["DictionaryWordMeaning"]

    def __str__(self):
        return self.term

    class Meta:
        ordering = ["term"]
        verbose_name = "Dictionary Word"
        verbose_name_plural = "Dictionary Words"


class DictionaryWordMeaning(models.Model):
    """
    Meaning of a word in the english dictionary.
    A "word" can have multiple meanings.
    """

    word = models.ForeignKey(DictionaryWord, on_delete=models.CASCADE, related_name="meanings")
    part_of_speech = models.CharField(max_length=50, blank=True, null=True)  # e.g., noun, verb, adjective
    definition = models.TextField()  # meaning of the word

    def __str__(self):
        return f"{self.word.term} ({self.part_of_speech}): {self.definition[:50]}..."

    class Meta:
        verbose_name = "Dictionary Meaning"
        verbose_name_plural = "Dictionary Meanings"


class CalendarEvent(models.Model):
    """
    Store Google Calendar events with vector embeddings for RAG.
    """

    # Google Calendar fields
    google_event_id = models.CharField(max_length=255, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="calendar_events")
    calendar_id = models.CharField(max_length=255, default="primary")

    # Event details
    summary = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=500, blank=True)

    # Time fields
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    timezone = models.CharField(max_length=100, default="UTC")

    # Event metadata
    creator_email = models.EmailField(blank=True)
    organizer_email = models.EmailField(blank=True)
    attendees = models.JSONField(default=list, blank=True)  # List of attendee emails and statuses

    # Meeting/event metadata
    meeting_url = models.URLField(blank=True, null=True)
    recurrence_rule = models.TextField(
        blank=True, help_text="RRULE for recurring events"
    )  # TODO: fix, seems always empty.
    recurrence_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default="confirmed")  # e.g. confirmed, tentative, cancelled

    # RAG fields
    combined_text = models.TextField(blank=True, help_text="Combined text for embedding generation")
    content_embedding = VectorField(dimensions=3072, null=True, blank=True)  # model: Google gemini-embedding-001

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced = models.DateTimeField(auto_now=True)

    # Raw Google Calendar API response
    raw_google_data = models.JSONField(default=dict, blank=True)

    if TYPE_CHECKING:
        attachments: "models.QuerySet[CalendarEventAttachment]"

    class Meta:
        ordering = ["-start_datetime"]
        verbose_name = "Calendar Event"
        verbose_name_plural = "Calendar Events"
        indexes = [
            models.Index(fields=["user", "start_datetime"]),
            models.Index(fields=["google_event_id"]),
        ]

    def __str__(self):
        return f"{self.summary} - {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"

    def generate_combined_text(self) -> str:
        """
        Generate combined text for embedding.
        Later this will be used to generate the content embedding.
        we will pass this combined text to the any of the cloud embedding APIs.
        """
        parts = []

        if self.summary:
            parts.append(f"Title: {self.summary}")

        if self.description:
            parts.append(f"Description: {self.description}")

        if self.location:
            parts.append(f"Location: {self.location}")

        if self.organizer_email:
            parts.append(f"Organizer: {self.organizer_email}")

        if self.attendees:
            attendee_emails = [att.get("email", "") for att in self.attendees if att.get("email")]
            if attendee_emails:
                parts.append(f"Attendees: {', '.join(attendee_emails)}")

        parts.append(f"Start: {self.start_datetime}")
        parts.append(f"End: {self.end_datetime}")

        # Include attachment content
        attachment_content = []
        for attachment in self.attachments.all():
            if attachment.processed_content:
                # Limit to few hundred characters if running into rate limits
                # to avoid too long text for embedding as needed
                attachment_content.append(f"Attachment ({attachment.file_name}): {attachment.processed_content[:5000]}")

        if attachment_content:
            parts.extend(attachment_content)

        return "\n".join(parts)

    def update_embedding(self):
        """Update the content embedding using Google's embedding service."""
        from chat_bot.services.google_embedding_service import google_embedding_service

        self.combined_text = self.generate_combined_text()
        self.content_embedding = google_embedding_service.generate_embedding(self.combined_text)

    def get_admin_url(self):
        """Get local admin URL for this calendar event."""
        return f"http://localhost:8220/admin/chat_bot/calendarevent/{self.id}/change/"


class CalendarEventAttachment(models.Model):
    """
    Store calendar event attachments and their processed content.
    """

    event = models.ForeignKey(CalendarEvent, on_delete=models.CASCADE, related_name="attachments")

    # Google Drive/attachment fields
    file_id = models.CharField(max_length=255, unique=True, db_index=True)
    file_name = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100)
    file_url = models.URLField()
    file_size = models.BigIntegerField(null=True, blank=True)
    icon_link = models.URLField(blank=True)

    # Processed content
    raw_content = models.TextField(blank=True, help_text="Raw extracted text content")
    processed_content = models.TextField(blank=True, help_text="Cleaned and processed content")
    content_embedding = VectorField(dimensions=3072, null=True, blank=True)  # model: Google gemini-embedding-001
    extraction_method = models.CharField(
        max_length=50, blank=True, help_text="Method used to extract text (pdf, docx, etc.)"
    )

    # Processing metadata
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("unsupported", "Unsupported Format"),
        ],
        default="pending",
    )
    processing_error = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Calendar Event Attachment"
        verbose_name_plural = "Calendar Event Attachments"
        indexes = [
            models.Index(fields=["event", "processing_status"]),
            models.Index(fields=["file_id"]),
        ]

    def __str__(self):
        return f"{self.file_name} ({self.event.summary})"

    def update_embedding(self):
        """Update the content embedding using Google's embedding service."""
        if not self.processed_content:
            return

        from chat_bot.services.google_embedding_service import google_embedding_service

        self.content_embedding = google_embedding_service.generate_embedding(self.processed_content)


class CalendarRAGQuery(models.Model):
    """
    Store user queries for testing.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rag_queries")

    # Query details
    query_text = models.TextField()
    query_embedding = VectorField(dimensions=3072, null=True, blank=True)  # model: Google gemini-embedding-001

    # Search parameters
    include_attachments = models.BooleanField(default=True)
    date_range_days = models.IntegerField(null=True, blank=True)

    # Results
    events_found = models.IntegerField(default=0)
    similarity_threshold = models.FloatField(default=0.7)
    retrieved_events = models.ManyToManyField(CalendarEvent, blank=True, related_name="rag_queries")
    similarity_scores = models.JSONField(default=dict, blank=True, help_text="Event IDs mapped to similarity scores")

    # Response
    generated_response = models.TextField(blank=True)
    model_used = models.CharField(max_length=100, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)

    # User feedback
    user_rating = models.IntegerField(
        null=True,
        blank=True,
        choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
        help_text="User rating from 1-5",
    )
    user_feedback = models.TextField(blank=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "RAG Query"
        verbose_name_plural = "RAG Queries"
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email}: {self.query_text[:50]}..."

    def update_query_embedding(self):
        """Update the query embedding using Google's embedding service."""
        from chat_bot.services.google_embedding_service import google_embedding_service

        self.query_embedding = google_embedding_service.generate_embedding(self.query_text)
