"""
Chat Bot Views
"""

from django.views.generic import TemplateView

from .utils import get_sidebar_menu_choices


class ChatWindowView(TemplateView):
    "Simple chat window api<>user communication base template."

    template_name = "chat_bot/chat_window.html"

    def get_context_data(self, **kwargs):
        "Add Additional context to template as needed."

        context = super().get_context_data(**kwargs)
        context['sidebar_menu_choices'] = get_sidebar_menu_choices()

        return context
