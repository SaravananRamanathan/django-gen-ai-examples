"""
All tasks related to Google Calendar integration.
"""

import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from allauth.socialaccount.models import SocialToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from googleapiclient.discovery import build

from chat_bot.const import GoogleOAuth2
from chat_bot.models import CalendarEvent, CalendarEventAttachment, CalendarRAGQuery
from chat_bot.services.attachment_service import attachment_service
from chat_bot.services.google_embedding_service import google_embedding_service

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource

logger = logging.getLogger(__name__)


def get_google_authenticated_user_emails(chunk_size: int = 1) -> List[str]:
    """
    Get email addresses of users with Google accounts.

    Args:
        chunk_size: Number of emails to return in each chunk (not implemented yet).

    Returns:
        A list of email addresses: ["email1", "email2", ...]
    """
    logger.info("Finding all users with linked Google accounts...")
    User = get_user_model()
    emails = User.objects.filter(socialaccount__provider="google").values_list("email", flat=True)
    logger.info("Total emails found: %s", len(emails))
    return list(emails)
    # TODO - handle chunking logic if needed.
    # return [
    #     tuple(emails[i : i + chunk_size])
    #     for i in range(0, len(emails), chunk_size)
    # ]


def get_upcoming_events(email: str, today_only: bool = True, max_results: int = 100) -> List[Any]:
    """
    Fetch upcoming calendar events for a specific user.

    Args:
        email: The email address of the user.
        today_only: If True: fetch events only for today. else: fetch all upcoming events.
        max_results: max num of events to return (ignored if today_only=True).

    Returns:
        A list of calendar events.
    """
    UserModel = get_user_model()
    try:
        user = UserModel.objects.get(email=email)
    except UserModel.DoesNotExist:
        logger.error("User with email %s does not exist.", email)
        return []

    logger.info(
        "Fetching calendar events for user: %s, email: %s, today_only: %s, max_results: %s",
        user,
        email,
        today_only,
        max_results,
    )

    try:
        social_token = SocialToken.objects.get(account__user=user, account__provider="google")
    except SocialToken.DoesNotExist:
        logger.error("No Google social token found for user %s.", user)
        return []

    service: "Resource" = build(
        "calendar",
        "v3",
        credentials=GoogleOAuth2.get_credentials(token=social_token.token, refresh_token=social_token.token_secret),
    )

    now = timezone.now()
    query_params = {
        "calendarId": "primary",
        "timeMin": now.isoformat(),
        "singleEvents": True,
        "orderBy": "startTime",
    }

    if today_only:
        query_params["timeMax"] = now.replace(
            hour=23,
            minute=59,
            second=59,
        ).isoformat()
    else:
        query_params["maxResults"] = max_results

    events_result = service.events().list(**query_params).execute()

    event_items = events_result.get("items", [])

    if not event_items:
        logger.warning("No upcoming events found for %s.", email)
        return []

    # NOTE: logging to test for now.
    for event_item in event_items:
        logger.info("Event: %s", event_item)
        logger.info("Event summary: %s", event_item.get("summary", "No summary"))

    return event_items


def process_calendar_events_for_rag(email: str, days_back: int = 30, days_forward: int = 90) -> dict:
    """
    Process calendar events for RAG by storing them in database with embeddings.

    Args:
        email: User email address
        days_back: Number of days to look back for events
        days_forward: Number of days to look forward for events

    Returns:
        Dictionary with processing results
    """
    UserModel = get_user_model()
    try:
        user = UserModel.objects.get(email=email)
    except UserModel.DoesNotExist:
        logger.error("User with email %s does not exist.", email)
        return {"error": "User not found", "processed": 0, "errors": 0}

    try:
        social_token = SocialToken.objects.get(account__user=user, account__provider="google")
    except SocialToken.DoesNotExist:
        # saravanan.ramanathan@kellton.com
        logger.error("No Google social token found for user %s.", user)
        return {"error": "No social token", "processed": 0, "errors": 0}

    logger.info(f"Processing calendar events for RAG -test : {email}")

    # Build Google Calendar service
    service: "Resource" = build(
        "calendar",
        "v3",
        credentials=GoogleOAuth2.get_credentials(token=social_token.token, refresh_token=social_token.token_secret),
    )

    # Set time range
    now = timezone.now()
    time_min = (now - timezone.timedelta(days=days_back)).isoformat()
    time_max = (now + timezone.timedelta(days=days_forward)).isoformat()

    # Fetch events
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            maxResults=1000,  # Increased limit for bulk processing
        )
        .execute()
    )

    events: List[Any] = events_result.get("items", [])
    processed_count = 0
    error_count = 0

    logger.info(f"Found {len(events)} events to process for {email}")

    for event_data in events:
        try:
            result = _process_single_event(user, event_data, social_token)
            if result:
                processed_count += 1
            else:
                error_count += 1
        except Exception as e:
            logger.error(f"Error processing event {event_data.get('id')}: {e}")
            error_count += 1

    return {"user_email": email, "processed": processed_count, "errors": error_count, "total_events": len(events)}


