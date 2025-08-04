"""
All Constants for the Chat Bot application.
"""

import os

from google.oauth2.credentials import Credentials


class SidebarMenuChoices:
    """
    Category/Sub-item choices for the sidebar menu.
    """

    # Main categories:
    COMPLETIONS = "Completions"
    LANG_CHAIN = "LangChain"
    SEMANTIC_SEARCH = "Semantic Search"

    # JSON keys for sidebar menu items (Used by FE-Vue):
    NAME_KEY = "name"
    IS_EXPANDED_KEY = "isExpanded"
    SUB_ITEMS_KEY = "subItems"
    API_URL_KEY = "apiUrl"
    API_URL_NAME_KEY = "apiUrlName"
    CONFIG_OPTIONS = "configOptions"
    PLACEHOLDER = "placeholder"
    UI_TYPE = "uiType"

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
                    {cls.NAME_KEY: "Single prompt", cls.API_URL_NAME_KEY: "chatbot-api:single_prompt"},
                    {cls.NAME_KEY: "Summarize text", cls.API_URL_NAME_KEY: "chatbot-api:summarize_text"},
                    {cls.NAME_KEY: "Sentiment analysis", cls.API_URL_NAME_KEY: "chatbot-api:sentiment_analysis"},
                ],
            },
            {
                cls.NAME_KEY: cls.LANG_CHAIN,
                cls.IS_EXPANDED_KEY: True,
                cls.SUB_ITEMS_KEY: [
                    {
                        cls.NAME_KEY: "Translate",
                        cls.API_URL_NAME_KEY: "chatbot-api:lc_translate",
                        cls.CONFIG_OPTIONS: [
                            {
                                "key": "language",
                                "label": "Translate to Language",
                                "type": "select",
                                "defaultValue": "Tamil",
                                "options": [
                                    {"value": "Tamil", "text": "Tamil"},
                                    {"value": "Hindi", "text": "Hindi"},
                                    {"value": "English", "text": "English"},
                                    {"value": "Japanese", "text": "Japanese"},
                                ],
                            },
                            {
                                "key": "tone",
                                "label": "Tone of Voice",
                                "type": "select",
                                "defaultValue": "Sweet",
                                "options": [
                                    {"value": "Sweet", "text": "Sweet"},
                                    {"value": "Formal", "text": "Formal"},
                                    {"value": "Informal", "text": "Informal"},
                                    {"value": "Rude", "text": "Rude"},
                                    {"value": "Angry", "text": "Angry"},
                                ],
                            },
                        ],
                    },
                    {
                        cls.NAME_KEY: "Conversation (Agent!)",
                        cls.API_URL_NAME_KEY: "chatbot-api:lc_conversation",
                    },
                    {
                        cls.NAME_KEY: "YouTube Transcript",
                        cls.API_URL_NAME_KEY: "chatbot-api:lc_youtube_transcript",
                        cls.PLACEHOLDER: "Enter YouTube Video ID",
                    },
                ],
            },
            {
                cls.NAME_KEY: cls.SEMANTIC_SEARCH,
                cls.IS_EXPANDED_KEY: True,
                cls.SUB_ITEMS_KEY: [
                    {
                        cls.NAME_KEY: "Dictionary Search",
                        cls.API_URL_NAME_KEY: "chatbot-api:dictionary_search",
                        cls.PLACEHOLDER: "Search for a word",
                        cls.UI_TYPE: "search-table",
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


class GoogleOAuth2:
    """
    Constants for Google OAuth integration.
    """

    GOOGLE_OAUTH_CLIENT_ID = "GOOGLE_OAUTH_CLIENT_ID"
    GOOGLE_OAUTH_CLIENT_SECRET = "GOOGLE_OAUTH_CLIENT_SECRET"
    token_uri = "https://oauth2.googleapis.com/token"
    scopes = ["https://www.googleapis.com/auth/calendar.readonly"]

    @classmethod
    def get_client_id(cls) -> str:
        """
        Retrieve the Google OAuth client ID from ENV.
        NOTE: client ID is also saved to allauth-SocialApp model via django admin.
        """
        try:
            return str(os.environ[cls.GOOGLE_OAUTH_CLIENT_ID])
        except KeyError as e:
            raise EnvironmentError(f"Environment variable `{cls.GOOGLE_OAUTH_CLIENT_ID}` not set.") from e

    @classmethod
    def get_client_secret(cls) -> str:
        """
        Retrieve the Google OAuth client secret from ENV.
        NOTE: client secret is also saved to allauth-SocialApp model via django admin.
        """
        try:
            return str(os.environ[cls.GOOGLE_OAUTH_CLIENT_SECRET])
        except KeyError as e:
            raise EnvironmentError(f"Environment variable `{cls.GOOGLE_OAUTH_CLIENT_SECRET}` not set.") from e

    @classmethod
    def get_credentials(cls, token: str, refresh_token: str) -> "Credentials":
        """
        Create and return Google OAuth credentials.

        Args:
            token: Access token.
            refresh_token: Refresh token.

        Returns:
            Credentials object for Google API access.
        """
        return Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri=cls.token_uri,
            client_id=cls.get_client_id(),
            client_secret=cls.get_client_secret(),
            scopes=cls.scopes,
        )
