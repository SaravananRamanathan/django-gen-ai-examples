"""
Chat Bot Views
"""
from django.views.generic import TemplateView


class ChatWindowView(TemplateView):
    "Simple chat window api<>user communication base template."

    template_name = "chat_bot/chat_window.html"

    def get_context_data(self, **kwargs):
        "Add Additional context to template as needed."

        context = super().get_context_data(**kwargs)

        return context