def _process_single_event(user, event_data: Any, social_token: SocialToken) -> bool:
    """
    Process a single calendar event and store it with embeddings.

    Args:
        user: Django user object
        event_data: Raw event data from Google Calendar API
        social_token: Google OAuth token for API calls

    Returns:
        True if processed successfully, False otherwise
    """
    google_event_id = event_data.get("id")
    if not google_event_id:
        logger.warning("Event missing ID, skipping")
        return False

    logger.info("Processing event: %s", google_event_id)

    # Parse start/end times BEFORE get_or_create
    start_info = event_data.get("start", {})
    end_info = event_data.get("end", {})

    logger.info("parsing start and end times for event %s", google_event_id)
    start_datetime = _parse_datetime(start_info)
    end_datetime = _parse_datetime(end_info)

    if not start_datetime or not end_datetime:
        logger.error(f"Could not parse datetime for event {google_event_id}. Start: {start_info}, End: {end_info}")
        return False

    # Determine if this is an all-day event
    is_all_day = "date" in start_info and "date" in end_info

    # Extract event details
    summary = event_data.get("summary", "")
    description = event_data.get("description", "")
    location = event_data.get("location", "")

    # Extract attendees
    attendees_data = event_data.get("attendees", [])
    attendees = [
        {
            "email": attendee.get("email"),
            "status": attendee.get("responseStatus"),
            "optional": attendee.get("optional", False),
        }
        for attendee in attendees_data
    ]

    # Check if event already exists
    existing_event, created = CalendarEvent.objects.get_or_create(
        google_event_id=google_event_id,
        user=user,
        defaults={
            "raw_google_data": event_data,
            "summary": summary,
            "description": description,
            "location": location,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "all_day": is_all_day,
            "organizer_email": event_data.get("organizer", {}).get("email", ""),
            "attendees": attendees,
            "meeting_url": _extract_meeting_url(event_data),
            "status": event_data.get("status", "confirmed"),
        },
    )

    logger.info("existing_event = %s", existing_event)

    if not created and existing_event.last_synced:
        logger.debug(f"Event {google_event_id} already processed, skipping")
        return True

    # If the event already existed, we still need to update it with latest data
    if not created:
        existing_event.summary = summary
        existing_event.description = description
        existing_event.location = location
        existing_event.start_datetime = start_datetime
        existing_event.end_datetime = end_datetime
        existing_event.all_day = is_all_day
        existing_event.organizer_email = event_data.get("organizer", {}).get("email", "")
        existing_event.attendees = attendees
        existing_event.meeting_url = _extract_meeting_url(event_data)
        existing_event.status = event_data.get("status", "confirmed")
        existing_event.raw_google_data = event_data

    # Process attachments if any
    attachments_data = event_data.get("attachments", [])
    if attachments_data:
        _process_event_attachments(existing_event, attachments_data, social_token)

    # Prepare content for embedding
    existing_event.combined_text = existing_event.generate_combined_text()

    # Generate embedding
    try:
        embedding = google_embedding_service.generate_embedding(existing_event.combined_text)
        if embedding:
            existing_event.content_embedding = embedding
        else:
            logger.warning(f"Failed to generate embedding for event {google_event_id}")
    except Exception as e:
        logger.error(f"Error generating embedding for event {google_event_id}: {e}")

    # Mark as processed
    existing_event.last_synced = timezone.now()
    existing_event.save()

    logger.info(f"Successfully processed event: {summary} ({google_event_id})")
    return True


def _parse_datetime(datetime_info: dict) -> Optional[datetime]:
    """Parse datetime from Google Calendar API format."""
    try:
        if "dateTime" in datetime_info:
            # Regular event with time
            datetime_str = datetime_info["dateTime"]
            logger.debug(f"Parsing dateTime: {datetime_str}")
            # Handle both Z suffix and timezone offset
            if datetime_str.endswith("Z"):
                datetime_str = datetime_str.replace("Z", "+00:00")
            return datetime.fromisoformat(datetime_str)
        elif "date" in datetime_info:
            # All-day event
            date_str = datetime_info["date"]
            logger.debug(f"Parsing all-day date: {date_str}")
            # Create datetime at start of day in UTC
            return datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
    except Exception as e:
        logger.error(f"Error parsing datetime from {datetime_info}: {e}")
        return None

    logger.warning(f"No valid date/dateTime found in {datetime_info}")
    return None


def _extract_meeting_url(event_data: dict) -> str:
    """Extract meeting URL from event data."""
    # Check various fields where meeting URLs might be stored

    # Google Meet links
    conference_data = event_data.get("conferenceData", {})
    entry_points = conference_data.get("entryPoints", [])
    for entry_point in entry_points:
        if entry_point.get("entryPointType") == "video":
            return entry_point.get("uri", "")

    # Check description for common meeting URL patterns
    description = event_data.get("description", "")
    if description:
        # Look for common meeting URL patterns
        url_patterns = [
            r"https://meet\.google\.com/[a-z-]+",
            r"https://zoom\.us/j/\d+",
            r"https://teams\.microsoft\.com/l/meetup-join/[^\\s]+",
        ]

        for pattern in url_patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(0)

    return ""


