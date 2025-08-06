"""
Common tasks and utilities for the chat bot app.
"""

import logging

from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


def validate_user_email(email: str) -> bool:
    """
    Validate if the provided email belongs to a registered user.

    Args:
        email (str): The email address to validate.

    Returns:
        bool: True if the email is associated with a registered user, False otherwise.
    """
    try:
        User.objects.get(email=email)
        logger.info("User with email %s exists.", email)
        return True
    except User.DoesNotExist:
        logger.warning("User with email %s does not exist.", email)
        return False
