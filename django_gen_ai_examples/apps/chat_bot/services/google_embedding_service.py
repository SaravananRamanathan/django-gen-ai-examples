"""
Google Embedding service using the new google-genai library.
Usage:
    from chat_bot.services.google_embedding_service import google_embedding_service
    embedding = google_embedding_service.generate_embedding("Your text here")
"""

import logging
from typing import List, Optional

import google.genai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class GoogleEmbeddingService:
    """
    Service for generating embeddings using Google's new embedding models.
    """

    def __init__(self):
        # Configure Google Generative AI
        api_key = getattr(settings, "GOOGLE_GENERATIVE_AI_API_KEY", None)
        if not api_key:
            raise ValueError("GOOGLE_GENERATIVE_AI_API_KEY not found in settings")

        # Initialize the new google-genai client
        self.client = genai.Client(api_key=api_key)
        # Use the latest text embedding model
        # self.embedding_model = "text-embedding-004"
        self.embedding_model = "gemini-embedding-001"
        self.embedding_dimension = 3072  # Native dimension of gemini-embedding-001

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to generate embedding for

        Returns:
            List of float values representing the embedding, or None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty or whitespace-only text provided for embedding")
            return None

        try:
            # Use the new google-genai API for embeddings
            response = self.client.models.embed_content(model=self.embedding_model, contents=text.strip())

            # Extract embedding from response - use defensive approach
            try:
                embedding_values = None

                # Try different possible response structures
                if hasattr(response, "embeddings") and response.embeddings:
                    # Handle list of embeddings
                    if len(response.embeddings) > 0:
                        embedding = response.embeddings[0]
                        if hasattr(embedding, "values") and embedding.values:
                            embedding_values = list(embedding.values)
                        elif isinstance(embedding, list):
                            embedding_values = embedding

                # Try accessing direct attributes
                if not embedding_values:
                    for attr_name in ["embedding", "values", "data"]:
                        if hasattr(response, attr_name):
                            attr_value = getattr(response, attr_name)
                            if attr_value:
                                if hasattr(attr_value, "values") and attr_value.values:
                                    embedding_values = list(attr_value.values)
                                    break
                                elif isinstance(attr_value, list):
                                    embedding_values = attr_value
                                    break

                if embedding_values:
                    return embedding_values

                logger.warning(f"Unexpected response structure: {type(response)}")

            except Exception as e:
                logger.error(f"Error extracting embedding from response: {e}")

            logger.warning("No embedding found in response")
            return None

        except Exception as e:
            logger.error(f"Error generating embedding for text length {len(text)}: {e}")
            return None

    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List of embeddings (same order as input texts)
        """
        embeddings = []

        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)

        return embeddings

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this service."""
        return self.embedding_dimension

    def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """
        Generate embedding for a search query.
        This uses the same method as generate_embedding but is semantically different.

        Args:
            query: Search query text

        Returns:
            Embedding vector for the query
        """
        return self.generate_embedding(query)


# import google_embedding_service to use in other modules.
google_embedding_service = GoogleEmbeddingService()
