"""
All tasks related to Google Calendar integration.
"""

import logging
from typing import List, Tuple

from allauth.socialaccount.models import SocialToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from googleapiclient.discovery import build

from chat_bot.const import GoogleOAuth2

logger = logging.getLogger(__name__)


def get_google_authenticated_user_emails(chunk_size: int = 1) -> List[Tuple[str]]:
    """
    Get emails in chunks.

    Args:
        chunk_size: Number of emails to return in each chunk.

    Returns:
        A list of tuples of email addresses: [(email1, email2, ...), (email21, email22, ...), ...]
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


def get_upcoming_events(email: str) -> list[dict]:
    """
    Fetch upcoming calendar events for a specific user.

    Args:
        email: The email address of the user.

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
        "Fetching calendar events for user: %s, email: %s",
        user,
        email,
    )

    try:
        social_token = SocialToken.objects.get(account__user=user, account__provider="google")
    except SocialToken.DoesNotExist:
        logger.error("No Google social token found for user %s.", user)
        return []

    service = build(
        "calendar",
        "v3",
        credentials=GoogleOAuth2.get_credentials(token=social_token.token, refresh_token=social_token.token_secret),
    )
    now = timezone.now().isoformat()

    events_result = (
        service.events()
        .list(calendarId="primary", timeMin=now, maxResults=100, singleEvents=True, orderBy="startTime")
        .execute()
    )

    event_items = events_result.get("items", [])

    if not event_items:
        logger.warning("No upcoming events found for %s.", email)
        return []

    # NOTE: logging to test for now.
    for event_item in event_items:
        logger.info("Event: %s", event_item)
        logger.info("Event summary: %s", event_item.get("summary", "No summary"))

    return event_items
