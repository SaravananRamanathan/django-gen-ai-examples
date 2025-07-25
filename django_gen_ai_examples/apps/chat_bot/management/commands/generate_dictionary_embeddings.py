"""
Management command to generate initial embeddings for already existing DictionaryWord objects.
This command uses the SentenceTransformer model (all-MiniLM-L6-v2) to generate embeddings for each word and its synonyms.
"""

from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer

from chat_bot.models import DictionaryWord


class Command(BaseCommand):
    help = "Generates and saves vector embeddings for dictionary words."

    def handle(self, *args, **kwargs):
        self.stdout.write("Loading sentence transformer model, will download if not available...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        self.stdout.write(self.style.SUCCESS("Model loaded."))

        words_to_process = list(DictionaryWord.objects.filter(embedding__isnull=True))

        if not words_to_process:
            self.stdout.write(self.style.SUCCESS("All words already have embeddings. Nothing to do."))
            return

        self.stdout.write(f"Found {len(words_to_process)} words to process...")

        # add extra content to the term. add meanings (?)
        texts_to_embed = [f"{word.term}. Synonyms: {', '.join(word.synonyms)}" for word in words_to_process]

        self.stdout.write("Generating embeddings in a batch, WILL TAKE TIME -just wait:)")
        embeddings = model.encode(texts_to_embed, show_progress_bar=True)

        for word, embedding in zip(words_to_process, embeddings):
            word.embedding = embedding

        # Save embeddings in batches. bulk update of 100k+ crashes the server.
        self.stdout.write("Saving embeddings to the database...")
        batch_size = 5000
        total_updated = 0
        total_words_to_process = len(words_to_process)

        for i in range(0, total_words_to_process, batch_size):
            self.stdout.write(f"Processing batch {i // batch_size + 1}...")
            batch = words_to_process[i : i + batch_size]
            DictionaryWord.objects.bulk_update(batch, ["embedding"])
            total_updated += len(batch)
            self.stdout.write(f"Updated {total_updated}/{total_words_to_process} words...")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully generated and saved embeddings for {total_words_to_process} words.")
        )
