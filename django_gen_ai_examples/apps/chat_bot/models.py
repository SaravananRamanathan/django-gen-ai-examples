"""
All models realted to chat_bot App.
"""

from django.db import models


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
