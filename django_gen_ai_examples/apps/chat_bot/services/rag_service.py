"""
Calendar RAG service for querying calendar events using vector similarity.
"""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from pgvector.django import CosineDistance

from chat_bot.models import CalendarEvent, CalendarEventAttachment, CalendarRAGQuery
from chat_bot.services.google_embedding_service import google_embedding_service

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    from django.db.models.query import QuerySet

User = get_user_model()
logger = logging.getLogger(__name__)


class CalendarRAGService:
    """
    Service for performing RAG queries on calendar events.
    """

    def __init__(self):
        self.default_similarity_threshold = 0.5
        self.max_results = 50

    def query_calendar_events(
        self,
        user_email: str,
        query_text: str,
        include_attachments: bool = True,
        date_range_days: Optional[int] = 90,
        similarity_threshold: Optional[float] = None,
        max_results: Optional[int] = None,
    ) -> Tuple[List[CalendarEvent], List[float], Optional[CalendarRAGQuery]]:
        """
        Query calendar events using vector similarity search.

        Args:
            user_email: Email of the user
            query_text: Natural language query
            include_attachments: Whether to include attachment content in search
            date_range_days: Limit search to events within N days (None for all events)
            similarity_threshold: Minimum similarity score (0-1)
            max_results: Maximum number of results to return

        Returns:
            Tuple of (events, similarity_scores, rag_query_record)
        """
        # Get user
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            logger.error(f"User with email {user_email} not found")
            return [], [], None

        # Set defaults
        if similarity_threshold is None:
            similarity_threshold = self.default_similarity_threshold
        if max_results is None:
            max_results = self.max_results

        # Create RAG query record
        rag_query = CalendarRAGQuery.objects.create(
            user=user,
            query_text=query_text,
            include_attachments=include_attachments,
            date_range_days=date_range_days,
            similarity_threshold=similarity_threshold,
        )

        # Generate query embedding
        query_embedding = google_embedding_service.generate_query_embedding(query_text)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            rag_query.events_found = 0
            rag_query.save()
            return [], [], rag_query

        rag_query.query_embedding = query_embedding
        rag_query.save()

        # Build base queryset
        queryset = (
            CalendarEvent.objects.filter(user=user, content_embedding__isnull=False)
            .select_related("user")
            .prefetch_related("attachments")
        )

        # Apply date range filter
        if date_range_days:
            cutoff_date = timezone.now() - timedelta(days=date_range_days)
            queryset = queryset.filter(start_datetime__gte=cutoff_date)

        # Perform vector similarity search
        events_with_scores = (
            queryset.annotate(similarity=1 - CosineDistance("content_embedding", query_embedding))
            .filter(similarity__gte=similarity_threshold)
            .order_by("-similarity")[:max_results]
        )

        # Extract events and scores
        events: List[CalendarEvent] = []
        scores: List[float] = []

        for event in events_with_scores:
            events.append(event)
            # Use getattr to access dynamically added similarity attribute
            scores.append(float(getattr(event, "similarity", 0.0)))

        # If including attachments, also search attachment content
        if include_attachments:
            attachment_events, attachment_scores = self._search_attachments(
                user, query_embedding, similarity_threshold, max_results, date_range_days
            )

            # Merge and deduplicate results
            events, scores = self._merge_results(events, scores, attachment_events, attachment_scores)

        # Update RAG query record
        rag_query.events_found = len(events)
        rag_query.save()

        logger.info(
            f"Found {len(events)} events for query '{query_text[:50]}...' "
            f"(threshold: {similarity_threshold}, max_results: {max_results})"
        )

        return events, scores, rag_query

    def _search_attachments(
        self,
        user: "AbstractUser",
        query_embedding: List[float],
        similarity_threshold: float,
        max_results: int,
        date_range_days: Optional[int],
    ) -> Tuple[List[CalendarEvent], List[float]]:
        """Search calendar event attachments for relevant content."""

        # Build attachment queryset
        attachment_queryset = CalendarEventAttachment.objects.filter(
            event__user=user, content_embedding__isnull=False, processing_status="completed"
        ).select_related("event__user")

        # Apply date range filter
        if date_range_days:
            cutoff_date = timezone.now() - timedelta(days=date_range_days)
            attachment_queryset = attachment_queryset.filter(event__start_datetime__gte=cutoff_date)

        # Perform vector similarity search on attachments
        attachments_with_scores = (
            attachment_queryset.annotate(similarity=1 - CosineDistance("content_embedding", query_embedding))
            .filter(similarity__gte=similarity_threshold)
            .order_by("-similarity")[:max_results]
        )

        # Extract unique events and their highest scores
        event_scores: Dict[int, Tuple[CalendarEvent, float]] = {}
        for attachment in attachments_with_scores:
            event = attachment.event
            # Use getattr to access dynamically added similarity attribute
            score = float(getattr(attachment, "similarity", 0.0))

            if event.pk not in event_scores or score > event_scores[event.pk][1]:
                event_scores[event.pk] = (event, score)

        # Sort by score
        sorted_events = sorted(event_scores.values(), key=lambda x: x[1], reverse=True)

        events: List[CalendarEvent] = [item[0] for item in sorted_events]
        scores: List[float] = [item[1] for item in sorted_events]

        return events, scores

    def _merge_results(
        self, events1: List[CalendarEvent], scores1: List[float], events2: List[CalendarEvent], scores2: List[float]
    ) -> Tuple[List[CalendarEvent], List[float]]:
        """Merge and deduplicate two sets of results."""

        # Create combined results with event ID as key
        combined: Dict[int, Tuple[CalendarEvent, float]] = {}

        # Add first set
        for event, score in zip(events1, scores1):
            combined[event.pk] = (event, score)

        # Add second set (higher scores will override)
        for event, score in zip(events2, scores2):
            if event.pk not in combined or score > combined[event.pk][1]:
                combined[event.pk] = (event, score)

        # Sort by score
        sorted_results = sorted(combined.values(), key=lambda x: x[1], reverse=True)

        events: List[CalendarEvent] = [item[0] for item in sorted_results]
        scores: List[float] = [item[1] for item in sorted_results]

        return events, scores

    def get_context_for_llm(self, events: List[CalendarEvent], scores: List[float]) -> str:
        """Format calendar events as context for LLM."""

        if not events:
            return "No relevant calendar events found."

        context_parts: List[str] = []

        for i, (event, score) in enumerate(zip(events, scores), 1):
            event_text: List[str] = [
                f"Event {i} (Relevance: {score:.2f}):",
                f"Title: {event.summary or 'No title'}",
                f"Date & Time: {event.start_datetime.strftime('%Y-%m-%d %H:%M')} - {event.end_datetime.strftime('%Y-%m-%d %H:%M')}",
            ]

            if event.description:
                event_text.append(f"Description: {event.description}")

            if event.location:
                event_text.append(f"Location: {event.location}")

            if event.attendees:
                attendee_emails = [att.get("email", "") for att in event.attendees if att.get("email")]
                if attendee_emails:
                    event_text.append(f"Attendees: {', '.join(attendee_emails)}")

            # Include attachment content
            attachments = event.attachments.filter(processing_status="completed")
            if attachments.exists():
                event_text.append("Attachments:")
                for attachment in attachments:
                    if attachment.processed_content:
                        # Truncate long content
                        content = attachment.processed_content[:300]
                        if len(attachment.processed_content) > 300:
                            content += "..."
                        event_text.append(f"  - {attachment.file_name}: {content}")

            context_parts.append("\n".join(event_text))

        return "\n\n---\n\n".join(context_parts)

    def get_user_calendar_summary(self, user_email: str, days_ahead: int = 7) -> Dict[str, Any]:
        """Get a summary of upcoming events for a user."""

        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return {"error": f"User with email {user_email} not found"}

        # Get upcoming events
        start_date = timezone.now()
        end_date = start_date + timedelta(days=days_ahead)

        if days_ahead == 0:
            q_filter = Q(user=user, start_datetime__date=start_date.date())
        else:
            q_filter = Q(user=user, start_datetime__gte=start_date, start_datetime__lte=end_date)

        events = CalendarEvent.objects.filter(q_filter).order_by("start_datetime")

        summary: Dict[str, Any] = {
            "user_email": user_email,
            "period": f"{days_ahead} days",
            "total_events": events.count(),
            "events": [],
        }

        for event in events[:20]:
            summary["events"].append(
                {
                    "title": event.summary,
                    "start": event.start_datetime.isoformat(),
                    "end": event.end_datetime.isoformat(),
                    "location": event.location,
                    "has_attachments": event.attachments.exists(),
                }
            )

        return summary


# import calendar_rag_service to use in other modules.
calendar_rag_service = CalendarRAGService()
