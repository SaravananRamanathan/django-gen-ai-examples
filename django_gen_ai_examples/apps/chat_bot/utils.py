"""
All Utility functions for the Chat Bot application.
"""

from django.urls import reverse

from .const import SidebarMenuChoices


def get_sidebar_menu_choices():
    """
    Process sidebar menu choices to reverse API Url's.
    Returns:
        list: Processed list with API URLs.
    """
    choices = SidebarMenuChoices.choices()
    for choice in choices:
        sub_items = choice.get(SidebarMenuChoices.SUB_ITEMS_KEY, [])
        if not sub_items and SidebarMenuChoices.API_URL_NAME_KEY in choice:
            choice[SidebarMenuChoices.API_URL_KEY] = reverse(choice[SidebarMenuChoices.API_URL_NAME_KEY])
            continue
        for sub_item in sub_items:
            if SidebarMenuChoices.API_URL_NAME_KEY in sub_item:
                sub_item[SidebarMenuChoices.API_URL_KEY] = reverse(sub_item[SidebarMenuChoices.API_URL_NAME_KEY])
    return choices
