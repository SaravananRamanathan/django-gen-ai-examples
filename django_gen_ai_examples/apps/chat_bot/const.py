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

    # JSON keys for sidebar menu items (Used by FE-Vue):
    NAME_KEY = "name"
    IS_EXPANDED_KEY = "isExpanded"
    SUB_ITEMS_KEY = "subItems"
    API_URL_KEY = "apiUrl"
    API_URL_NAME_KEY = "apiUrlName"

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
                ],
            },
            # TODO: Add more categories as needed:
            # {cls.NAME_KEY: 'Cat 2', cls.API_URL_KEY: 'chatbot-api:cat_2'},
            # {cls.NAME_KEY: 'Cat 3', cls.API_URL_KEY: 'chatbot-api:cat_3'},
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