def _process_event_attachments(event: CalendarEvent, attachments_data: list, social_token: SocialToken):
    """Process attachments for a calendar event."""
    for attachment_data in attachments_data:
        file_id = attachment_data.get("fileId")
        title = attachment_data.get("title", "Unknown")

        if not file_id:
            continue

        # Create or get attachment record
        attachment, created = CalendarEventAttachment.objects.get_or_create(
            event=event,
            file_id=file_id,
            defaults={
                "file_name": title,
                "mime_type": attachment_data.get("mimeType", ""),
                "file_url": attachment_data.get("fileUrl", ""),
                "icon_link": attachment_data.get("iconLink", ""),
            },
        )

        if attachment.processing_status == "completed":
            continue

        # Process the attachment
        try:
            extracted_text, extraction_method = attachment_service.process_attachment(
                attachment_data, social_token.token, social_token.token_secret
            )

            attachment.processed_content = extracted_text or ""
            attachment.extraction_method = extraction_method
            attachment.processing_status = "completed"
            attachment.processed_at = timezone.now()

            # Generate embedding for attachment content
            if extracted_text:
                try:
                    embedding = google_embedding_service.generate_embedding(extracted_text)
                    if embedding:
                        attachment.content_embedding = embedding
                except Exception as e:
                    logger.error(f"Error generating embedding for attachment {file_id}: {e}")

            attachment.save()
            logger.info(f"Processed attachment: {title} ({extraction_method})")

        except Exception as e:
            attachment.processing_error = str(e)
            attachment.processing_status = "failed"
            attachment.save()
            logger.error(f"Error processing attachment {title}: {e}")


def bulk_process_all_users_calendar_events(days_back: int = 30, days_forward: int = 90) -> dict:
    """
    Process calendar events for all users with Google accounts.

    Args:
        days_back: Number of days to look back for events
        days_forward: Number of days to look forward for events

    Returns:
        Dictionary with processing results for all users
    """
    emails = get_google_authenticated_user_emails()
    results = {}

    logger.info(f"Starting bulk processing for {len(emails)} users")

    total_processed = 0
    total_errors = 0
    for email in emails:
        try:
            result = process_calendar_events_for_rag(email, days_back, days_forward)
            results[email] = result
            total_processed += result.get("processed", 0)
        except Exception as e:
            logger.error(f"Error processing events for {email}: {e}")
            results[email] = {"error": str(e), "processed": 0, "errors": 1}
            total_errors += 1

    logger.info(f"Bulk processing complete: {total_processed} processed, {total_errors} errors.")
    return results


def process_single_user_calendar_events(email: str, days_back: int = 30, days_forward: int = 90) -> dict:
    """
    Process calendar events for a single user.

    Args:
        email: User email address
        days_back: Number of days to look back for events
        days_forward: Number of days to look forward for events

    Returns:
        Dictionary with processing results
    """
    logger.info("Processing calendar events for user: %s", email)

    result = process_calendar_events_for_rag(email, days_back, days_forward)

    logger.info("Finished processing calendar events for user: %s", email)
    logger.info("Total events found: %s", result.get("total_events", 0))
    logger.info("Events processed: %s", result.get("processed", 0))
    total_errors = result.get("errors", 0)
    if total_errors > 0:
        logger.error("Total Errors: %s", total_errors)

    return result


def generate_embeddings_for_unprocessed_events():
    """
    Generate embeddings for calendar events that don't have them yet.
    """

    events_without_embeddings = CalendarEvent.objects.filter(
        content_embedding__isnull=True, combined_text__isnull=False
    ).exclude(combined_text="")

    logger.info(f"Found {events_without_embeddings.count()} events without embeddings")

    processed = 0
    errors = 0

    for event in events_without_embeddings:
        try:
            if not event.combined_text:
                logger.warning(f"Event {event.google_event_id} has no combined text. generating embedding.")
                event.combined_text = event.generate_combined_text()

            embedding = google_embedding_service.generate_embedding(event.combined_text)
            if embedding:
                event.content_embedding = embedding
                event.last_synced = timezone.now()
                event.save(update_fields=["content_embedding", "combined_text", "last_synced"])
                processed += 1
            else:
                errors += 1
                logger.warning(f"Failed to generate embedding for event {event.google_event_id}")
        except Exception as e:
            errors += 1
            logger.error(f"Error generating embedding for event {event.google_event_id}: {e}")

    logger.info(f"Embedding generation complete: {processed} processed, {errors} errors.")


def cleanup_old_rag_queries(cutoff_days: int = 1):
    """
    Clean up old RAG queries based on the cutoff days.

    Args:
        cutoff_days: Number of days to keep the RAG queries for
    """
    logger.debug("Starting cleanup of old RAG queries")

    cutoff_date = timezone.now() - timezone.timedelta(days=cutoff_days)
    old_queries = CalendarRAGQuery.objects.filter(created_at__lt=cutoff_date)

    logger.info(f"Cleaning up {old_queries.count()} old RAG queries older than {cutoff_days} days")

    deleted_count, _ = old_queries.delete()
    logger.info(f"Deleted {deleted_count} old RAG queries.")
