"""
All Constants for the Chat Bot application.
"""

import os


class SidebarMenuChoices:
    """
    Category/Sub-item choices for the sidebar menu.
    """

    # Main categories:
    COMPLETIONS = "Completions"
    LANG_CHAIN = "LangChain"

    # JSON keys for sidebar menu items (Used by FE-Vue):
    NAME_KEY = "name"
    IS_EXPANDED_KEY = "isExpanded"
    SUB_ITEMS_KEY = "subItems"
    API_URL_KEY = "apiUrl"
    API_URL_NAME_KEY = "apiUrlName"
    CONFIG_OPTIONS = "configOptions"

    @classmethod
    def choices(cls):
        """
        Returns a list of choices for the sidebar menu.
        """
        return [
            {
                cls.NAME_KEY: cls.COMPLETIONS,
                cls.IS_EXPANDED_KEY: True,
                cls.SUB_ITEMS_KEY: [
                    {cls.NAME_KEY: 'Single prompt', cls.API_URL_NAME_KEY: 'chatbot-api:single_prompt'},
                    {cls.NAME_KEY: 'Summarize text', cls.API_URL_NAME_KEY: 'chatbot-api:summarize_text'},
                    {cls.NAME_KEY: 'Sentiment analysis', cls.API_URL_NAME_KEY: 'chatbot-api:sentiment_analysis'},
                ],
            },
            {
                cls.NAME_KEY: cls.LANG_CHAIN,
                cls.IS_EXPANDED_KEY: True,
                cls.SUB_ITEMS_KEY: [
                    {
                        cls.NAME_KEY: 'Translate',
                        cls.API_URL_NAME_KEY: 'chatbot-api:translate',
                        cls.CONFIG_OPTIONS: [
                            {
                                'key': 'language',
                                'label': 'Translate to Language',
                                'type': 'select',
                                'defaultValue': 'Tamil',
                                'options': [
                                    {'value': 'Tamil', 'text': 'Tamil'},
                                    {'value': 'Hindi', 'text': 'Hindi'},
                                    {'value': 'English', 'text': 'English'},
                                    {'value': 'Japanese', 'text': 'Japanese'},
                                ],
                            },
                            {
                                'key': 'tone',
                                'label': 'Tone of Voice',
                                'type': 'select',
                                'defaultValue': 'Sweet',
                                'options': [
                                    {'value': 'Sweet', 'text': 'Sweet'},
                                    {'value': 'Formal', 'text': 'Formal'},
                                    {'value': 'Informal', 'text': 'Informal'},
                                    {'value': 'Rude', 'text': 'Rude'},
                                    {'value': 'Angry', 'text': 'Angry'},
                                ],
                            },
                        ],
                    },
                ],
            },
        ]


class GeminiAPIConstants:
    """
    Constants for Gemini API interactions.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    MODEL = "gemini-2.5-flash"
    GEMINI_API_KEY = "GEMINI_API_KEY"
    GEMINI_API_KEY_CACHE = "GEMINI_API_KEY_CACHE"
    CACHE_TIMEOUT = 60 * 60  # 1 hour

    @classmethod
    def get_api_key(cls) -> str:
        """
        Retrieve the Gemini API key from ENV.
        """
        try:
            return str(os.environ[cls.GEMINI_API_KEY])
        except KeyError as e:
            raise EnvironmentError(f"Environment variable `{cls.GEMINI_API_KEY}` not set.") from e
