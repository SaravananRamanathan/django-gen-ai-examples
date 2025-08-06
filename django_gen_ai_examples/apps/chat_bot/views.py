"""
Chat Bot Views
"""

import logging

from allauth.socialaccount.models import SocialAccount
from django.views.generic import TemplateView

from .utils import get_sidebar_menu_choices

logger = logging.getLogger(__name__)


class ChatWindowView(TemplateView):
    "Simple chat window api<>user communication base template."

    # Default template for authenticated users:
    template_name = "chat_bot/chat_window.html"

    def get_template_names(self):
        """
        If the user is authenticated show main application.
        If not, redirect to simple onboarding/login page.
        """
        user = self.request.user

        if user.is_authenticated and SocialAccount.objects.filter(user__pk=user.pk, provider="google").exists():
            logger.debug(
                "User %s [ID: %s] is authenticated and has a Linked Google account.",
                user,
                user.pk,
            )
            return [self.template_name]
        else:
            logger.debug(
                "User %s [ID: %s] is not authenticated or doesn't have a Linked Google account. Redirecting to onboarding.",
                user,
                user.pk,
            )
            return ["chat_bot/onboarding.html"]

    def get_context_data(self, **kwargs):
        "Add Additional context to template as needed."

        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["sidebar_menu_choices"] = get_sidebar_menu_choices()

        return context
