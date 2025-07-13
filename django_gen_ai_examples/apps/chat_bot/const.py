"""
All Constants for the Chat Bot application.
"""


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
                    {cls.NAME_KEY: 'Single prompt', cls.API_URL_NAME_KEY: 'chatbot-api:gemini_chat_bot'},
                    {cls.NAME_KEY: 'Summarize text', cls.API_URL_NAME_KEY: 'chatbot-api:summarize_text'},
                ],
            },
            # TODO: Add more categories as needed:
            # {cls.NAME_KEY: 'Cat 2', cls.API_URL_KEY: 'chatbot-api:cat_2'},
            # {cls.NAME_KEY: 'Cat 3', cls.API_URL_KEY: 'chatbot-api:cat_3'},
        ]
