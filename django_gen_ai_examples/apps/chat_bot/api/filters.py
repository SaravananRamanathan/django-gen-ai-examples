"""
Chat Bot API Filters
"""

import django_filters
from pgvector.django import L2Distance
from sentence_transformers import SentenceTransformer

from chat_bot.models import DictionaryWord

# Question: will the model be loaded into memory? downloaded every time?
EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


class DictionaryWordFilter(django_filters.FilterSet):
    """
    DictionaryWord model FilterSet.
    Supports semantic search using vector embeddings.
    """

    # term = django_filters.CharFilter(field_name="term", lookup_expr="istartswith")
    semantic_term = django_filters.CharFilter(method="filter_by_similarity", label="Semantic Search Term")

    def filter_by_similarity(self, queryset, name, value):
        """
        Filter DictionaryWord objects by semantic similarity to the given term.
        Uses the SentenceTransformer model to generate embeddings and filter results.
        """
        # TODO: add logging instead of print statements.
        print("Filtering by semantic term:", value)
        if not value:
            return queryset

        # Generate embedding for the input value ,NOTE: AKA the term that we are trying to find similar terms for.
        # value is our Input term, e.g., "cat" , now we need to find terms similar to cat!
        embedding = EMBEDDING_MODEL.encode(value, convert_to_tensor=True)

        # Filter using L2 distance
        # NOTE: L2Distance is used to calculate the distance between the vector embeddings. - we don't have to know the math.
        # The closer the distance, the more similar the terms are => hence we order by distance.
        return queryset.annotate(_distance=L2Distance("embedding", embedding)).order_by("_distance")[:100]
        # NOTE: hard limit needed atleast until we have pagination.
        # funny thing, I tried to debug this for some time, then realized that the backend was returning all results, and the frontend was crashing due to too many results.
        # so in theory all "terms" are similar to each other but at a greater distance.
        # Question: how do we know which percentage to consider as good enough similarity?

    class Meta:
        model = DictionaryWord
        fields = ["semantic_term"]
