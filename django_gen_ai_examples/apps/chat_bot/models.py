"""
All models realted to chat_bot App.
"""

from typing import TYPE_CHECKING

from django.db import models
from pgvector.django import VectorField


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
