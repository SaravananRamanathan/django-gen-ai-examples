"""
Chat Bot API Filters
"""

import django_filters

from chat_bot.models import DictionaryWord


class DictionaryWordFilter(django_filters.FilterSet):
    """
    DictionaryWord model FilterSet.
    """

    term = django_filters.CharFilter(field_name="term", lookup_expr="istartswith")

    class Meta:
        model = DictionaryWord
        fields = ["term"]
