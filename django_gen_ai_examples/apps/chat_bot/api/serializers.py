"""
Chat Bot API Serializers
"""

from rest_framework import serializers

from chat_bot.models import DictionaryWord, DictionaryWordMeaning


class DictionaryWordMeaningSerializer(serializers.ModelSerializer):
    """
    DictionaryWordMeaning serializer.
    """

    class Meta:
        model = DictionaryWordMeaning
        fields = ["part_of_speech", "definition"]


class DictionaryWordSerializer(serializers.ModelSerializer):
    """
    DictionaryWord serializer.
    """

    meanings = DictionaryWordMeaningSerializer(many=True, read_only=True)

    class Meta:
        model = DictionaryWord
        fields = ["term", "synonyms", "meanings"]
